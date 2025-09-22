ubuntu@ip-172-31-32-78:~/test$ cat aws.py
#!/usr/bin/env python3
"""
costoptimization_prod.py - Production-ready cost optimization reporter

What it does (read-only / non-destructive):
- Discovers tagged resources using Resource Groups Tagging API.
- Fetches costs via Cost Explorer (handles NextPageToken).
- Probes CloudWatch for basic metrics (EC2, RDS, Lambda heuristics).
- Produces recommendations (Stop/Delete/Rightsize/Optimize) including EC2 rightsizing.
- Flags Free Tier / zero-cost resources.
- Prints a human-friendly ASCII report (summary table + recommendation details) matching your requested format.
- Saves a JSON report to ./outputs/

Notes:
- This script is *report-only*: it does not modify or delete any AWS resources.
- Configure AWS credentials via the usual environment/credential chain (AWS CLI, env vars, or IAM role).
- Intended for production use as a read-only reporting tool. Run from a machine with network access to AWS APIs.

Requirements:
- Python 3.9+
- boto3
- botocore
- tabulate

Install: pip install boto3 tabulate
"""

from datetime import datetime, timedelta
import json
import logging
import os
import sys
from typing import Dict, Tuple

import boto3
from botocore.exceptions import ClientError
from tabulate import tabulate

# ----------------------------
# Config
# ----------------------------
LOG_LEVEL = logging.INFO
REPORT_DIR = "./outputs"
os.makedirs(REPORT_DIR, exist_ok=True)

# Number of top services to show in the header list
TOP_SERVICES_COUNT = 5

# Limits
MAX_TAG_PAGES = 50           # pagination limit for tagging API discovery
MAX_RESOURCE_MATCH = 1000    # protect against huge loops when matching resources

# Logging
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("costopt")

# ----------------------------
# Helpers
# ----------------------------
def iso_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def safe_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

# ----------------------------
# Regions
# ----------------------------
def get_all_regions() -> list:
    ec2 = boto3.client('ec2', region_name='us-east-1')
    try:
        regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
        log.info("Found %d regions", len(regions))
        return regions
    except Exception as e:
        log.warning("Couldn't list regions, defaulting to ['us-east-1']: %s", e)
        return ['us-east-1']

# ----------------------------
# Discover tagged resources (Resource Groups Tagging API)
# ----------------------------
def discover_tagged_resources(max_pages: int = MAX_TAG_PAGES) -> list:
    client = boto3.client('resourcegroupstaggingapi', region_name='us-east-1')
    paginator = client.get_paginator('get_resources')
    resources = []
    pages = 0
    try:
        for page in paginator.paginate(ResourcesPerPage=50):
            pages += 1
            for r in page.get('ResourceTagMappingList', []):
                arn = r.get('ResourceARN')
                if not arn:
                    continue
                tags = {t['Key']: t['Value'] for t in r.get('Tags', [])} if r.get('Tags') else {}
                resources.append({'arn': arn, 'tags': tags})
            if max_pages and pages >= max_pages:
                break
    except ClientError as e:
        log.error("Tagging API failed: %s", e)
    log.info("Discovered %d tagged resources", len(resources))
    return resources

