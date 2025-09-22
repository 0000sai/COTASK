ubuntu@ip-172-31-32-78:~/test$ cat costoptimization.py
#!/usr/bin/env python3
"""
costoptimization.py

- Discovers tagged resources (Resource Groups Tagging API).
- Fetches costs via Cost Explorer (handles NextPageToken).
- Probes CloudWatch for basic metrics (EC2, RDS, Lambda heuristics).
- Produces recommendations (Stop/Delete/Rightsize/Optimize) including EC2 rightsizing.
- Flags Free Tier / zero-cost resources.
- Saves JSON report to ./outputs/
"""
from datetime import datetime, timedelta
import json
import logging
import os
import sys

import boto3
from botocore.exceptions import ClientError
from tabulate import tabulate

# ----------------------------
# Config
# ----------------------------
LOG_LEVEL = logging.INFO
REPORT_DIR = "./outputs"
os.makedirs(REPORT_DIR, exist_ok=True)

# A comprehensive service list (lowercase tokens)
valid_services = [
    'accessanalyzer', 'account', 'acm', 'acm-pca', 'aiops', 'amp', 'amplify', 'amplifybackend',
    'amplifyuibuilder', 'apigateway', 'apigatewaymanagementapi', 'apigatewayv2', 'appconfig',
    'appconfigdata', 'appfabric', 'appflow', 'appintegrations', 'application-autoscaling',
    'application-insights', 'application-signals', 'applicationcostprofiler', 'appmesh',
    'apprunner', 'appstream', 'appsync', 'apptest', 'arc-region-switch', 'arc-zonal-shift',
    'artifact', 'athena', 'auditmanager', 'autoscaling', 'autoscaling-plans', 'b2bi', 'backup',
    'backup-gateway', 'backupsearch', 'batch', 'bcm-dashboards', 'bcm-data-exports',
    'bcm-pricing-calculator', 'bcm-recommended-actions', 'bedrock', 'bedrock-agent',
    'bedrock-agent-runtime', 'bedrock-agentcore', 'bedrock-agentcore-control',
    'bedrock-data-automation', 'bedrock-data-automation-runtime', 'bedrock-runtime', 'billing',
    'billingconductor', 'braket', 'budgets', 'ce', 'chatbot', 'chime', 'chime-sdk-identity',
    'chime-sdk-media-pipelines', 'chime-sdk-meetings', 'chime-sdk-messaging', 'chime-sdk-voice',
    'cleanrooms', 'cleanroomsml', 'cloud9', 'cloudcontrol', 'clouddirectory', 'cloudformation',
    'cloudfront', 'cloudfront-keyvaluestore', 'cloudhsm', 'cloudhsmv2', 'cloudsearch',
    'cloudsearchdomain', 'cloudtrail', 'cloudtrail-data', 'cloudwatch', 'codeartifact',
    'codebuild', 'codecatalyst', 'codecommit', 'codeconnections', 'codedeploy',
    'codeguru-reviewer', 'codeguru-security', 'codeguruprofiler', 'codepipeline',
    'codestar-connections', 'codestar-notifications', 'cognito-identity', 'cognito-idp',
    'cognito-sync', 'comprehend', 'comprehendmedical', 'compute-optimizer', 'config', 'connect',
    'connect-contact-lens', 'connectcampaigns', 'connectcampaignsv2', 'connectcases',
    'connectparticipant', 'controlcatalog', 'controltower', 'cost-optimization-hub', 'cur',
    'customer-profiles', 'databrew', 'dataexchange', 'datapipeline', 'datasync', 'datazone',
    'dax', 'deadline', 'detective', 'devicefarm', 'devops-guru', 'directconnect', 'discovery',
    'dlm', 'dms', 'docdb', 'docdb-elastic', 'drs', 'ds', 'ds-data', 'dsql', 'dynamodb',
    'dynamodbstreams', 'ebs', 'ec2', 'ec2-instance-connect', 'ecr', 'ecr-public', 'ecs', 'efs',
    'eks', 'eks-auth', 'elasticache', 'elasticbeanstalk', 'elastictranscoder', 'elb', 'elbv2',
    'emr', 'emr-containers', 'emr-serverless', 'entityresolution', 'es', 'events', 'evidently',
    'evs', 'finspace', 'finspace-data', 'firehose', 'fis', 'fms', 'forecast', 'forecastquery',
    'frauddetector', 'freetier', 'fsx', 'gamelift', 'gameliftstreams', 'geo-maps', 'geo-places',
    'geo-routes', 'glacier', 'globalaccelerator', 'glue', 'grafana', 'greengrass',
    'greengrassv2', 'groundstation', 'guardduty', 'health', 'healthlake', 'iam', 'identitystore',
    'imagebuilder', 'importexport', 'inspector', 'inspector-scan', 'inspector2',
    'internetmonitor', 'invoicing', 'iot', 'iot-data', 'iot-jobs-data',
    'iot-managed-integrations', 'iotanalytics', 'iotdeviceadvisor', 'iotevents',
    'iotevents-data', 'iotfleethub', 'iotfleetwise', 'iotsecuretunneling', 'iotsitewise',
    'iotthingsgraph', 'iottwinmaker', 'iotwireless', 'ivs', 'ivs-realtime', 'ivschat', 'kafka',
    'kafkaconnect', 'kendra', 'kendra-ranking', 'keyspaces', 'keyspacesstreams', 'kinesis',
    'kinesis-video-archived-media', 'kinesis-video-media', 'kinesis-video-signaling',
    'kinesis-video-webrtc-storage', 'kinesisanalytics', 'kinesisanalyticsv2', 'kinesisvideo',
    'kms', 'lakeformation', 'lambda', 'launch-wizard', 'lex-models', 'lex-runtime',
    'lexv2-models', 'lexv2-runtime', 'license-manager', 'license-manager-linux-subscriptions',
    'license-manager-user-subscriptions', 'lightsail', 'location', 'logs', 'lookoutequipment',
    'lookoutmetrics', 'lookoutvision', 'm2', 'machinelearning', 'macie2', 'mailmanager',
    'managedblockchain', 'managedblockchain-query', 'marketplace-agreement',
    'marketplace-catalog', 'marketplace-deployment', 'marketplace-entitlement',
    'marketplace-reporting', 'marketplacecommerceanalytics', 'mediaconnect', 'mediaconvert',
    'medialive', 'mediapackage', 'mediapackage-vod', 'mediapackagev2', 'mediastore',
    'mediastore-data', 'mediatailor', 'medical-imaging', 'memorydb', 'meteringmarketplace',
    'mgh', 'mgn', 'migration-hub-refactor-spaces', 'migrationhub-config',
    'migrationhuborchestrator', 'migrationhubstrategy', 'mpa', 'mq', 'mturk', 'mwaa', 'neptune',
    'neptune-graph', 'neptunedata', 'network-firewall', 'networkflowmonitor', 'networkmanager',
    'networkmonitor', 'notifications', 'notificationscontacts', 'oam', 'observabilityadmin',
    'odb', 'omics', 'opensearch', 'opensearchserverless', 'organizations', 'osis', 'outposts',
    'panorama', 'partnercentral-selling', 'payment-cryptography', 'payment-cryptography-data',
    'pca-connector-ad', 'pca-connector-scep', 'pcs', 'personalize', 'personalize-events',
    'personalize-runtime', 'pi', 'pinpoint', 'pinpoint-email', 'pinpoint-sms-voice',
    'pinpoint-sms-voice-v2', 'pipes', 'polly', 'pricing', 'proton', 'qapps', 'qbusiness',
    'qconnect', 'qldb', 'qldb-session', 'quicksight', 'ram', 'rbin', 'rds', 'rds-data',
    'redshift', 'redshift-data', 'redshift-serverless', 'rekognition', 'repostspace',
    'resiliencehub', 'resource-explorer-2', 'resource-groups', 'resourcegroupstaggingapi',
    'robomaker', 'rolesanywhere', 'route53', 'route53-recovery-cluster',
    'route53-recovery-control-config', 'route53-recovery-readiness', 'route53domains',
    'route53profiles', 'route53resolver', 'rum', 's3', 's3control', 's3outposts', 's3tables',
    's3vectors', 'sagemaker', 'sagemaker-a2i-runtime', 'sagemaker-edge',
    'sagemaker-featurestore-runtime', 'sagemaker-geospatial', 'sagemaker-metrics',
    'sagemaker-runtime', 'savingsplans', 'scheduler', 'schemas', 'sdb', 'secretsmanager',
    'security-ir', 'securityhub', 'securitylake', 'serverlessrepo', 'service-quotas',
    'servicecatalog', 'servicecatalog-appregistry', 'servicediscovery', 'ses', 'sesv2',
    'shield', 'signer', 'simspaceweaver', 'sms-voice', 'snow-device-management', 'snowball',
    'sns', 'socialmessaging', 'sqs', 'ssm', 'ssm-contacts', 'ssm-guiconnect', 'ssm-incidents',
    'ssm-quicksetup', 'ssm-sap', 'sso', 'sso-admin', 'sso-oidc', 'stepfunctions',
    'storagegateway', 'sts', 'supplychain', 'support', 'support-app', 'swf', 'synthetics',
    'taxsettings', 'textract', 'timestream-influxdb', 'timestream-query', 'timestream-write',
    'tnb', 'transcribe', 'transfer', 'translate', 'trustedadvisor', 'verifiedpermissions',
    'voice-id', 'vpc-lattice', 'waf', 'waf-regional', 'wafv2', 'wellarchitected', 'wisdom',
    'workdocs', 'workmail', 'workmailmessageflow', 'workspaces', 'workspaces-instances',
    'workspaces-thin-client', 'workspaces-web', 'xray'
]