# ----------------------------
# Cost Explorer: get_cost_and_usage handling NextPageToken (SERVICE grouping only)
# ----------------------------
def get_costs_by_service(start_date: str, end_date: str) -> Dict[str, float]:
    ce = boto3.client('ce', region_name='us-east-1')  # Cost Explorer is global (us-east-1 ok)
    cost_by_service: Dict[str, float] = {}
    token = None
    while True:
        params = {
            'TimePeriod': {'Start': start_date, 'End': end_date},
            'Granularity': 'DAILY',
            'Metrics': ['UnblendedCost'],
            'GroupBy': [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        }
        if token:
            params['NextPageToken'] = token
        try:
            resp = ce.get_cost_and_usage(**params)
        except ClientError as e:
            log.error("Cost Explorer API error: %s", e)
            return cost_by_service
        for rbt in resp.get('ResultsByTime', []):
            for grp in rbt.get('Groups', []):
                keys = grp.get('Keys', [])
                amt = safe_float(grp.get('Metrics', {}).get('UnblendedCost', {}).get('Amount', 0.0))
                svc_name = keys[0] if len(keys) >= 1 else 'Unknown'
                cost_by_service[svc_name] = cost_by_service.get(svc_name, 0.0) + amt
        token = resp.get('NextPageToken')
        if not token:
            break
    log.info("Aggregated costs for %d services", len(cost_by_service))
    return cost_by_service

# ----------------------------
# CloudWatch metric probes (helper)
# ----------------------------
def probe_cloudwatch_average(namespace: str, metric_name: str, dim_name: str, dim_value: str,
                             start_time: datetime, end_time: datetime, region: str) -> float:
    try:
        cw = boto3.client('cloudwatch', region_name=region)
        resp = cw.get_metric_statistics(Namespace=namespace, MetricName=metric_name,
                                        Dimensions=[{'Name': dim_name, 'Value': dim_value}],
                                        StartTime=start_time, EndTime=end_time,
                                        Period=3600, Statistics=['Average'])
        points = resp.get('Datapoints', [])
        if not points:
            return 0.0
        return sum(p['Average'] for p in points) / len(points)
    except ClientError as e:
        log.debug("CloudWatch ClientError for %s %s: %s", namespace, dim_value, e)
        return 0.0
    except Exception as e:
        log.debug("CloudWatch error for %s %s: %s", namespace, dim_value, e)
        return 0.0

def get_usage_for_resource(service_short: str, resource_id: str,
                           start_time: datetime, end_time: datetime, region_hint: str = None) -> Tuple[bool, dict]:
    """
    Returns (is_unused_flag, usage_dict)
    is_unused = True means likely unused based on the heuristics applied.
    """
    usage = {}
    is_unused = True
    region = region_hint or 'us-east-1'
    try:
        if service_short in ('ec2', 'ec2-instance-connect') or service_short.startswith('ec2'):
            cpu = probe_cloudwatch_average('AWS/EC2', 'CPUUtilization', 'InstanceId', resource_id, start_time, end_time, region)
            usage['cpu_util'] = cpu
            if cpu > 0:
                is_unused = False
        elif service_short.startswith('rds') or service_short == 'rds':
            cpu = probe_cloudwatch_average('AWS/RDS', 'CPUUtilization', 'DBInstanceIdentifier', resource_id, start_time, end_time, region)
            usage['cpu_util'] = cpu
            if cpu > 0:
                is_unused = False
        elif 'lambda' in service_short:
            inv = probe_cloudwatch_average('AWS/Lambda', 'Invocations', 'FunctionName', resource_id, start_time, end_time, region)
            usage['invocations'] = inv
            if inv > 0:
                is_unused = False
        else:
            # For other services we don't probe metrics by default
            pass
    except Exception as e:
        log.debug("get_usage_for_resource error for %s %s: %s", service_short, resource_id, e)
    return is_unused, usage

# ----------------------------
# Recommendation heuristics
# ----------------------------
def recommend_by_service_and_usage(service_display: str, resource_id: str, usage: dict, cost: float) -> dict:
    svc = (service_display or '').lower()
    cost = safe_float(cost)
    # Zero cost / free tier
    if cost == 0:
        return {'action': 'NoCost', 'details': f"Free Tier / zero-cost {service_display} {resource_id}", 'estimated_savings': 0.0, 'confidence': 'LOW'}

    # EC2 heuristics
    if 'elastic compute' in svc or 'ec2' in svc:
        cpu = usage.get('cpu_util')
        if cpu is None:
            return {'action': 'Investigate', 'details': f"No CPU metric found for {resource_id}; check CloudWatch dimensions/region", 'estimated_savings': 0.0, 'confidence': 'LOW'}
        if cpu == 0:
            return {'action': 'Stop/Delete', 'details': f"No CPU activity for instance {resource_id}", 'estimated_savings': cost, 'confidence': 'HIGH'}
        if cpu < 20:
            return {'action': 'Rightsize (down)', 'details': f"Recommend downsize instance {resource_id} to t3.micro (avg CPU {cpu:.1f}%)", 'estimated_savings': round(cost * 0.30, 2), 'confidence': 'MEDIUM'}
        if cpu > 80:
            return {'action': 'Upsize', 'details': f"High CPU ({cpu:.1f}%) on {resource_id} — consider larger instance or autoscaling", 'estimated_savings': 0.0, 'confidence': 'MEDIUM'}
        return {'action': 'Keep/Optimize', 'details': f"Instance {resource_id} shows avg CPU {cpu:.1f}%", 'estimated_savings': round(cost * 0.05, 2), 'confidence': 'LOW'}

    # Lambda heuristics
    if 'lambda' in svc:
        inv = usage.get('invocations', 0)
        if inv == 0:
            return {'action': 'Delete', 'details': f"No invocations for function {resource_id}", 'estimated_savings': cost, 'confidence': 'HIGH'}
        return {'action': 'Optimize', 'details': f"{inv} invocations — consider tuning memory/timeout", 'estimated_savings': round(cost * 0.1, 2), 'confidence': 'LOW'}

    # S3 heuristics
    if 's3' in svc or 'simple storage' in svc or 'glacier' in svc:
        return {'action': 'Review Lifecycle', 'details': f"Consider lifecycle/archival for {resource_id}", 'estimated_savings': round(cost * 0.5, 2), 'confidence': 'MEDIUM'}

    # Cost Explorer / reporting
    if 'cost explorer' in svc or 'costexplorer' in svc or 'cost' in svc and 'explorer' in svc:
        return {'action': 'Review', 'details': f"Review Cost Explorer queries and granularity for {resource_id}", 'estimated_savings': round(cost * 0.5, 2), 'confidence': 'LOW'}

    # Generic fallback
    return {'action': 'Review', 'details': f"Review usage for {service_display} {resource_id}", 'estimated_savings': round(min(cost * 0.5, cost), 2), 'confidence': 'LOW'}

# ----------------------------
# Build recommendations
# ----------------------------
def build_recommendations(period_days: int = 30, tag_pages_limit: int = MAX_TAG_PAGES) -> dict:
    now = datetime.utcnow()
    start = now - timedelta(days=period_days)
    start_date = iso_date(start)
    end_date = iso_date(now)
    log.info("Building recommendations for period %s -> %s", start_date, end_date)

    # Discover resources and costs
    regions = get_all_regions()
    tagged = discover_tagged_resources(max_pages=tag_pages_limit)
    costs = get_costs_by_service(start_date, end_date)

    # Build resource map keyed by simple resource name (last ARN part)
    resource_map: Dict[str, list] = {}
    for r in tagged:
        arn = r.get('arn')
        if not arn:
            continue
        # last part after ':' or '/'
        rid = arn.split(':')[-1].split('/')[-1]
        resource_map.setdefault(rid, []).append(r)

    report = {
        'generated_at': now.isoformat() + 'Z',
        'period': {'start': start_date, 'end': end_date},
        'total_cost': round(sum(costs.values()), 2),
        'services': {}
    }

    processed = 0
    # For each service group returned by Cost Explorer, attempt to match resources and create recs
    for svc_display, svc_cost in sorted(costs.items(), key=lambda kv: kv[1], reverse=True):
        svc_cost = round(svc_cost, 4)
        report['services'].setdefault(svc_display, {'cost': svc_cost, 'recommendations': []})
        matched = False

        # Iterate resources and try to match by token or simple rules
        for rid, entries in list(resource_map.items())[:MAX_RESOURCE_MATCH]:
            # Quick heuristic matching: if the service token exists in the ARN or service name
            lower = svc_display.lower()
            # treat EC2 specially - matches instance IDs that start with i-
            if ('elastic compute' in lower or 'ec2' in lower) and rid.startswith('i-'):
                matched = True
                arn_region = None
                try:
                    arn = entries[0]['arn']
                    parts = arn.split(':')
                    if len(parts) > 3 and parts[3]:
                        arn_region = parts[3]
                except Exception:
                    arn_region = None
                is_unused, usage = get_usage_for_resource('ec2', rid, start, now, arn_region)
                rec = recommend_by_service_and_usage(svc_display, rid, usage, svc_cost)
                report['services'][svc_display]['recommendations'].append({
                    'resource': rid,
                    'region': arn_region or 'unknown',
                    **rec
                })
            else:
                try:
                    arn_lower = entries[0]['arn'].lower()
                    token = svc_display.lower().split()[0]
                    if token and token in arn_lower:
                        matched = True
                        arn_region = None
                        try:
                            arn = entries[0]['arn']
                            parts = arn.split(':')
                            if len(parts) > 3 and parts[3]:
                                arn_region = parts[3]
                        except Exception:
                            arn_region = None
                        # default: no metrics probed for generic services
                        is_unused, usage = True, {}
                        rec = recommend_by_service_and_usage(svc_display, rid, usage, svc_cost)
                        report['services'][svc_display]['recommendations'].append({
                            'resource': rid,
                            'region': arn_region or 'unknown',
                            **rec
                        })
                except Exception:
                    continue

        # If nothing matched, provide a generic recommendation (so every service has at least one rec)
        if not matched:
            rec = recommend_by_service_and_usage(svc_display, 'N/A', {}, svc_cost)
            report['services'][svc_display]['recommendations'].append({
                'resource': 'N/A',
                'region': 'all',
                **rec
            })

        processed += 1

    return report

# ----------------------------
# Output formatting to match the user's requested format
# ----------------------------
def print_cost_optimization_summary(report: dict):
    """
    Prints the human-friendly summary table and recommendation details in the exact style
    the user provided (ASCII table + detailed bullets).
    """
    gen = report.get('generated_at')
    period = report.get('period', {})
    total_spend = report.get('total_cost', 0.0)

    # Header
    print("====== COST OPTIMIZATION SUMMARY ======\n")
    print(f"Report generated at: {gen}")
    print(f"Analysis period   : {period}\n")
    print(f"Total spend (period): ${total_spend:.2f}\n")

    # Top services by cost
    services = report.get('services', {})
    sorted_services = sorted(services.items(), key=lambda kv: kv[1].get('cost', 0.0), reverse=True)
    print("Top services by cost:")
    for svc, info in sorted_services[:TOP_SERVICES_COUNT]:
        print(f" - {svc.ljust(40)} : ${info.get('cost', 0.0):.2f}")
    print("======================================\n")

    # Build table rows
    rows = []
    for svc, info in sorted_services:
        cost = info.get('cost', 0.0)
        recs = info.get('recommendations', [])
        for rec in recs:
            rows.append([
                svc if len(svc) <= 30 else svc[:27] + '...',  # shorten if very long
                f"{cost:.2f}",
                rec.get('resource', 'N/A'),
                rec.get('region', 'unknown'),
                rec.get('action', ''),
                f"{rec.get('estimated_savings', 0.0):.2f}",
                rec.get('confidence', ''),
                rec.get('details', '')
            ])

    # Print ASCII table similar to user's format
    headers = ["Service", "Cost($)", "Resource", "Region", "Action", "Est$Saved", "Conf", "Details"]
    if rows:
        # Use tabulate to produce a grid; tweak column spacing to look similar to example
        print(tabulate(rows, headers=headers, tablefmt='grid', stralign='left', numalign='right'))
    else:
        print("No recommendations generated.\n")

    # Recommendation details (bullet style)
    print("\n====== RECOMMENDATION DETAILS ======\n")
    for svc, info in sorted_services:
        cost = info.get('cost', 0.0)
        for rec in info.get('recommendations', []):
            resource = rec.get('resource', 'N/A')
            region = rec.get('region', 'unknown')
            action = rec.get('action', '')
            est = rec.get('estimated_savings', 0.0)
            conf = rec.get('confidence', '')
            details = rec.get('details', '')
            print(f"📌 Service: {svc}")
            print(f"   Resource : {resource}")
            print(f"   Region   : {region}")
            print(f"   Cost     : ${cost:.2f}")
            print(f"   Action   : {action} (Save ~${est:.2f}, {conf} confidence)")
            print(f"   Details  : {details}\n")

# ----------------------------
# Save JSON
# ----------------------------
def save_report_json(report: dict, prefix: str = "aws_optimization_report") -> str:
    fn = os.path.join(REPORT_DIR, f"{prefix}_{timestamp()}.json")
    try:
        with open(fn, 'w') as fh:
            json.dump(report, fh, indent=2, default=str)
        log.info("Saved report to %s", fn)
        return fn
    except Exception as e:
        log.error("Failed to save report: %s", e)
        return ""

# ----------------------------
# CLI Entrypoint
# ----------------------------
def main():
    try:
        # You can change period_days here (or extend to parse CLI args)
        period_days = 30
        report = build_recommendations(period_days=period_days, tag_pages_limit=MAX_TAG_PAGES)
        print_cost_optimization_summary(report)
        saved = save_report_json(report)
        if saved:
            print(f"Report saved to: {saved}")
    except Exception as e:
        log.exception("Run failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()

==============================================================================OUTPUT==============================================================================
ubuntu@ip-172-31-32-78:~/test$ ./aws.py
2025-09-22 12:22:53,644 INFO Building recommendations for period 2025-08-23 -> 2025-09-22
2025-09-22 12:22:53,657 INFO Found credentials in shared credentials file: ~/.aws/credentials
2025-09-22 12:22:53,907 INFO Found 18 regions
2025-09-22 12:22:54,025 INFO Discovered 13 tagged resources
2025-09-22 12:22:54,321 INFO Aggregated costs for 17 services
====== COST OPTIMIZATION SUMMARY ======

Report generated at: 2025-09-22T12:22:53.644382Z
Analysis period   : {'start': '2025-08-23', 'end': '2025-09-22'}

Total spend (period): $51.03

Top services by cost:
 - AmazonCloudWatch                         : $21.86
 - EC2 - Other                              : $13.23
 - AWS Cost Explorer                        : $10.49
 - Amazon Elastic Compute Cloud - Compute   : $2.83
 - Tax                                      : $2.25
======================================

+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Service                        |   Cost($) | Resource                                                    | Region    | Action           |   Est$Saved | Conf   | Details                                                                                                      |
+================================+===========+=============================================================+===========+==================+=============+========+==============================================================================================================+
| AmazonCloudWatch               |     21.86 | N/A                                                         | all       | Review           |       10.93 | LOW    | Review usage for AmazonCloudWatch N/A                                                                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | sg-0066b78761a1e0e36                                        | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for sg-0066b78761a1e0e36; check CloudWatch dimensions/region                             |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | subnet-021b48de68b5958ee                                    | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for subnet-021b48de68b5958ee; check CloudWatch dimensions/region                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for subnet-0ee11b98b8dd343ea; check CloudWatch dimensions/region                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | subnet-03497fad2ec0debfe                                    | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for subnet-03497fad2ec0debfe; check CloudWatch dimensions/region                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | subnet-049c6400a665ecdde                                    | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for subnet-049c6400a665ecdde; check CloudWatch dimensions/region                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | i-09c064032c9fca209                                         | us-east-1 | Rightsize (down) |        3.97 | MEDIUM | Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.6%)                                   |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | subnet-0d24a17f3160eae81                                    | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for subnet-0d24a17f3160eae81; check CloudWatch dimensions/region                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| EC2 - Other                    |     13.23 | subnet-08f5537eaa37be271                                    | us-east-1 | Investigate      |           0 | LOW    | No CPU metric found for subnet-08f5537eaa37be271; check CloudWatch dimensions/region                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | infra                                                       | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for infra                                                       |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | sg-0066b78761a1e0e36                                        | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for sg-0066b78761a1e0e36                                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | subnet-021b48de68b5958ee                                    | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for subnet-021b48de68b5958ee                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for subnet-0ee11b98b8dd343ea                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | subnet-03497fad2ec0debfe                                    | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for subnet-03497fad2ec0debfe                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | subnet-049c6400a665ecdde                                    | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for subnet-049c6400a665ecdde                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | devops                                                      | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for devops                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | awscostuserreport                                           | unknown   | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for awscostuserreport                                           |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | i-09c064032c9fca209                                         | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for i-09c064032c9fca209                                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | subnet-0d24a17f3160eae81                                    | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for subnet-0d24a17f3160eae81                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | subnet-08f5537eaa37be271                                    | us-east-1 | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for subnet-08f5537eaa37be271                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Cost Explorer              |     10.49 | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | Review           |        5.25 | LOW    | Review Cost Explorer queries and granularity for vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Elastic Compute Clou... |      2.83 | i-09c064032c9fca209                                         | us-east-1 | Rightsize (down) |        0.85 | MEDIUM | Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.6%)                                   |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Tax                            |      2.25 | N/A                                                         | all       | Review           |        1.12 | LOW    | Review usage for Tax N/A                                                                                     |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Virtual Private Cloud   |      0.33 | N/A                                                         | all       | Review           |        0.16 | LOW    | Review usage for Amazon Virtual Private Cloud N/A                                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Polly                   |      0.03 | N/A                                                         | all       | Review           |        0.01 | LOW    | Review usage for Amazon Polly N/A                                                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Lex                     |      0.01 | N/A                                                         | all       | Review           |        0.01 | LOW    | Review usage for Amazon Lex N/A                                                                              |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Simple Storage Service  |         0 | N/A                                                         | all       | Review Lifecycle |           0 | MEDIUM | Consider lifecycle/archival for N/A                                                                          |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | infra                                                       | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager infra                                                                   |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | sg-0066b78761a1e0e36                                        | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager sg-0066b78761a1e0e36                                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | subnet-021b48de68b5958ee                                    | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager subnet-021b48de68b5958ee                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | Review           |           0 | LOW    | Review usage for AWS Secrets Manager 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager subnet-0ee11b98b8dd343ea                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | subnet-03497fad2ec0debfe                                    | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager subnet-03497fad2ec0debfe                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | subnet-049c6400a665ecdde                                    | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager subnet-049c6400a665ecdde                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | devops                                                      | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager devops                                                                  |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | awscostuserreport                                           | unknown   | Review           |           0 | LOW    | Review usage for AWS Secrets Manager awscostuserreport                                                       |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | i-09c064032c9fca209                                         | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager i-09c064032c9fca209                                                     |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | subnet-0d24a17f3160eae81                                    | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager subnet-0d24a17f3160eae81                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | subnet-08f5537eaa37be271                                    | us-east-1 | Review           |           0 | LOW    | Review usage for AWS Secrets Manager subnet-08f5537eaa37be271                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Secrets Manager            |         0 | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | Review           |           0 | LOW    | Review usage for AWS Secrets Manager vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63             |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Location Service        |         0 | N/A                                                         | all       | Review           |           0 | LOW    | Review usage for Amazon Location Service N/A                                                                 |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Glacier                 |         0 | N/A                                                         | all       | NoCost           |           0 | LOW    | Free Tier / zero-cost Amazon Glacier N/A                                                                     |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | infra                                                       | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue infra                                                                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | sg-0066b78761a1e0e36                                        | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue sg-0066b78761a1e0e36                                                          |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | subnet-021b48de68b5958ee                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue subnet-021b48de68b5958ee                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                          |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue subnet-0ee11b98b8dd343ea                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | subnet-03497fad2ec0debfe                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue subnet-03497fad2ec0debfe                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | subnet-049c6400a665ecdde                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue subnet-049c6400a665ecdde                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | devops                                                      | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue devops                                                                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | awscostuserreport                                           | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue awscostuserreport                                                             |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | i-09c064032c9fca209                                         | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue i-09c064032c9fca209                                                           |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | subnet-0d24a17f3160eae81                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue subnet-0d24a17f3160eae81                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | subnet-08f5537eaa37be271                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue subnet-08f5537eaa37be271                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Glue                       |         0 | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Glue vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63                   |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Simple Notification ... |         0 | N/A                                                         | all       | NoCost           |           0 | LOW    | Free Tier / zero-cost Amazon Simple Notification Service N/A                                                 |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| Amazon Simple Queue Service    |         0 | N/A                                                         | all       | NoCost           |           0 | LOW    | Free Tier / zero-cost Amazon Simple Queue Service N/A                                                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | infra                                                       | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service infra                                                       |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | sg-0066b78761a1e0e36                                        | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service sg-0066b78761a1e0e36                                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | subnet-021b48de68b5958ee                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service subnet-021b48de68b5958ee                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service subnet-0ee11b98b8dd343ea                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | subnet-03497fad2ec0debfe                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service subnet-03497fad2ec0debfe                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | subnet-049c6400a665ecdde                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service subnet-049c6400a665ecdde                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | devops                                                      | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service devops                                                      |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | awscostuserreport                                           | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service awscostuserreport                                           |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | i-09c064032c9fca209                                         | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service i-09c064032c9fca209                                         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | subnet-0d24a17f3160eae81                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service subnet-0d24a17f3160eae81                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | subnet-08f5537eaa37be271                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service subnet-08f5537eaa37be271                                    |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS Key Management Service     |         0 | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS Key Management Service vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | infra                                                       | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation infra                                                               |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | sg-0066b78761a1e0e36                                        | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation sg-0066b78761a1e0e36                                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | subnet-021b48de68b5958ee                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation subnet-021b48de68b5958ee                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation subnet-0ee11b98b8dd343ea                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | subnet-03497fad2ec0debfe                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation subnet-03497fad2ec0debfe                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | subnet-049c6400a665ecdde                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation subnet-049c6400a665ecdde                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | devops                                                      | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation devops                                                              |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | awscostuserreport                                           | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation awscostuserreport                                                   |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | i-09c064032c9fca209                                         | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation i-09c064032c9fca209                                                 |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | subnet-0d24a17f3160eae81                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation subnet-0d24a17f3160eae81                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | subnet-08f5537eaa37be271                                    | us-east-1 | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation subnet-08f5537eaa37be271                                            |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+
| AWS CloudFormation             |         0 | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | NoCost           |           0 | LOW    | Free Tier / zero-cost AWS CloudFormation vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63         |
+--------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+-------------+--------+--------------------------------------------------------------------------------------------------------------+

====== RECOMMENDATION DETAILS ======

📌 Service: AmazonCloudWatch
   Resource : N/A
   Region   : all
   Cost     : $21.86
   Action   : Review (Save ~$10.93, LOW confidence)
   Details  : Review usage for AmazonCloudWatch N/A

📌 Service: EC2 - Other
   Resource : sg-0066b78761a1e0e36
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for sg-0066b78761a1e0e36; check CloudWatch dimensions/region

📌 Service: EC2 - Other
   Resource : subnet-021b48de68b5958ee
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for subnet-021b48de68b5958ee; check CloudWatch dimensions/region

📌 Service: EC2 - Other
   Resource : subnet-0ee11b98b8dd343ea
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for subnet-0ee11b98b8dd343ea; check CloudWatch dimensions/region

📌 Service: EC2 - Other
   Resource : subnet-03497fad2ec0debfe
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for subnet-03497fad2ec0debfe; check CloudWatch dimensions/region

📌 Service: EC2 - Other
   Resource : subnet-049c6400a665ecdde
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for subnet-049c6400a665ecdde; check CloudWatch dimensions/region

📌 Service: EC2 - Other
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $13.23
   Action   : Rightsize (down) (Save ~$3.97, MEDIUM confidence)
   Details  : Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.6%)

📌 Service: EC2 - Other
   Resource : subnet-0d24a17f3160eae81
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for subnet-0d24a17f3160eae81; check CloudWatch dimensions/region