# Logging
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("costopt")

# ----------------------------
# Helpers
# ----------------------------
def iso_date(dt):
    return dt.strftime("%Y-%m-%d")

def timestamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

# ----------------------------
# Regions
# ----------------------------
def get_all_regions():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    try:
        regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
        log.info("Found %d regions", len(regions))
        return regions
    except Exception as e:
        log.warning("Couldn't list regions, defaulting to us-east-1: %s", e)
        return ['us-east-1']

# ----------------------------
# Discover tagged resources (Resource Groups Tagging API)
# ----------------------------
def discover_tagged_resources(max_pages=None):
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
def get_costs_by_service(start_date, end_date):
    ce = boto3.client('ce', region_name='us-east-1')  # CE is global
    cost_by_service = {}
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
        # parse results
        for rbt in resp.get('ResultsByTime', []):
            for grp in rbt.get('Groups', []):
                keys = grp.get('Keys', [])
                amt = 0.0
                try:
                    amt = float(grp.get('Metrics', {}).get('UnblendedCost', {}).get('Amount', 0.0))
                except Exception:
                    amt = 0.0
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
def probe_cloudwatch_average(namespace, metric_name, dim_name, dim_value, start_time, end_time, region):
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
    except ClientError:
        return 0.0
    except Exception:
        return 0.0