📌 Service: EC2 - Other
   Resource : subnet-08f5537eaa37be271
   Region   : us-east-1
   Cost     : $13.23
   Action   : Investigate (Save ~$0.00, LOW confidence)
   Details  : No CPU metric found for subnet-08f5537eaa37be271; check CloudWatch dimensions/region

📌 Service: AWS Cost Explorer
   Resource : infra
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for infra

📌 Service: AWS Cost Explorer
   Resource : sg-0066b78761a1e0e36
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for sg-0066b78761a1e0e36

📌 Service: AWS Cost Explorer
   Resource : subnet-021b48de68b5958ee
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for subnet-021b48de68b5958ee

📌 Service: AWS Cost Explorer
   Resource : 97e9dfd9-4493-4657-9657-dd17cdb8d4c3
   Region   : unknown
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for 97e9dfd9-4493-4657-9657-dd17cdb8d4c3

📌 Service: AWS Cost Explorer
   Resource : subnet-0ee11b98b8dd343ea
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for subnet-0ee11b98b8dd343ea

📌 Service: AWS Cost Explorer
   Resource : subnet-03497fad2ec0debfe
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for subnet-03497fad2ec0debfe

📌 Service: AWS Cost Explorer
   Resource : subnet-049c6400a665ecdde
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for subnet-049c6400a665ecdde