def get_usage_for_resource(service_short, resource_id, start_time, end_time, region_hint=None):
    usage = {}
    is_unused = True
    region = region_hint or 'us-east-1'
    try:
        if service_short in ('ec2', 'ec2-instance-connect'):
            cpu = probe_cloudwatch_average('AWS/EC2', 'CPUUtilization', 'InstanceId', resource_id, start_time, end_time, region)
            usage['cpu_util'] = cpu
            if cpu > 0:
                is_unused = False
        elif service_short == 'rds':
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
            pass
    except Exception as e:
        log.debug("get_usage_for_resource error for %s %s: %s", service_short, resource_id, e)
    return is_unused, usage

# ----------------------------
# Recommendation heuristics
# ----------------------------
def recommend_by_service_and_usage(service_display, resource_id, usage, cost):
    svc = (service_display or '').lower()
    if cost == 0:
        return {'action': 'NoCost', 'details': f"Free Tier / zero-cost {service_display} {resource_id}", 'estimated_savings': 0.0, 'confidence': 'LOW'}
    if 'elastic compute' in svc or 'ec2' in svc:
        cpu = usage.get('cpu_util')
        if cpu is None:
            return {'action': 'Investigate', 'details': f"No CPU metric found for {resource_id}; check CloudWatch dimensions/region", 'estimated_savings': 0.0, 'confidence': 'LOW'}
        if cpu == 0:
            return {'action': 'Stop/Delete', 'details': f"No CPU activity for instance {resource_id}", 'estimated_savings': cost, 'confidence': 'HIGH'}
        if cpu < 20:
            return {'action': 'Rightsize (down)', 'details': f"Recommend downsize instance {resource_id} to t3.micro (avg CPU {cpu:.1f}%)", 'estimated_savings': round(cost * 0.30, 2), 'confidence': 'MEDIUM'}
        if cpu > 80:
            return {'action': 'Upsize', 'details': f"High CPU ({cpu:.1f}%) on {resource_id} — consider larger instance", 'estimated_savings': 0.0, 'confidence': 'MEDIUM'}
        return {'action': 'Keep/Optimize', 'details': f"Instance {resource_id} shows avg CPU {cpu:.1f}%", 'estimated_savings': round(cost * 0.05, 2), 'confidence': 'LOW'}
    if 'lambda' in svc:
        inv = usage.get('invocations', 0)
        if inv == 0:
            return {'action': 'Delete', 'details': f"No invocations for function {resource_id}", 'estimated_savings': cost, 'confidence': 'HIGH'}
        return {'action': 'Optimize', 'details': f"{inv} invocations (consider tuning memory/timeout)", 'estimated_savings': round(cost * 0.1, 2), 'confidence': 'LOW'}
    if 's3' in svc or 'simple storage' in svc or 'glacier' in svc:
        if cost == 0:
            return {'action': 'NoCost', 'details': f"Free Tier / zero-cost storage {resource_id}", 'estimated_savings': 0.0, 'confidence': 'LOW'}
        return {'action': 'Review Lifecycle', 'details': f"Consider lifecycle/archival for {resource_id}", 'estimated_savings': round(cost * 0.5, 2), 'confidence': 'MEDIUM'}
    return {'action': 'Review', 'details': f"Review usage for {service_display} {resource_id}", 'estimated_savings': round(min(cost * 0.5, cost), 2), 'confidence': 'LOW'}

# ----------------------------
# Build recommendations
# ----------------------------
def build_recommendations(period_days=30, tag_pages_limit=10):
    now = datetime.utcnow()
    start = now - timedelta(days=period_days)
    start_date = iso_date(start)
    end_date = iso_date(now)
    log.info("Building recommendations for period %s -> %s", start_date, end_date)

    regions = get_all_regions()
    tagged = discover_tagged_resources(max_pages=tag_pages_limit)

    # fetch costs (service-level)
    costs = get_costs_by_service(start_date, end_date)

    # build resource map keyed by simple resource name (last ARN part)
    resource_map = {}
    for r in tagged:
        arn = r.get('arn')
        if not arn:
            continue
        rid = arn.split(':')[-1].split('/')[-1]
        resource_map.setdefault(rid, []).append(r)

    report = {'generated_at': now.isoformat() + 'Z', 'period': {'start': start_date, 'end': end_date}, 'services': {}}

    for svc_display, svc_cost in costs.items():
        report['services'].setdefault(svc_display, {'cost': round(svc_cost, 4), 'recommendations': []})
        matched = False
        for rid, entries in list(resource_map.items())[:500]:
            lower = svc_display.lower()
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
                report['services'][svc_display]['recommendations'].append({'resource_id': rid, 'region': arn_region or 'unknown', **rec})
            else:
                try:
                    arn_lower = entries[0]['arn'].lower()
                    token = svc_display.lower().split()[0]
                    if token in arn_lower:
                        matched = True
                        arn_region = None
                        try:
                            arn = entries[0]['arn']
                            parts = arn.split(':')
                            if len(parts) > 3 and parts[3]:
                                arn_region = parts[3]
                        except Exception:
                            arn_region = None
                        is_unused, usage = True, {}
                        rec = recommend_by_service_and_usage(svc_display, rid, usage, svc_cost)
                        report['services'][svc_display]['recommendations'].append({'resource_id': rid, 'region': arn_region or 'unknown', **rec})
                except Exception:
                    continue
        if not matched:
            rec = recommend_by_service_and_usage(svc_display, 'N/A', {}, svc_cost)
            report['services'][svc_display]['recommendations'].append({'resource_id': 'N/A', 'region': 'all', **rec})

    return report

# ----------------------------
# Output helpers
# ----------------------------
def print_report_table(report):
    rows = []
    headers = ["Service", "Cost($)", "Resource", "Region", "Action", "Details", "EstSavings($)", "Confidence"]
    for svc, info in report.get('services', {}).items():
        cost = info.get('cost', 0)
        for rec in info.get('recommendations', []):
            rows.append([
                svc,
                f"{cost:.2f}",
                rec.get('resource_id'),
                rec.get('region'),
                rec.get('action'),
                rec.get('details'),
                f"{rec.get('estimated_savings', 0):.2f}",
                rec.get('confidence')
            ])
    if rows:
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    else:
        print("No recommendations generated.")