📌 Service: AWS Cost Explorer
   Resource : devops
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for devops

📌 Service: AWS Cost Explorer
   Resource : awscostuserreport
   Region   : unknown
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for awscostuserreport

📌 Service: AWS Cost Explorer
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for i-09c064032c9fca209

📌 Service: AWS Cost Explorer
   Resource : subnet-0d24a17f3160eae81
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for subnet-0d24a17f3160eae81

📌 Service: AWS Cost Explorer
   Resource : subnet-08f5537eaa37be271
   Region   : us-east-1
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for subnet-08f5537eaa37be271

📌 Service: AWS Cost Explorer
   Resource : vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63
   Region   : unknown
   Cost     : $10.49
   Action   : Review (Save ~$5.25, LOW confidence)
   Details  : Review Cost Explorer queries and granularity for vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63

📌 Service: Amazon Elastic Compute Cloud - Compute
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $2.83
   Action   : Rightsize (down) (Save ~$0.85, MEDIUM confidence)
   Details  : Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.6%)

📌 Service: Tax
   Resource : N/A
   Region   : all
   Cost     : $2.25
   Action   : Review (Save ~$1.12, LOW confidence)
   Details  : Review usage for Tax N/A

📌 Service: Amazon Virtual Private Cloud
   Resource : N/A
   Region   : all
   Cost     : $0.33
   Action   : Review (Save ~$0.16, LOW confidence)
   Details  : Review usage for Amazon Virtual Private Cloud N/A