def save_report_json(report, prefix="aws_optimization_report"):
    fn = os.path.join(REPORT_DIR, f"{prefix}_{timestamp()}.json")
    try:
        with open(fn, 'w') as fh:
            json.dump(report, fh, indent=2, default=str)
        log.info("Saved report to %s", fn)
        return fn
    except Exception as e:
        log.error("Failed to save report: %s", e)
        return None

# ----------------------------
# Entrypoint
# ----------------------------
def main():
    try:
        report = build_recommendations(period_days=30, tag_pages_limit=20)
        print_report_table(report)
        save_report_json(report)
    except Exception as e:
        log.exception("Run failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()

========================================================================OUTPUT============================================================================
ubuntu@ip-172-31-32-78:~/test$ ./costoptimization.py
2025-09-22 12:37:15,310 INFO Building recommendations for period 2025-08-23 -> 2025-09-22
2025-09-22 12:37:15,322 INFO Found credentials in shared credentials file: ~/.aws/credentials
2025-09-22 12:37:15,573 INFO Found 18 regions
2025-09-22 12:37:15,695 INFO Discovered 13 tagged resources
2025-09-22 12:37:15,982 INFO Aggregated costs for 17 services
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Service                                |   Cost($) | Resource                                                    | Region    | Action           | Details                                                                                                      |   EstSavings($) | Confidence   |
+========================================+===========+=============================================================+===========+==================+==============================================================================================================+=================+==============+
| AWS Glue                               |      0    | infra                                                       | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue infra                                                                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | sg-0066b78761a1e0e36                                        | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue sg-0066b78761a1e0e36                                                          |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | subnet-021b48de68b5958ee                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue subnet-021b48de68b5958ee                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | NoCost           | Free Tier / zero-cost AWS Glue 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                          |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | subnet-0ee11b98b8dd343ea                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue subnet-0ee11b98b8dd343ea                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | subnet-03497fad2ec0debfe                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue subnet-03497fad2ec0debfe                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | subnet-049c6400a665ecdde                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue subnet-049c6400a665ecdde                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | devops                                                      | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue devops                                                                        |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | awscostuserreport                                           | unknown   | NoCost           | Free Tier / zero-cost AWS Glue awscostuserreport                                                             |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | i-09c064032c9fca209                                         | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue i-09c064032c9fca209                                                           |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | subnet-0d24a17f3160eae81                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue subnet-0d24a17f3160eae81                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | subnet-08f5537eaa37be271                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Glue subnet-08f5537eaa37be271                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Glue                               |      0    | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | NoCost           | Free Tier / zero-cost AWS Glue vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63                   |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | sg-0066b78761a1e0e36                                        | us-east-1 | Investigate      | No CPU metric found for sg-0066b78761a1e0e36; check CloudWatch dimensions/region                             |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | subnet-021b48de68b5958ee                                    | us-east-1 | Investigate      | No CPU metric found for subnet-021b48de68b5958ee; check CloudWatch dimensions/region                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | Investigate      | No CPU metric found for subnet-0ee11b98b8dd343ea; check CloudWatch dimensions/region                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | subnet-03497fad2ec0debfe                                    | us-east-1 | Investigate      | No CPU metric found for subnet-03497fad2ec0debfe; check CloudWatch dimensions/region                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | subnet-049c6400a665ecdde                                    | us-east-1 | Investigate      | No CPU metric found for subnet-049c6400a665ecdde; check CloudWatch dimensions/region                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | i-09c064032c9fca209                                         | us-east-1 | Rightsize (down) | Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.5%)                                   |            3.97 | MEDIUM       |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | subnet-0d24a17f3160eae81                                    | us-east-1 | Investigate      | No CPU metric found for subnet-0d24a17f3160eae81; check CloudWatch dimensions/region                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| EC2 - Other                            |     13.23 | subnet-08f5537eaa37be271                                    | us-east-1 | Investigate      | No CPU metric found for subnet-08f5537eaa37be271; check CloudWatch dimensions/region                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Location Service                |      0    | N/A                                                         | all       | Review           | Review usage for Amazon Location Service N/A                                                                 |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Simple Notification Service     |      0    | N/A                                                         | all       | NoCost           | Free Tier / zero-cost Amazon Simple Notification Service N/A                                                 |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Simple Queue Service            |      0    | N/A                                                         | all       | NoCost           | Free Tier / zero-cost Amazon Simple Queue Service N/A                                                        |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Simple Storage Service          |      0    | N/A                                                         | all       | Review Lifecycle | Consider lifecycle/archival for N/A                                                                          |            0    | MEDIUM       |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AmazonCloudWatch                       |     21.86 | N/A                                                         | all       | Review           | Review usage for AmazonCloudWatch N/A                                                                        |           10.93 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | infra                                                       | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service infra                                                       |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | sg-0066b78761a1e0e36                                        | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service sg-0066b78761a1e0e36                                        |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | subnet-021b48de68b5958ee                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service subnet-021b48de68b5958ee                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | NoCost           | Free Tier / zero-cost AWS Key Management Service 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | subnet-0ee11b98b8dd343ea                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service subnet-0ee11b98b8dd343ea                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | subnet-03497fad2ec0debfe                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service subnet-03497fad2ec0debfe                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | subnet-049c6400a665ecdde                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service subnet-049c6400a665ecdde                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | devops                                                      | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service devops                                                      |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | awscostuserreport                                           | unknown   | NoCost           | Free Tier / zero-cost AWS Key Management Service awscostuserreport                                           |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | i-09c064032c9fca209                                         | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service i-09c064032c9fca209                                         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | subnet-0d24a17f3160eae81                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service subnet-0d24a17f3160eae81                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | subnet-08f5537eaa37be271                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS Key Management Service subnet-08f5537eaa37be271                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Key Management Service             |      0    | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | NoCost           | Free Tier / zero-cost AWS Key Management Service vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | infra                                                       | us-east-1 | Review           | Review usage for AWS Secrets Manager infra                                                                   |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | sg-0066b78761a1e0e36                                        | us-east-1 | Review           | Review usage for AWS Secrets Manager sg-0066b78761a1e0e36                                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | subnet-021b48de68b5958ee                                    | us-east-1 | Review           | Review usage for AWS Secrets Manager subnet-021b48de68b5958ee                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | Review           | Review usage for AWS Secrets Manager 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                    |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | subnet-0ee11b98b8dd343ea                                    | us-east-1 | Review           | Review usage for AWS Secrets Manager subnet-0ee11b98b8dd343ea                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | subnet-03497fad2ec0debfe                                    | us-east-1 | Review           | Review usage for AWS Secrets Manager subnet-03497fad2ec0debfe                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | subnet-049c6400a665ecdde                                    | us-east-1 | Review           | Review usage for AWS Secrets Manager subnet-049c6400a665ecdde                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | devops                                                      | us-east-1 | Review           | Review usage for AWS Secrets Manager devops                                                                  |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | awscostuserreport                                           | unknown   | Review           | Review usage for AWS Secrets Manager awscostuserreport                                                       |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | i-09c064032c9fca209                                         | us-east-1 | Review           | Review usage for AWS Secrets Manager i-09c064032c9fca209                                                     |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | subnet-0d24a17f3160eae81                                    | us-east-1 | Review           | Review usage for AWS Secrets Manager subnet-0d24a17f3160eae81                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | subnet-08f5537eaa37be271                                    | us-east-1 | Review           | Review usage for AWS Secrets Manager subnet-08f5537eaa37be271                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Secrets Manager                    |      0    | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | Review           | Review usage for AWS Secrets Manager vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63             |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Lex                             |      0.01 | N/A                                                         | all       | Review           | Review usage for Amazon Lex N/A                                                                              |            0.01 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Polly                           |      0.03 | N/A                                                         | all       | Review           | Review usage for Amazon Polly N/A                                                                            |            0.01 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Elastic Compute Cloud - Compute |      2.83 | i-09c064032c9fca209                                         | us-east-1 | Rightsize (down) | Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.5%)                                   |            0.85 | MEDIUM       |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Virtual Private Cloud           |      0.33 | N/A                                                         | all       | Review           | Review usage for Amazon Virtual Private Cloud N/A                                                            |            0.16 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Tax                                    |      2.25 | N/A                                                         | all       | Review           | Review usage for Tax N/A                                                                                     |            1.12 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | infra                                                       | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation infra                                                               |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | sg-0066b78761a1e0e36                                        | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation sg-0066b78761a1e0e36                                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | subnet-021b48de68b5958ee                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation subnet-021b48de68b5958ee                                            |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | NoCost           | Free Tier / zero-cost AWS CloudFormation 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | subnet-0ee11b98b8dd343ea                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation subnet-0ee11b98b8dd343ea                                            |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | subnet-03497fad2ec0debfe                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation subnet-03497fad2ec0debfe                                            |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | subnet-049c6400a665ecdde                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation subnet-049c6400a665ecdde                                            |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | devops                                                      | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation devops                                                              |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | awscostuserreport                                           | unknown   | NoCost           | Free Tier / zero-cost AWS CloudFormation awscostuserreport                                                   |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | i-09c064032c9fca209                                         | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation i-09c064032c9fca209                                                 |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | subnet-0d24a17f3160eae81                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation subnet-0d24a17f3160eae81                                            |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | subnet-08f5537eaa37be271                                    | us-east-1 | NoCost           | Free Tier / zero-cost AWS CloudFormation subnet-08f5537eaa37be271                                            |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS CloudFormation                     |      0    | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | NoCost           | Free Tier / zero-cost AWS CloudFormation vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63         |            0    | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | infra                                                       | us-east-1 | Review           | Review usage for AWS Cost Explorer infra                                                                     |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | sg-0066b78761a1e0e36                                        | us-east-1 | Review           | Review usage for AWS Cost Explorer sg-0066b78761a1e0e36                                                      |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | subnet-021b48de68b5958ee                                    | us-east-1 | Review           | Review usage for AWS Cost Explorer subnet-021b48de68b5958ee                                                  |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                        | unknown   | Review           | Review usage for AWS Cost Explorer 97e9dfd9-4493-4657-9657-dd17cdb8d4c3                                      |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | subnet-0ee11b98b8dd343ea                                    | us-east-1 | Review           | Review usage for AWS Cost Explorer subnet-0ee11b98b8dd343ea                                                  |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | subnet-03497fad2ec0debfe                                    | us-east-1 | Review           | Review usage for AWS Cost Explorer subnet-03497fad2ec0debfe                                                  |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | subnet-049c6400a665ecdde                                    | us-east-1 | Review           | Review usage for AWS Cost Explorer subnet-049c6400a665ecdde                                                  |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | devops                                                      | us-east-1 | Review           | Review usage for AWS Cost Explorer devops                                                                    |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | awscostuserreport                                           | unknown   | Review           | Review usage for AWS Cost Explorer awscostuserreport                                                         |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | i-09c064032c9fca209                                         | us-east-1 | Review           | Review usage for AWS Cost Explorer i-09c064032c9fca209                                                       |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | subnet-0d24a17f3160eae81                                    | us-east-1 | Review           | Review usage for AWS Cost Explorer subnet-0d24a17f3160eae81                                                  |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | subnet-08f5537eaa37be271                                    | us-east-1 | Review           | Review usage for AWS Cost Explorer subnet-08f5537eaa37be271                                                  |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| AWS Cost Explorer                      |     10.49 | vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63 | unknown   | Review           | Review usage for AWS Cost Explorer vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63               |            5.25 | LOW          |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
| Amazon Glacier                         |      0    | N/A                                                         | all       | Review Lifecycle | Consider lifecycle/archival for N/A                                                                          |            0    | MEDIUM       |
+----------------------------------------+-----------+-------------------------------------------------------------+-----------+------------------+--------------------------------------------------------------------------------------------------------------+-----------------+--------------+
2025-09-22 12:37:16,236 INFO Saved report to ./outputs/aws_optimization_report_20250922_123716.json
ubuntu@ip-172-31-32-78:~/test$ cat  ./outputs/aws_optimization_report_20250922_123716.json
{
  "generated_at": "2025-09-22T12:37:15.310884Z",
  "period": {
    "start": "2025-08-23",
    "end": "2025-09-22"
  },
  "services": {
    "AWS Glue": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource_id": "infra",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "devops",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "awscostuserreport",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Glue vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "EC2 - Other": {
      "cost": 13.2284,
      "recommendations": [
        {
          "resource_id": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for sg-0066b78761a1e0e36; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-021b48de68b5958ee; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-0ee11b98b8dd343ea; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-03497fad2ec0debfe; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-049c6400a665ecdde; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Rightsize (down)",
          "details": "Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.5%)",
          "estimated_savings": 3.97,
          "confidence": "MEDIUM"
        },
        {
          "resource_id": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-0d24a17f3160eae81; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "Investigate",
          "details": "No CPU metric found for subnet-08f5537eaa37be271; check CloudWatch dimensions/region",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Location Service": {
      "cost": 0.0005,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Location Service N/A",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Simple Notification Service": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource_id": "N/A",
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
          "resource_id": "N/A",
          "region": "all",
          "action": "NoCost",
          "details": "Free Tier / zero-cost Amazon Simple Queue Service N/A",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Simple Storage Service": {
      "cost": 0.0024,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review Lifecycle",
          "details": "Consider lifecycle/archival for N/A",
          "estimated_savings": 0.0,
          "confidence": "MEDIUM"
        }
      ]
    },
    "AmazonCloudWatch": {
      "cost": 21.8645,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for AmazonCloudWatch N/A",
          "estimated_savings": 10.93,
          "confidence": "LOW"
        }
      ]
    },
    "AWS Key Management Service": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource_id": "infra",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "devops",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "awscostuserreport",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS Key Management Service vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "AWS Secrets Manager": {
      "cost": 0.0005,
      "recommendations": [
        {
          "resource_id": "infra",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "devops",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "awscostuserreport",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Secrets Manager vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Lex": {
      "cost": 0.0135,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Lex N/A",
          "estimated_savings": 0.01,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Polly": {
      "cost": 0.0266,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Polly N/A",
          "estimated_savings": 0.01,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Elastic Compute Cloud - Compute": {
      "cost": 2.8269,
      "recommendations": [
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Rightsize (down)",
          "details": "Recommend downsize instance i-09c064032c9fca209 to t3.micro (avg CPU 3.5%)",
          "estimated_savings": 0.85,
          "confidence": "MEDIUM"
        }
      ]
    },
    "Amazon Virtual Private Cloud": {
      "cost": 0.3286,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Amazon Virtual Private Cloud N/A",
          "estimated_savings": 0.16,
          "confidence": "LOW"
        }
      ]
    },
    "Tax": {
      "cost": 2.25,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review",
          "details": "Review usage for Tax N/A",
          "estimated_savings": 1.12,
          "confidence": "LOW"
        }
      ]
    },
    "AWS CloudFormation": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource_id": "infra",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation infra",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation sg-0066b78761a1e0e36",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-021b48de68b5958ee",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-0ee11b98b8dd343ea",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-03497fad2ec0debfe",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-049c6400a665ecdde",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "devops",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation devops",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "awscostuserreport",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation awscostuserreport",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation i-09c064032c9fca209",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-0d24a17f3160eae81",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation subnet-08f5537eaa37be271",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        },
        {
          "resource_id": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "NoCost",
          "details": "Free Tier / zero-cost AWS CloudFormation vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 0.0,
          "confidence": "LOW"
        }
      ]
    },
    "AWS Cost Explorer": {
      "cost": 10.49,
      "recommendations": [
        {
          "resource_id": "infra",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer infra",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "sg-0066b78761a1e0e36",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer sg-0066b78761a1e0e36",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-021b48de68b5958ee",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer subnet-021b48de68b5958ee",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer 97e9dfd9-4493-4657-9657-dd17cdb8d4c3",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0ee11b98b8dd343ea",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer subnet-0ee11b98b8dd343ea",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-03497fad2ec0debfe",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer subnet-03497fad2ec0debfe",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-049c6400a665ecdde",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer subnet-049c6400a665ecdde",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "devops",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer devops",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "awscostuserreport",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer awscostuserreport",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "i-09c064032c9fca209",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer i-09c064032c9fca209",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-0d24a17f3160eae81",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer subnet-0d24a17f3160eae81",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "subnet-08f5537eaa37be271",
          "region": "us-east-1",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer subnet-08f5537eaa37be271",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        },
        {
          "resource_id": "vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "region": "unknown",
          "action": "Review",
          "details": "Review usage for AWS Cost Explorer vantage-cur-cf589c6f-4d7e-4b9f-ad49-11f27fd8f164-2c804b5b63",
          "estimated_savings": 5.25,
          "confidence": "LOW"
        }
      ]
    },
    "Amazon Glacier": {
      "cost": 0.0,
      "recommendations": [
        {
          "resource_id": "N/A",
          "region": "all",
          "action": "Review Lifecycle",
          "details": "Consider lifecycle/archival for N/A",
          "estimated_savings": 0.0,
          "confidence": "MEDIUM"
        }
      ]
    }
  }
}