📌 Service: Amazon Polly
   Resource : N/A
   Region   : all
   Cost     : $0.03
   Action   : Review (Save ~$0.01, LOW confidence)
   Details  : Review usage for Amazon Polly N/A

📌 Service: Amazon Lex
   Resource : N/A
   Region   : all
   Cost     : $0.01
   Action   : Review (Save ~$0.01, LOW confidence)
   Details  : Review usage for Amazon Lex N/A

📌 Service: Amazon Simple Storage Service
   Resource : N/A
   Region   : all
   Cost     : $0.00
   Action   : Review Lifecycle (Save ~$0.00, MEDIUM confidence)
   Details  : Consider lifecycle/archival for N/A

📌 Service: AWS Secrets Manager
   Resource : infra
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager infra

📌 Service: AWS Secrets Manager
   Resource : sg-0066b78761a1e0e36
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager sg-0066b78761a1e0e36

📌 Service: AWS Secrets Manager
   Resource : subnet-021b48de68b5958ee
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager subnet-021b48de68b5958ee

📌 Service: AWS Secrets Manager
   Resource : 97e9dfd9-4493-4657-9657-dd17cdb8d4c3
   Region   : unknown
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager 97e9dfd9-4493-4657-9657-dd17cdb8d4c3

📌 Service: AWS Secrets Manager
   Resource : subnet-0ee11b98b8dd343ea
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager subnet-0ee11b98b8dd343ea

📌 Service: AWS Secrets Manager
   Resource : subnet-03497fad2ec0debfe
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager subnet-03497fad2ec0debfe

📌 Service: AWS Secrets Manager
   Resource : subnet-049c6400a665ecdde
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager subnet-049c6400a665ecdde

📌 Service: AWS Secrets Manager
   Resource : devops
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager devops

📌 Service: AWS Secrets Manager
   Resource : awscostuserreport
   Region   : unknown
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager awscostuserreport

📌 Service: AWS Secrets Manager
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager i-09c064032c9fca209

📌 Service: AWS Secrets Manager
   Resource : subnet-0d24a17f3160eae81
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager subnet-0d24a17f3160eae81

📌 Service: AWS Secrets Manager
   Resource : subnet-08f5537eaa37be271
   Region   : us-east-1
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager subnet-08f5537eaa37be271

📌 Service: AWS Secrets Manager
   Resource : vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63
   Region   : unknown
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for AWS Secrets Manager vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63

📌 Service: Amazon Location Service
   Resource : N/A
   Region   : all
   Cost     : $0.00
   Action   : Review (Save ~$0.00, LOW confidence)
   Details  : Review usage for Amazon Location Service N/A

📌 Service: Amazon Glacier
   Resource : N/A
   Region   : all
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost Amazon Glacier N/A

📌 Service: AWS Glue
   Resource : infra
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue infra

📌 Service: AWS Glue
   Resource : sg-0066b78761a1e0e36
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue sg-0066b78761a1e0e36

📌 Service: AWS Glue
   Resource : subnet-021b48de68b5958ee
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue subnet-021b48de68b5958ee

📌 Service: AWS Glue
   Resource : 97e9dfd9-4493-4657-9657-dd17cdb8d4c3
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue 97e9dfd9-4493-4657-9657-dd17cdb8d4c3

📌 Service: AWS Glue
   Resource : subnet-0ee11b98b8dd343ea
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue subnet-0ee11b98b8dd343ea

📌 Service: AWS Glue
   Resource : subnet-03497fad2ec0debfe
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue subnet-03497fad2ec0debfe

📌 Service: AWS Glue
   Resource : subnet-049c6400a665ecdde
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue subnet-049c6400a665ecdde

📌 Service: AWS Glue
   Resource : devops
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue devops

📌 Service: AWS Glue
   Resource : awscostuserreport
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue awscostuserreport

📌 Service: AWS Glue
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue i-09c064032c9fca209

📌 Service: AWS Glue
   Resource : subnet-0d24a17f3160eae81
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue subnet-0d24a17f3160eae81

📌 Service: AWS Glue
   Resource : subnet-08f5537eaa37be271
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue subnet-08f5537eaa37be271

📌 Service: AWS Glue
   Resource : vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Glue vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63

📌 Service: Amazon Simple Notification Service
   Resource : N/A
   Region   : all
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost Amazon Simple Notification Service N/A

📌 Service: Amazon Simple Queue Service
   Resource : N/A
   Region   : all
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost Amazon Simple Queue Service N/A

📌 Service: AWS Key Management Service
   Resource : infra
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service infra

📌 Service: AWS Key Management Service
   Resource : sg-0066b78761a1e0e36
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service sg-0066b78761a1e0e36

📌 Service: AWS Key Management Service
   Resource : subnet-021b48de68b5958ee
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service subnet-021b48de68b5958ee

📌 Service: AWS Key Management Service
   Resource : 97e9dfd9-4493-4657-9657-dd17cdb8d4c3
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service 97e9dfd9-4493-4657-9657-dd17cdb8d4c3

📌 Service: AWS Key Management Service
   Resource : subnet-0ee11b98b8dd343ea
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service subnet-0ee11b98b8dd343ea

📌 Service: AWS Key Management Service
   Resource : subnet-03497fad2ec0debfe
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service subnet-03497fad2ec0debfe

📌 Service: AWS Key Management Service
   Resource : subnet-049c6400a665ecdde
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service subnet-049c6400a665ecdde

📌 Service: AWS Key Management Service
   Resource : devops
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service devops

📌 Service: AWS Key Management Service
   Resource : awscostuserreport
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service awscostuserreport

📌 Service: AWS Key Management Service
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service i-09c064032c9fca209

📌 Service: AWS Key Management Service
   Resource : subnet-0d24a17f3160eae81
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service subnet-0d24a17f3160eae81

📌 Service: AWS Key Management Service
   Resource : subnet-08f5537eaa37be271
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service subnet-08f5537eaa37be271

📌 Service: AWS Key Management Service
   Resource : vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS Key Management Service vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63

📌 Service: AWS CloudFormation
   Resource : infra
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation infra

📌 Service: AWS CloudFormation
   Resource : sg-0066b78761a1e0e36
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation sg-0066b78761a1e0e36

📌 Service: AWS CloudFormation
   Resource : subnet-021b48de68b5958ee
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation subnet-021b48de68b5958ee

📌 Service: AWS CloudFormation
   Resource : 97e9dfd9-4493-4657-9657-dd17cdb8d4c3
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation 97e9dfd9-4493-4657-9657-dd17cdb8d4c3

📌 Service: AWS CloudFormation
   Resource : subnet-0ee11b98b8dd343ea
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation subnet-0ee11b98b8dd343ea

📌 Service: AWS CloudFormation
   Resource : subnet-03497fad2ec0debfe
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation subnet-03497fad2ec0debfe

📌 Service: AWS CloudFormation
   Resource : subnet-049c6400a665ecdde
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation subnet-049c6400a665ecdde

📌 Service: AWS CloudFormation
   Resource : devops
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation devops

📌 Service: AWS CloudFormation
   Resource : awscostuserreport
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation awscostuserreport

📌 Service: AWS CloudFormation
   Resource : i-09c064032c9fca209
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation i-09c064032c9fca209

📌 Service: AWS CloudFormation
   Resource : subnet-0d24a17f3160eae81
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation subnet-0d24a17f3160eae81

📌 Service: AWS CloudFormation
   Resource : subnet-08f5537eaa37be271
   Region   : us-east-1
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation subnet-08f5537eaa37be271

📌 Service: AWS CloudFormation
   Resource : vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63
   Region   : unknown
   Cost     : $0.00
   Action   : NoCost (Save ~$0.00, LOW confidence)
   Details  : Free Tier / zero-cost AWS CloudFormation vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63

=============================================================================================JSONfile optimization ===========================================================
ubuntu@ip-172-31-32-78:~/test$ cat ./outputs/aws_optimization_report_20250922_122254.json
{
  "generated_at": "2025-09-22T12:22:53.644382Z",
  "period": {
    "start": "2025-08-23",
    "end": "2025-09-22"
  },
  "total_cost": 51.03,
  "services": {
    "AmazonCloudWatch": {
      "cost": 21.8645,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for AmazonCloudWatch N/A",
          "estimated_savings": 10.93,
          "confidence": "LOW"
        }
      ]
    },
    "EC2 - Other": {
      "cost": 13.2284,
      "recommendations": [
        {
          "resource": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for sg-0066b78761a1e0e36; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-021b48de68b5958ee; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-0ee11b98b8dd343ea; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-03497fad2ec0debfe; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-049c6400a665ecdde; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Rightsize (down)",
          "details": "Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.6%)",
          "estimated_savings": 3.97,
          "confidence": "MEDIUM"
        },
        {
          "resource": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-0d24a17f3160eae81; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-08f5537eaa37be271; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "AWS Cost Explorer": {
      "cost": 10.49,
      "recommendations": [
        {
          "resource": "infra",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for infra",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for sg-0066b78761a1e0e36",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for subnet-021b48de68b5958ee",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for subnet-0ee11b98b8dd343ea",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for subnet-03497fad2ec0debfe",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for subnet-049c6400a665ecdde",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "devops",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for devops",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "awscostuserreport",
          "region": "unknown",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for awscostuserreport",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for i-09c064032c9fca209",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for subnet-0d24a17f3160eae81",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for subnet-08f5537eaa37be271",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "Review",
          "details": "Review Cost Explorer queries and granularity for vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Elastic Compute Cloud - Compute": {
      "cost": 2.8269,
      "recommendations": [
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Rightsize (down)",
          "details": "Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.6%)",
          "estimated_savings": 0.85,
          "confidence": "MEDIUM"
        }
      ]
    },
    "Tax": {
      "cost": 2.25,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Tax N/A",
          "estimated_savings": 1.12,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Virtual Private Cloud": {
      "cost": 0.3286,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Virtual Private Cloud N/A",
          "estimated_savings": 0.16,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Polly": {
      "cost": 0.0266,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Polly N/A",
          "estimated_savings": 0.01,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Lex": {
      "cost": 0.0135,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Lex N/A",
          "estimated_savings": 0.01,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Simple Storage Service": {
      "cost": 0.0024,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review Lifecycle",
          "details": "Consider lifecycle/archival for N/A",
          "estimated_savings": 0.0,
          "confidence": "MEDIUM"
        }
      ]
    },
    "AWS Secrets Manager": {
      "cost": 0.0005,
      "recommendations": [
        {
          "resource": "infra",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "devops",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "awscostuserreport",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Location Service": {
      "cost": 0.0005,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Location Service N/A",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Glacier": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "NoCost",
          "details": "Free Tier / zero-cost Amazon Glacier N/A",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "AWS Glue": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource": "infra",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "devops",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "awscostuserreport",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Simple Notification Service": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "NoCost",
          "details": "Free Tier / zero-cost Amazon Simple Notification Service N/A",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Simple Queue Service": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource": "N/A",
          "region": "all",
          "action": "NoCost",
          "details": "Free Tier / zero-cost Amazon Simple Queue Service N/A",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "AWS Key Management Service": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource": "infra",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "devops",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "awscostuserreport",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "AWS CloudFormation": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource": "infra",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "devops",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "awscostuserreport",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    }
  }
}ubuntu@ip-172-31-32-78:~/test$

