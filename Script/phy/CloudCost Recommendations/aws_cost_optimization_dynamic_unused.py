ubuntu@ip-172-31-32-78:~/test$ ls
IAM.py                                   aws_optimization_report.json                  aws_optimization_report_20250919_153717.json  cloudcost.py     ec2.py
aws_cost_optimization_dynamic_unused.py  aws_optimization_report_20250919_152605.json  aws_optimization_report_20250919_155351.json  cloudcostbox.py  prod.py
=========================================================================================================================================================
ubuntu@ip-172-31-32-78:~/test$ cat cloudcostbox.py
#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, UnknownServiceError
import json
from tabulate import tabulate
import time

# Updated valid_services list as provided
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

def get_all_aws_services():
    """
    Fetch all AWS service codes using the Pricing API with pagination.
    """
    pricing_client = boto3.client('pricing', region_name='us-east-1')
    services = {}
    try:
        paginator = pricing_client.get_paginator('describe_services')
        page_iterator = paginator.paginate(FormatVersion='aws_v1')
        for page in page_iterator:
            for svc in page['Services']:
                services[svc['ServiceCode']] = svc['AttributeNames']
        print(f"Retrieved {len(services)} AWS services.")
        return services
    except ClientError as e:
        print(f"Error fetching services: {e}")
        return {}

def get_all_aws_regions():
    """
    Fetch all available AWS regions.
    """
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    try:
        response = ec2_client.describe_regions()
        return [region['RegionName'] for region in response['Regions']]
    except ClientError as e:
        print(f"Error fetching regions: {e}")
        return ['us-east-1']  # Fallback to default region

def get_costs_by_service(start_date, end_date, region='us-east-1'):
    """
    Fetch costs grouped by SERVICE using Cost Explorer API for the specified period and region.
    Include FreeTier filter to capture free tier usage.
    """
    ce_client = boto3.client('ce', region_name=region)
    try:
        # Convert strings back to datetime for comparison
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if start_dt >= end_dt:
            print(f"Skipping cost fetch for {region}: Start date ({start_date}) is not before end date ({end_date}).")
            return {}
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Filter={'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit', 'Refund', 'Upfront']}}}
        )
        costs = {}
        for group in response['ResultsByTime'][0]['Groups']:
            service = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])
            costs[service] = costs.get(service, 0) + cost
        print(f"Retrieved costs for {len(costs)} services from {start_date} to {end_date} in {region} including free tier.")
        return costs
    except ClientError as e:
        print(f"Error fetching costs in {region}: {e}")
        return {}

def aggregate_costs_across_regions(start_date, end_date, regions):
    """
    Aggregate costs from all regions, skipping invalid periods.
    """
    total_costs = {}
    for region in regions:
        costs = get_costs_by_service(start_date, end_date, region)
        for service, cost in costs.items():
            total_costs[service] = total_costs.get(service, 0) + cost
    return total_costs

def get_usage_metrics(service_code, resource_id, start_time, end_time, region='us-east-1'):
    """
    Fetch usage metrics for the specified period and region.
    Returns True if inactive and usage stats if available.
    """
    cloudwatch_client = boto3.client('cloudwatch', region_name=region)
    is_unused = True
    usage_stats = {'cpu_util': 0, 'memory_util': 0}
    try:
        metrics = {
            'CPUUtilization': 'cpu_util',
            'MemoryUtilization': 'memory_util',
            'Requests': None,
            'NumberOfMessagesSent': None,
            'SearchableDocuments': None,
            'DatabaseConnections': None,
            'BytesTransferred': None
        }
        for metric, stat_key in metrics.items():
            try:
                response = cloudwatch_client.get_metric_statistics(
                    Namespace=f'AWS/{service_code}',
                    MetricName=metric,
                    Dimensions=[{'Name': 'ResourceId', 'Value': resource_id}] if resource_id else [],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Average']
                )
                points = response['Datapoints']
                if points:
                    avg = sum(point['Average'] for point in points) / len(points) if points else 0
                    if stat_key:
                        usage_stats[stat_key] = avg
                    if avg > 0:
                        is_unused = False
            except ClientError:
                continue

        if is_unused:
            short_start_time = end_time - timedelta(days=1)
            for metric, stat_key in metrics.items():
                try:
                    response = cloudwatch_client.get_metric_statistics(
                        Namespace=f'AWS/{service_code}',
                        MetricName=metric,
                        Dimensions=[{'Name': 'ResourceId', 'Value': resource_id}] if resource_id else [],
                        StartTime=short_start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Average']
                    )
                    points = response['Datapoints']
                    if points:
                        avg = sum(point['Average'] for point in points) / len(points) if points else 0
                        if stat_key:
                            usage_stats[stat_key] = max(usage_stats[stat_key], avg)
                        if avg > 0:
                            is_unused = False
                except ClientError:
                    continue

        if is_unused:
            try:
                service_client = boto3.client(service_code.lower(), region_name=region)
                api_call = getattr(service_client, f'list_{service_code.lower()[:-4]}s', None) or getattr(service_client, 'list_resources', None)
                if api_call:
                    response = api_call()
                    resources = response.get('Resources', []) if 'Resources' in response else response.get(f'{service_code.lower()}s', [])
                    for resource in resources:
                        if resource.get('ResourceId') == resource_id or not resource_id:
                            is_unused = False
                            break
            except (ClientError, UnknownServiceError):
                pass
    except ClientError as e:
        print(f"Error fetching usage for {service_code} {resource_id} in {region}: {e}")

    return is_unused, usage_stats

def get_s3_buckets(region):
    """
    Fetch all S3 bucket names for the specified region.
    """
    s3_client = boto3.client('s3', region_name=region)
    try:
        response = s3_client.list_buckets()
        return [bucket['Name'] for bucket in response['Buckets']]
    except ClientError as e:
        print(f"Error fetching S3 buckets in {region}: {e}")
        return []

def get_ebs_volume_status(region):
    """
    Fetch EBS volumes and check if unattached (unused) for the specified region.
    """
    ec2_client = boto3.client('ec2', region_name=region)
    try:
        response = ec2_client.describe_volumes()
        volumes = []
        for volume in response['Volumes']:
            volumes.append({
                'VolumeId': volume['VolumeId'],
                'is_unused': len(volume['Attachments']) == 0
            })
        return volumes
    except ClientError as e:
        print(f"Error fetching EBS volumes in {region}: {e}")
        return []

def suggest_action(service_code, resource_id, is_unused, usage_stats=None, current_cost=0):
    """
    Suggest actions with dynamic cost reduction percentages.
    """
    if is_unused:
        if service_code == 'EC2' and usage_stats['cpu_util'] == 0 and usage_stats['memory_util'] == 0:
            savings_percent = 100 if current_cost > 0 else 0
            return f"Stop {service_code} instance {resource_id} (no activity, reduce cost by {savings_percent}%)"
        savings_percent = 75 if current_cost > 0 else 0
        return f"Delete unused {service_code} resource {resource_id} (no activity, reduce cost by {savings_percent}%)"
    else:
        if service_code == 'EC2' and usage_stats:
            cpu_util = usage_stats['cpu_util']
            memory_util = usage_stats['memory_util']
            if cpu_util < 20 and memory_util < 20:
                savings_percent = 30
                return f"Rightsize {service_code} instance {resource_id} to t3.micro (low utilization, reduce cost by {savings_percent}%)"
            elif cpu_util > 80 or memory_util > 80:
                savings_percent = 10
                return f"Rightsize {service_code} instance {resource_id} to a larger type (high utilization, reduce cost by {savings_percent}%)"
        savings_percent = 5
        return f"Optimize {service_code} resource {resource_id} (activity detected, reduce cost by {savings_percent}%)"

def get_service_recommendations(services, costs, start_time, end_time, regions):
    """
    Fetch recommendations for all AWS services dynamically across all regions.
    """
    recommendations = {}
    ist_offset = 5.5 * 3600  # IST is UTC+5:30
    now_ist = datetime.utcnow() + timedelta(seconds=ist_offset)

    for service_code in services.keys():
        if service_code.lower() not in valid_services:
            print(f"Skipping invalid service: {service_code}")
            continue
        recommendations[service_code] = []
        for region in regions:
            try:
                service_client = boto3.client(service_code.lower(), region_name=region)
                list_method = getattr(service_client, f'list_{service_code.lower()[:-4]}s', None) or getattr(service_client, 'list_resources', None)
                if list_method:
                    response = list_method()
                    resources = response.get('Resources', []) if 'Resources' in response else response.get(f'{service_code.lower()}s', [])
                    for resource in resources:
                        resource_id = resource.get('ResourceId', resource.get('Id', str(resource)))
                        is_unused, usage_stats = get_usage_metrics(service_code, resource_id, start_time, end_time, region)
                        current_cost = costs.get(service_code, 0) / len(resources) if resources else 0
                        rec = {
                            'account_id': 'N/A' if is_unused else '123456789012',
                            'action': 'Delete' if is_unused else 'Optimize',
                            'savings': current_cost,
                            'details': suggest_action(service_code, resource_id, is_unused, usage_stats, current_cost),
                            'region': region
                        }
                        recommendations[service_code].append(rec)
            except ClientError as e:
                print(f"Error fetching recommendations for {service_code} in {region}: {e}")
                recommendations[service_code].append({
                    'account_id': 'N/A',
                    'action': 'Review',
                    'savings': 0,
                    'details': f"Review usage for potential {service_code} resources (API error)",
                    'region': region
                })

    return recommendations

def apply_recommendations(services, costs, start_time, end_time, period_label, regions):
    """
    Simulate applying recommendations for the specified period across all regions.
    """
    recommendations = get_service_recommendations(services, costs, start_time, end_time, regions)
    report = {"services": {}}
    for service, recs in recommendations.items():
        if service in costs or recs:
            report["services"][service] = {
                "cost": costs.get(service, 0),
                "period": period_label,
                "recommendations": [
                    {
                        "account_id": rec['account_id'],
                        "action": rec['action'],
                        "estimated_savings": rec['savings'],
                        "details": rec['details'],
                        'region': rec['region']
                    } for rec in recs
                ]
            }
    return report

def save_report(report, filename="aws_optimization_report.json"):
    """
    Save the recommendation report to a JSON file.
    """
    try:
        with open(filename, 'w') as f:
            json.dump(report, f, indent=4)
        print(f"Recommendation report saved to {filename}")
    except Exception as e:
        print(f"Error saving report: {e}")

def print_table_report(all_reports):
    """
    Print a table-formatted report for all periods and services.
    """
    table_data = []
    headers = ["Period", "Service", "Cost ($)", "Account", "Action", "Savings ($)", "Details", "Region"]

    for period, report in all_reports.items():
        for service, data in report["services"].items():
            for rec in data["recommendations"]:
                table_data.append([
                    period,
                    service,
                    f"{data['cost']:.2f}",
                    rec['account_id'],
                    rec['action'],
                    f"{rec['estimated_savings']:.2f}",
                    rec['details'],
                    rec['region']
                ])

    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def main():
    # Set base date and time (03:42 PM IST, September 19, 2025)
    ist_offset = 5.5 * 3600  # IST is UTC+5:30
    now_ist = datetime.utcnow() + timedelta(seconds=ist_offset)
    end_date = now_ist.strftime('%Y-%m-%d')
    end_time = now_ist

    # Define time periods (5 minutes, 7 days, 15 days, 30 days, 60 days)
    periods = [0.00347, 7, 15, 30, 60]  # 5 minutes in days (300s / 86400s/day)
    all_reports = {}

    # Get all services and regions
    services = get_all_aws_services()
    regions = get_all_aws_regions()

    while True:
        print(f"Starting optimization run at {now_ist.strftime('%H:%M:%S IST, %Y-%m-%d')}")
        for days in periods:
            start_date = (now_ist - timedelta(days=days)).strftime('%Y-%m-%d')
            start_time = now_ist - timedelta(days=days)
            period_label = "5 minutes" if days == 0.00347 else f"{int(days)} days"

            # Adjust start_date for 5-minute period to ensure at least 1-hour window
            if days < 1:
                start_date = (now_ist - timedelta(hours=1)).strftime('%Y-%m-%d')
                if start_date == end_date:
                    start_date = (now_ist - timedelta(days=1)).strftime('%Y-%m-%d')
                    print(f"Adjusted {period_label} period start_date to {start_date} for valid range.")

            # Get aggregated costs across all regions
            costs = aggregate_costs_across_regions(start_date, end_date, regions)

            # Generate and apply recommendations
            report = apply_recommendations(services, costs, start_time, end_time, period_label, regions)
            all_reports[period_label] = report

        # Print table-formatted report
        print_table_report(all_reports)

        # Save consolidated report with timestamp
        timestamp = now_ist.strftime('%Y%m%d_%H%M%S')
        save_report(all_reports, f"aws_optimization_report_{timestamp}.json")

        # Wait for 5 minutes before the next run
        time.sleep(300)

if __name__ == "__main__":
    main()
============================================================OUTPUT==============================================================================================
ubuntu@ip-172-31-32-78:~/test$ ./cloudcostbox.py
Retrieved 243 AWS services.
Starting optimization run at 16:43:09 IST, 2025-09-19
Adjusted 5 minutes period start_date to 2025-09-18 for valid range.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-south-2 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-south-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in eu-north-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in eu-west-3 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in eu-west-2 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in eu-west-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-northeast-3 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-northeast-2 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-northeast-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ca-central-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in sa-east-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-southeast-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in ap-southeast-2 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in eu-central-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in us-east-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in us-east-2 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in us-west-1 including free tier.
Retrieved costs for 6 services from 2025-09-18 to 2025-09-19 in us-west-2 including free tier.
Skipping invalid service: A4B
Skipping invalid service: AWSAmplify
Skipping invalid service: AWSAppFabric
Skipping invalid service: AWSAppRunner
Skipping invalid service: AWSAppStudio
Skipping invalid service: AWSAppSync
Skipping invalid service: AWSApplicationMigrationSvc
Skipping invalid service: AWSB2Bi
Skipping invalid service: AWSBCMPricingCalculator
Skipping invalid service: AWSBackup
Skipping invalid service: AWSBillingConductor
Skipping invalid service: AWSBudgets
Skipping invalid service: AWSCertificateManager
Skipping invalid service: AWSCleanRooms
Skipping invalid service: AWSCloudFormation
Skipping invalid service: AWSCloudMap
Skipping invalid service: AWSCloudTrail
Skipping invalid service: AWSCloudWAN
Skipping invalid service: AWSCodeArtifact
Skipping invalid service: AWSCodeCommit
Skipping invalid service: AWSCodeDeploy
Skipping invalid service: AWSCodePipeline
Skipping invalid service: AWSComputeOptimizer
Skipping invalid service: AWSConfig
Skipping invalid service: AWSCostExplorer
Skipping invalid service: AWSDataExchange
Skipping invalid service: AWSDataSync
Skipping invalid service: AWSDataTransfer
Skipping invalid service: AWSDatabaseMigrationSvc
Skipping invalid service: AWSDeepRacer
Skipping invalid service: AWSDeveloperSupport
Skipping invalid service: AWSDeviceFarm
Skipping invalid service: AWSDirectConnect
Skipping invalid service: AWSDirectoryService
Skipping invalid service: AWSELB
Skipping invalid service: AWSElasticDisasterRecovery
Skipping invalid service: AWSElementalMediaConvert
Skipping invalid service: AWSElementalMediaLive
Skipping invalid service: AWSElementalMediaPackage
Skipping invalid service: AWSElementalMediaStore
Skipping invalid service: AWSElementalMediaTailor
Skipping invalid service: AWSEndUserMessaging3pFees
Skipping invalid service: AWSEnterpriseOnRamp
Skipping invalid service: AWSEntityResolution
Skipping invalid service: AWSEvents
Skipping invalid service: AWSFIS
Skipping invalid service: AWSFMS
Skipping invalid service: AWSGlobalAccelerator
Skipping invalid service: AWSGlueElasticViews
Skipping invalid service: AWSGlue
Skipping invalid service: AWSGreengrass
Skipping invalid service: AWSGroundStation
Skipping invalid service: AWSIAMAccessAnalyzer
Skipping invalid service: AWSIoT1Click
Skipping invalid service: AWSIoTAnalytics
Skipping invalid service: AWSIoTEvents
Skipping invalid service: AWSIoTFleetWise
Skipping invalid service: AWSIoTSiteWise
Skipping invalid service: AWSIoTThingsGraph
Skipping invalid service: AWSIoT
Skipping invalid service: AWSLakeFormation
Skipping invalid service: AWSLambda
Skipping invalid service: AWSM2
Skipping invalid service: AWSMDC
Skipping invalid service: AWSManagedServices
Skipping invalid service: AWSMediaConnect
Skipping invalid service: AWSMigrationHubRefactorSpaces
Skipping invalid service: AWSNetworkFirewall
Skipping invalid service: AWSOutposts
Skipping invalid service: AWSPCS
Skipping invalid service: AWSPrivate5G
Skipping invalid service: AWSQueueService
Skipping invalid service: AWSR53AppRecoveryController
Skipping invalid service: AWSResilienceHub
Skipping invalid service: AWSRoboMaker
Skipping invalid service: AWSSecretsManager
Skipping invalid service: AWSSecurityHub
Skipping invalid service: AWSServiceCatalog
Skipping invalid service: AWSShield
Skipping invalid service: AWSStorageGatewayDeepArchive
Skipping invalid service: AWSStorageGateway
Skipping invalid service: AWSSupplyChain
Skipping invalid service: AWSSupportBusiness
Skipping invalid service: AWSSupportEnterprise
Skipping invalid service: AWSSystemsManager
Skipping invalid service: AWSTelcoNetworkBuilder
Skipping invalid service: AWSTransfer
Skipping invalid service: AWSWickr
Skipping invalid service: AWSWisdom
Skipping invalid service: AWSXRay
Skipping invalid service: AlexaTopSites
Skipping invalid service: AlexaWebInfoService
Skipping invalid service: AmazonA2I
Skipping invalid service: AmazonApiGateway
Skipping invalid service: AmazonAppStream
Skipping invalid service: AmazonAthena
Skipping invalid service: AmazonBedrockService
Skipping invalid service: AmazonBedrock
Skipping invalid service: AmazonBraket
Skipping invalid service: AmazonChimeBusinessCalling
Skipping invalid service: AmazonChimeCallMeAMCS
Skipping invalid service: AmazonChimeCallMe
Skipping invalid service: AmazonChimeDialInAMCS
Skipping invalid service: AmazonChimeDialin
Skipping invalid service: AmazonChimeFeatures
Skipping invalid service: AmazonChimeServices
Skipping invalid service: AmazonChimeVoiceConnector
Skipping invalid service: AmazonChime
Skipping invalid service: AmazonCloudDirectory
Skipping invalid service: AmazonCloudFront
Skipping invalid service: AmazonCloudSearch
Skipping invalid service: AmazonCloudWatch
Skipping invalid service: AmazonCodeWhisperer
Skipping invalid service: AmazonCognitoSync
Skipping invalid service: AmazonCognito
Skipping invalid service: AmazonConnectCases
Skipping invalid service: AmazonConnectVoiceID
Skipping invalid service: AmazonConnect
Skipping invalid service: AmazonDAX
Skipping invalid service: AmazonDataZone
Skipping invalid service: AmazonDeadline
Skipping invalid service: AmazonDetective
Skipping invalid service: AmazonDevOpsGuru
Skipping invalid service: AmazonDocDB
Skipping invalid service: AmazonDynamoDB
Skipping invalid service: AmazonEC2
Skipping invalid service: AmazonECRPublic
Skipping invalid service: AmazonECR
Skipping invalid service: AmazonECS
Skipping invalid service: AmazonEFS
Skipping invalid service: AmazonEI
Skipping invalid service: AmazonEKSAnywhere
Skipping invalid service: AmazonEKS
Skipping invalid service: AmazonES
Skipping invalid service: AmazonETS
Skipping invalid service: AmazonEVS
Skipping invalid service: AmazonElastiCache
Skipping invalid service: AmazonFSx
Skipping invalid service: AmazonFinSpace
Skipping invalid service: AmazonForecast
Skipping invalid service: AmazonFraudDetector
Skipping invalid service: AmazonGameLiftStreams
Skipping invalid service: AmazonGameLift
Skipping invalid service: AmazonGlacier
Skipping invalid service: AmazonGrafana
Skipping invalid service: AmazonGuardDuty
Skipping invalid service: AmazonHealthLake
Skipping invalid service: AmazonHoneycode
Skipping invalid service: AmazonIVSChat
Skipping invalid service: AmazonIVS
Skipping invalid service: AmazonInspectorV2
Skipping invalid service: AmazonInspector
Skipping invalid service: AmazonKendra
Skipping invalid service: AmazonKinesisAnalytics
Skipping invalid service: AmazonKinesisFirehose
Skipping invalid service: AmazonKinesisVideo
Skipping invalid service: AmazonKinesis
Skipping invalid service: AmazonLex
Skipping invalid service: AmazonLightsail
Skipping invalid service: AmazonLocationService
Skipping invalid service: AmazonLookoutEquipment
Skipping invalid service: AmazonLookoutMetrics
Skipping invalid service: AmazonLookoutVision
Skipping invalid service: AmazonMCS
Skipping invalid service: AmazonML
Skipping invalid service: AmazonMQ
Skipping invalid service: AmazonMSK
Skipping invalid service: AmazonMWAA
Skipping invalid service: AmazonMacie
Skipping invalid service: AmazonManagedBlockchain
Skipping invalid service: AmazonMedicalImaging
Skipping invalid service: AmazonMemoryDB
Skipping invalid service: AmazonMonitron
Skipping invalid service: AmazonNeptune
Skipping invalid service: AmazonOmics
Skipping invalid service: AmazonPersonalize
Skipping invalid service: AmazonPinpoint
Skipping invalid service: AmazonPolly
Skipping invalid service: AmazonPrometheus
Skipping invalid service: AmazonQLDB
Skipping invalid service: AmazonQ
Skipping invalid service: AmazonQuickSight
Skipping invalid service: AmazonRDS
Skipping invalid service: AmazonRedshift
Skipping invalid service: AmazonRekognition
Skipping invalid service: AmazonRoute53
Skipping invalid service: AmazonS3GlacierDeepArchive
Skipping invalid service: AmazonS3
Skipping invalid service: AmazonSES
Skipping invalid service: AmazonSNS
Skipping invalid service: AmazonSWF
Skipping invalid service: AmazonSageMaker
Skipping invalid service: AmazonSecurityLake
Skipping invalid service: AmazonSimpleDB
Skipping invalid service: AmazonStates
Skipping invalid service: AmazonSumerian
Skipping invalid service: AmazonTextract
Skipping invalid service: AmazonTimestream
Skipping invalid service: AmazonVPC
Skipping invalid service: AmazonVerifiedPermissions
Skipping invalid service: AmazonWAM
Skipping invalid service: AmazonWorkDocs
Skipping invalid service: AmazonWorkLink
Skipping invalid service: AmazonWorkMail
Skipping invalid service: AmazonWorkSpacesThinClient
Skipping invalid service: AmazonWorkSpacesWeb
Skipping invalid service: AmazonWorkSpaces
Skipping invalid service: AuroraDSQL
Skipping invalid service: CodeGuru
Skipping invalid service: ContactCenterTelecommKR
Skipping invalid service: ContactCenterTelecommZA
Skipping invalid service: ContactCenterTelecomm
Skipping invalid service: ContactLensAmazonConnect
Skipping invalid service: CustomerProfiles
Skipping invalid service: ElasticMapReduce
Skipping invalid service: IngestionServiceSnowball
Skipping invalid service: IngestionService
Skipping invalid service: IoTDeviceDefender
Skipping invalid service: IoTDeviceManagement
Skipping invalid service: OpsWorks
Skipping invalid service: OracleDbAtAWS
Skipping invalid service: PaymentCryptography
Skipping invalid service: SSMSAP
Skipping invalid service: SnowballExtraDays
Skipping invalid service: VMwareCloudOnAWS
Skipping invalid service: awskms
Skipping invalid service: awswaf
Skipping invalid service: mobileanalytics
Skipping invalid service: nimble
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-south-2 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-south-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in eu-north-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in eu-west-3 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in eu-west-2 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in eu-west-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-northeast-3 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-northeast-2 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-northeast-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ca-central-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in sa-east-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-southeast-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in ap-southeast-2 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in eu-central-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in us-east-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in us-east-2 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in us-west-1 including free tier.
Retrieved costs for 11 services from 2025-09-12 to 2025-09-19 in us-west-2 including free tier.
Skipping invalid service: A4B
Skipping invalid service: AWSAmplify
Skipping invalid service: AWSAppFabric
Skipping invalid service: AWSAppRunner
Skipping invalid service: AWSAppStudio
Skipping invalid service: AWSAppSync
Skipping invalid service: AWSApplicationMigrationSvc
Skipping invalid service: AWSB2Bi
Skipping invalid service: AWSBCMPricingCalculator
Skipping invalid service: AWSBackup
Skipping invalid service: AWSBillingConductor
Skipping invalid service: AWSBudgets
Skipping invalid service: AWSCertificateManager
Skipping invalid service: AWSCleanRooms
Skipping invalid service: AWSCloudFormation
Skipping invalid service: AWSCloudMap
Skipping invalid service: AWSCloudTrail
Skipping invalid service: AWSCloudWAN
Skipping invalid service: AWSCodeArtifact
Skipping invalid service: AWSCodeCommit
Skipping invalid service: AWSCodeDeploy
Skipping invalid service: AWSCodePipeline
Skipping invalid service: AWSComputeOptimizer
Skipping invalid service: AWSConfig
Skipping invalid service: AWSCostExplorer
Skipping invalid service: AWSDataExchange
Skipping invalid service: AWSDataSync
Skipping invalid service: AWSDataTransfer
Skipping invalid service: AWSDatabaseMigrationSvc
Skipping invalid service: AWSDeepRacer
Skipping invalid service: AWSDeveloperSupport
Skipping invalid service: AWSDeviceFarm
Skipping invalid service: AWSDirectConnect
Skipping invalid service: AWSDirectoryService
Skipping invalid service: AWSELB
Skipping invalid service: AWSElasticDisasterRecovery
Skipping invalid service: AWSElementalMediaConvert
Skipping invalid service: AWSElementalMediaLive
Skipping invalid service: AWSElementalMediaPackage
Skipping invalid service: AWSElementalMediaStore
Skipping invalid service: AWSElementalMediaTailor
Skipping invalid service: AWSEndUserMessaging3pFees
Skipping invalid service: AWSEnterpriseOnRamp
Skipping invalid service: AWSEntityResolution
Skipping invalid service: AWSEvents
Skipping invalid service: AWSFIS
Skipping invalid service: AWSFMS
Skipping invalid service: AWSGlobalAccelerator
Skipping invalid service: AWSGlueElasticViews
Skipping invalid service: AWSGlue
Skipping invalid service: AWSGreengrass
Skipping invalid service: AWSGroundStation
Skipping invalid service: AWSIAMAccessAnalyzer
Skipping invalid service: AWSIoT1Click
Skipping invalid service: AWSIoTAnalytics
Skipping invalid service: AWSIoTEvents
Skipping invalid service: AWSIoTFleetWise
Skipping invalid service: AWSIoTSiteWise
Skipping invalid service: AWSIoTThingsGraph
Skipping invalid service: AWSIoT
Skipping invalid service: AWSLakeFormation
Skipping invalid service: AWSLambda
Skipping invalid service: AWSM2
Skipping invalid service: AWSMDC
Skipping invalid service: AWSManagedServices
Skipping invalid service: AWSMediaConnect
Skipping invalid service: AWSMigrationHubRefactorSpaces
Skipping invalid service: AWSNetworkFirewall
Skipping invalid service: AWSOutposts
Skipping invalid service: AWSPCS
Skipping invalid service: AWSPrivate5G
Skipping invalid service: AWSQueueService
Skipping invalid service: AWSR53AppRecoveryController
Skipping invalid service: AWSResilienceHub
Skipping invalid service: AWSRoboMaker
Skipping invalid service: AWSSecretsManager
Skipping invalid service: AWSSecurityHub
Skipping invalid service: AWSServiceCatalog
Skipping invalid service: AWSShield
Skipping invalid service: AWSStorageGatewayDeepArchive
Skipping invalid service: AWSStorageGateway
Skipping invalid service: AWSSupplyChain
Skipping invalid service: AWSSupportBusiness
Skipping invalid service: AWSSupportEnterprise
Skipping invalid service: AWSSystemsManager
Skipping invalid service: AWSTelcoNetworkBuilder
Skipping invalid service: AWSTransfer
Skipping invalid service: AWSWickr
Skipping invalid service: AWSWisdom
Skipping invalid service: AWSXRay
Skipping invalid service: AlexaTopSites
Skipping invalid service: AlexaWebInfoService
Skipping invalid service: AmazonA2I
Skipping invalid service: AmazonApiGateway
Skipping invalid service: AmazonAppStream
Skipping invalid service: AmazonAthena
Skipping invalid service: AmazonBedrockService
Skipping invalid service: AmazonBedrock
Skipping invalid service: AmazonBraket
Skipping invalid service: AmazonChimeBusinessCalling
Skipping invalid service: AmazonChimeCallMeAMCS
Skipping invalid service: AmazonChimeCallMe
Skipping invalid service: AmazonChimeDialInAMCS
Skipping invalid service: AmazonChimeDialin
Skipping invalid service: AmazonChimeFeatures
Skipping invalid service: AmazonChimeServices
Skipping invalid service: AmazonChimeVoiceConnector
Skipping invalid service: AmazonChime
Skipping invalid service: AmazonCloudDirectory
Skipping invalid service: AmazonCloudFront
Skipping invalid service: AmazonCloudSearch
Skipping invalid service: AmazonCloudWatch
Skipping invalid service: AmazonCodeWhisperer
Skipping invalid service: AmazonCognitoSync
Skipping invalid service: AmazonCognito
Skipping invalid service: AmazonConnectCases
Skipping invalid service: AmazonConnectVoiceID
Skipping invalid service: AmazonConnect
Skipping invalid service: AmazonDAX
Skipping invalid service: AmazonDataZone
Skipping invalid service: AmazonDeadline
Skipping invalid service: AmazonDetective
Skipping invalid service: AmazonDevOpsGuru
Skipping invalid service: AmazonDocDB
Skipping invalid service: AmazonDynamoDB
Skipping invalid service: AmazonEC2
Skipping invalid service: AmazonECRPublic
Skipping invalid service: AmazonECR
Skipping invalid service: AmazonECS
Skipping invalid service: AmazonEFS
Skipping invalid service: AmazonEI
Skipping invalid service: AmazonEKSAnywhere
Skipping invalid service: AmazonEKS
Skipping invalid service: AmazonES
Skipping invalid service: AmazonETS
Skipping invalid service: AmazonEVS
Skipping invalid service: AmazonElastiCache
Skipping invalid service: AmazonFSx
Skipping invalid service: AmazonFinSpace
Skipping invalid service: AmazonForecast
Skipping invalid service: AmazonFraudDetector
Skipping invalid service: AmazonGameLiftStreams
Skipping invalid service: AmazonGameLift
Skipping invalid service: AmazonGlacier
Skipping invalid service: AmazonGrafana
Skipping invalid service: AmazonGuardDuty
Skipping invalid service: AmazonHealthLake
Skipping invalid service: AmazonHoneycode
Skipping invalid service: AmazonIVSChat
Skipping invalid service: AmazonIVS
Skipping invalid service: AmazonInspectorV2
Skipping invalid service: AmazonInspector
Skipping invalid service: AmazonKendra
Skipping invalid service: AmazonKinesisAnalytics
Skipping invalid service: AmazonKinesisFirehose
Skipping invalid service: AmazonKinesisVideo
Skipping invalid service: AmazonKinesis
Skipping invalid service: AmazonLex
Skipping invalid service: AmazonLightsail
Skipping invalid service: AmazonLocationService
Skipping invalid service: AmazonLookoutEquipment
Skipping invalid service: AmazonLookoutMetrics
Skipping invalid service: AmazonLookoutVision
Skipping invalid service: AmazonMCS
Skipping invalid service: AmazonML
Skipping invalid service: AmazonMQ
Skipping invalid service: AmazonMSK
Skipping invalid service: AmazonMWAA
Skipping invalid service: AmazonMacie
Skipping invalid service: AmazonManagedBlockchain
Skipping invalid service: AmazonMedicalImaging
Skipping invalid service: AmazonMemoryDB
Skipping invalid service: AmazonMonitron
Skipping invalid service: AmazonNeptune
Skipping invalid service: AmazonOmics
Skipping invalid service: AmazonPersonalize
Skipping invalid service: AmazonPinpoint
Skipping invalid service: AmazonPolly
Skipping invalid service: AmazonPrometheus
Skipping invalid service: AmazonQLDB
Skipping invalid service: AmazonQ
Skipping invalid service: AmazonQuickSight
Skipping invalid service: AmazonRDS
Skipping invalid service: AmazonRedshift
Skipping invalid service: AmazonRekognition
Skipping invalid service: AmazonRoute53
Skipping invalid service: AmazonS3GlacierDeepArchive
Skipping invalid service: AmazonS3
Skipping invalid service: AmazonSES
Skipping invalid service: AmazonSNS
Skipping invalid service: AmazonSWF
Skipping invalid service: AmazonSageMaker
Skipping invalid service: AmazonSecurityLake
Skipping invalid service: AmazonSimpleDB
Skipping invalid service: AmazonStates
Skipping invalid service: AmazonSumerian
Skipping invalid service: AmazonTextract
Skipping invalid service: AmazonTimestream
Skipping invalid service: AmazonVPC
Skipping invalid service: AmazonVerifiedPermissions
Skipping invalid service: AmazonWAM
Skipping invalid service: AmazonWorkDocs
Skipping invalid service: AmazonWorkLink
Skipping invalid service: AmazonWorkMail
Skipping invalid service: AmazonWorkSpacesThinClient
Skipping invalid service: AmazonWorkSpacesWeb
Skipping invalid service: AmazonWorkSpaces
Skipping invalid service: AuroraDSQL
Skipping invalid service: CodeGuru
Skipping invalid service: ContactCenterTelecommKR
Skipping invalid service: ContactCenterTelecommZA
Skipping invalid service: ContactCenterTelecomm
Skipping invalid service: ContactLensAmazonConnect
Skipping invalid service: CustomerProfiles
Skipping invalid service: ElasticMapReduce
Skipping invalid service: IngestionServiceSnowball
Skipping invalid service: IngestionService
Skipping invalid service: IoTDeviceDefender
Skipping invalid service: IoTDeviceManagement
Skipping invalid service: OpsWorks
Skipping invalid service: OracleDbAtAWS
Skipping invalid service: PaymentCryptography
Skipping invalid service: SSMSAP
Skipping invalid service: SnowballExtraDays
Skipping invalid service: VMwareCloudOnAWS
Skipping invalid service: awskms
Skipping invalid service: awswaf
Skipping invalid service: mobileanalytics
Skipping invalid service: nimble
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-south-2 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-south-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in eu-north-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in eu-west-3 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in eu-west-2 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in eu-west-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-northeast-3 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-northeast-2 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-northeast-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ca-central-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in sa-east-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-southeast-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in ap-southeast-2 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in eu-central-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in us-east-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in us-east-2 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in us-west-1 including free tier.
Retrieved costs for 12 services from 2025-09-04 to 2025-09-19 in us-west-2 including free tier.
Skipping invalid service: A4B
Skipping invalid service: AWSAmplify
Skipping invalid service: AWSAppFabric
Skipping invalid service: AWSAppRunner
Skipping invalid service: AWSAppStudio
Skipping invalid service: AWSAppSync
Skipping invalid service: AWSApplicationMigrationSvc
Skipping invalid service: AWSB2Bi
Skipping invalid service: AWSBCMPricingCalculator
Skipping invalid service: AWSBackup
Skipping invalid service: AWSBillingConductor
Skipping invalid service: AWSBudgets
Skipping invalid service: AWSCertificateManager
Skipping invalid service: AWSCleanRooms
Skipping invalid service: AWSCloudFormation
Skipping invalid service: AWSCloudMap
Skipping invalid service: AWSCloudTrail
Skipping invalid service: AWSCloudWAN
Skipping invalid service: AWSCodeArtifact
Skipping invalid service: AWSCodeCommit
Skipping invalid service: AWSCodeDeploy
Skipping invalid service: AWSCodePipeline
Skipping invalid service: AWSComputeOptimizer
Skipping invalid service: AWSConfig
Skipping invalid service: AWSCostExplorer
Skipping invalid service: AWSDataExchange
Skipping invalid service: AWSDataSync
Skipping invalid service: AWSDataTransfer
Skipping invalid service: AWSDatabaseMigrationSvc
Skipping invalid service: AWSDeepRacer
Skipping invalid service: AWSDeveloperSupport
Skipping invalid service: AWSDeviceFarm
Skipping invalid service: AWSDirectConnect
Skipping invalid service: AWSDirectoryService
Skipping invalid service: AWSELB
Skipping invalid service: AWSElasticDisasterRecovery
Skipping invalid service: AWSElementalMediaConvert
Skipping invalid service: AWSElementalMediaLive
Skipping invalid service: AWSElementalMediaPackage
Skipping invalid service: AWSElementalMediaStore
Skipping invalid service: AWSElementalMediaTailor
Skipping invalid service: AWSEndUserMessaging3pFees
Skipping invalid service: AWSEnterpriseOnRamp
Skipping invalid service: AWSEntityResolution
Skipping invalid service: AWSEvents
Skipping invalid service: AWSFIS
Skipping invalid service: AWSFMS
Skipping invalid service: AWSGlobalAccelerator
Skipping invalid service: AWSGlueElasticViews
Skipping invalid service: AWSGlue
Skipping invalid service: AWSGreengrass
Skipping invalid service: AWSGroundStation
Skipping invalid service: AWSIAMAccessAnalyzer
Skipping invalid service: AWSIoT1Click
Skipping invalid service: AWSIoTAnalytics
Skipping invalid service: AWSIoTEvents
Skipping invalid service: AWSIoTFleetWise
Skipping invalid service: AWSIoTSiteWise
Skipping invalid service: AWSIoTThingsGraph
Skipping invalid service: AWSIoT
Skipping invalid service: AWSLakeFormation
Skipping invalid service: AWSLambda
Skipping invalid service: AWSM2
Skipping invalid service: AWSMDC
Skipping invalid service: AWSManagedServices
Skipping invalid service: AWSMediaConnect
Skipping invalid service: AWSMigrationHubRefactorSpaces
Skipping invalid service: AWSNetworkFirewall
Skipping invalid service: AWSOutposts
Skipping invalid service: AWSPCS
Skipping invalid service: AWSPrivate5G
Skipping invalid service: AWSQueueService
Skipping invalid service: AWSR53AppRecoveryController
Skipping invalid service: AWSResilienceHub
Skipping invalid service: AWSRoboMaker
Skipping invalid service: AWSSecretsManager
Skipping invalid service: AWSSecurityHub
Skipping invalid service: AWSServiceCatalog
Skipping invalid service: AWSShield
Skipping invalid service: AWSStorageGatewayDeepArchive
Skipping invalid service: AWSStorageGateway
Skipping invalid service: AWSSupplyChain
Skipping invalid service: AWSSupportBusiness
Skipping invalid service: AWSSupportEnterprise
Skipping invalid service: AWSSystemsManager
Skipping invalid service: AWSTelcoNetworkBuilder
Skipping invalid service: AWSTransfer
Skipping invalid service: AWSWickr
Skipping invalid service: AWSWisdom
Skipping invalid service: AWSXRay
Skipping invalid service: AlexaTopSites
Skipping invalid service: AlexaWebInfoService
Skipping invalid service: AmazonA2I
Skipping invalid service: AmazonApiGateway
Skipping invalid service: AmazonAppStream
Skipping invalid service: AmazonAthena
Skipping invalid service: AmazonBedrockService
Skipping invalid service: AmazonBedrock
Skipping invalid service: AmazonBraket
Skipping invalid service: AmazonChimeBusinessCalling
Skipping invalid service: AmazonChimeCallMeAMCS
Skipping invalid service: AmazonChimeCallMe
Skipping invalid service: AmazonChimeDialInAMCS
Skipping invalid service: AmazonChimeDialin
Skipping invalid service: AmazonChimeFeatures
Skipping invalid service: AmazonChimeServices
Skipping invalid service: AmazonChimeVoiceConnector
Skipping invalid service: AmazonChime
Skipping invalid service: AmazonCloudDirectory
Skipping invalid service: AmazonCloudFront
Skipping invalid service: AmazonCloudSearch
Skipping invalid service: AmazonCloudWatch
Skipping invalid service: AmazonCodeWhisperer
Skipping invalid service: AmazonCognitoSync
Skipping invalid service: AmazonCognito
Skipping invalid service: AmazonConnectCases
Skipping invalid service: AmazonConnectVoiceID
Skipping invalid service: AmazonConnect
Skipping invalid service: AmazonDAX
Skipping invalid service: AmazonDataZone
Skipping invalid service: AmazonDeadline
Skipping invalid service: AmazonDetective
Skipping invalid service: AmazonDevOpsGuru
Skipping invalid service: AmazonDocDB
Skipping invalid service: AmazonDynamoDB
Skipping invalid service: AmazonEC2
Skipping invalid service: AmazonECRPublic
Skipping invalid service: AmazonECR
Skipping invalid service: AmazonECS
Skipping invalid service: AmazonEFS
Skipping invalid service: AmazonEI
Skipping invalid service: AmazonEKSAnywhere
Skipping invalid service: AmazonEKS
Skipping invalid service: AmazonES
Skipping invalid service: AmazonETS
Skipping invalid service: AmazonEVS
Skipping invalid service: AmazonElastiCache
Skipping invalid service: AmazonFSx
Skipping invalid service: AmazonFinSpace
Skipping invalid service: AmazonForecast
Skipping invalid service: AmazonFraudDetector
Skipping invalid service: AmazonGameLiftStreams
Skipping invalid service: AmazonGameLift
Skipping invalid service: AmazonGlacier
Skipping invalid service: AmazonGrafana
Skipping invalid service: AmazonGuardDuty
Skipping invalid service: AmazonHealthLake
Skipping invalid service: AmazonHoneycode
Skipping invalid service: AmazonIVSChat
Skipping invalid service: AmazonIVS
Skipping invalid service: AmazonInspectorV2
Skipping invalid service: AmazonInspector
Skipping invalid service: AmazonKendra
Skipping invalid service: AmazonKinesisAnalytics
Skipping invalid service: AmazonKinesisFirehose
Skipping invalid service: AmazonKinesisVideo
Skipping invalid service: AmazonKinesis
Skipping invalid service: AmazonLex
Skipping invalid service: AmazonLightsail
Skipping invalid service: AmazonLocationService
Skipping invalid service: AmazonLookoutEquipment
Skipping invalid service: AmazonLookoutMetrics
Skipping invalid service: AmazonLookoutVision
Skipping invalid service: AmazonMCS
Skipping invalid service: AmazonML
Skipping invalid service: AmazonMQ
Skipping invalid service: AmazonMSK
Skipping invalid service: AmazonMWAA
Skipping invalid service: AmazonMacie
Skipping invalid service: AmazonManagedBlockchain
Skipping invalid service: AmazonMedicalImaging
Skipping invalid service: AmazonMemoryDB
Skipping invalid service: AmazonMonitron
Skipping invalid service: AmazonNeptune
Skipping invalid service: AmazonOmics
Skipping invalid service: AmazonPersonalize
Skipping invalid service: AmazonPinpoint
Skipping invalid service: AmazonPolly
Skipping invalid service: AmazonPrometheus
Skipping invalid service: AmazonQLDB
Skipping invalid service: AmazonQ
Skipping invalid service: AmazonQuickSight
Skipping invalid service: AmazonRDS
Skipping invalid service: AmazonRedshift
Skipping invalid service: AmazonRekognition
Skipping invalid service: AmazonRoute53
Skipping invalid service: AmazonS3GlacierDeepArchive
Skipping invalid service: AmazonS3
Skipping invalid service: AmazonSES
Skipping invalid service: AmazonSNS
Skipping invalid service: AmazonSWF
Skipping invalid service: AmazonSageMaker
Skipping invalid service: AmazonSecurityLake
Skipping invalid service: AmazonSimpleDB
Skipping invalid service: AmazonStates
Skipping invalid service: AmazonSumerian
Skipping invalid service: AmazonTextract
Skipping invalid service: AmazonTimestream
Skipping invalid service: AmazonVPC
Skipping invalid service: AmazonVerifiedPermissions
Skipping invalid service: AmazonWAM
Skipping invalid service: AmazonWorkDocs
Skipping invalid service: AmazonWorkLink
Skipping invalid service: AmazonWorkMail
Skipping invalid service: AmazonWorkSpacesThinClient
Skipping invalid service: AmazonWorkSpacesWeb
Skipping invalid service: AmazonWorkSpaces
Skipping invalid service: AuroraDSQL
Skipping invalid service: CodeGuru
Skipping invalid service: ContactCenterTelecommKR
Skipping invalid service: ContactCenterTelecommZA
Skipping invalid service: ContactCenterTelecomm
Skipping invalid service: ContactLensAmazonConnect
Skipping invalid service: CustomerProfiles
Skipping invalid service: ElasticMapReduce
Skipping invalid service: IngestionServiceSnowball
Skipping invalid service: IngestionService
Skipping invalid service: IoTDeviceDefender
Skipping invalid service: IoTDeviceManagement
Skipping invalid service: OpsWorks
Skipping invalid service: OracleDbAtAWS
Skipping invalid service: PaymentCryptography
Skipping invalid service: SSMSAP
Skipping invalid service: SnowballExtraDays
Skipping invalid service: VMwareCloudOnAWS
Skipping invalid service: awskms
Skipping invalid service: awswaf
Skipping invalid service: mobileanalytics
Skipping invalid service: nimble
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-south-2 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-south-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in eu-north-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in eu-west-3 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in eu-west-2 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in eu-west-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-northeast-3 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-northeast-2 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-northeast-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ca-central-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in sa-east-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-southeast-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in ap-southeast-2 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in eu-central-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in us-east-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in us-east-2 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in us-west-1 including free tier.
Retrieved costs for 10 services from 2025-08-20 to 2025-09-19 in us-west-2 including free tier.
Skipping invalid service: A4B
Skipping invalid service: AWSAmplify
Skipping invalid service: AWSAppFabric
Skipping invalid service: AWSAppRunner
Skipping invalid service: AWSAppStudio
Skipping invalid service: AWSAppSync
Skipping invalid service: AWSApplicationMigrationSvc
Skipping invalid service: AWSB2Bi
Skipping invalid service: AWSBCMPricingCalculator
Skipping invalid service: AWSBackup
Skipping invalid service: AWSBillingConductor
Skipping invalid service: AWSBudgets
Skipping invalid service: AWSCertificateManager
Skipping invalid service: AWSCleanRooms
Skipping invalid service: AWSCloudFormation
Skipping invalid service: AWSCloudMap
Skipping invalid service: AWSCloudTrail
Skipping invalid service: AWSCloudWAN
Skipping invalid service: AWSCodeArtifact
Skipping invalid service: AWSCodeCommit
Skipping invalid service: AWSCodeDeploy
Skipping invalid service: AWSCodePipeline
Skipping invalid service: AWSComputeOptimizer
Skipping invalid service: AWSConfig
Skipping invalid service: AWSCostExplorer
Skipping invalid service: AWSDataExchange
Skipping invalid service: AWSDataSync
Skipping invalid service: AWSDataTransfer
Skipping invalid service: AWSDatabaseMigrationSvc
Skipping invalid service: AWSDeepRacer
Skipping invalid service: AWSDeveloperSupport
Skipping invalid service: AWSDeviceFarm
Skipping invalid service: AWSDirectConnect
Skipping invalid service: AWSDirectoryService
Skipping invalid service: AWSELB
Skipping invalid service: AWSElasticDisasterRecovery
Skipping invalid service: AWSElementalMediaConvert
Skipping invalid service: AWSElementalMediaLive
Skipping invalid service: AWSElementalMediaPackage
Skipping invalid service: AWSElementalMediaStore
Skipping invalid service: AWSElementalMediaTailor
Skipping invalid service: AWSEndUserMessaging3pFees
Skipping invalid service: AWSEnterpriseOnRamp
Skipping invalid service: AWSEntityResolution
Skipping invalid service: AWSEvents
Skipping invalid service: AWSFIS
Skipping invalid service: AWSFMS
Skipping invalid service: AWSGlobalAccelerator
Skipping invalid service: AWSGlueElasticViews
Skipping invalid service: AWSGlue
Skipping invalid service: AWSGreengrass
Skipping invalid service: AWSGroundStation
Skipping invalid service: AWSIAMAccessAnalyzer
Skipping invalid service: AWSIoT1Click
Skipping invalid service: AWSIoTAnalytics
Skipping invalid service: AWSIoTEvents
Skipping invalid service: AWSIoTFleetWise
Skipping invalid service: AWSIoTSiteWise
Skipping invalid service: AWSIoTThingsGraph
Skipping invalid service: AWSIoT
Skipping invalid service: AWSLakeFormation
Skipping invalid service: AWSLambda
Skipping invalid service: AWSM2
Skipping invalid service: AWSMDC
Skipping invalid service: AWSManagedServices
Skipping invalid service: AWSMediaConnect
Skipping invalid service: AWSMigrationHubRefactorSpaces
Skipping invalid service: AWSNetworkFirewall
Skipping invalid service: AWSOutposts
Skipping invalid service: AWSPCS
Skipping invalid service: AWSPrivate5G
Skipping invalid service: AWSQueueService
Skipping invalid service: AWSR53AppRecoveryController
Skipping invalid service: AWSResilienceHub
Skipping invalid service: AWSRoboMaker
Skipping invalid service: AWSSecretsManager
Skipping invalid service: AWSSecurityHub
Skipping invalid service: AWSServiceCatalog
Skipping invalid service: AWSShield
Skipping invalid service: AWSStorageGatewayDeepArchive
Skipping invalid service: AWSStorageGateway
Skipping invalid service: AWSSupplyChain
Skipping invalid service: AWSSupportBusiness
Skipping invalid service: AWSSupportEnterprise
Skipping invalid service: AWSSystemsManager
Skipping invalid service: AWSTelcoNetworkBuilder
Skipping invalid service: AWSTransfer
Skipping invalid service: AWSWickr
Skipping invalid service: AWSWisdom
Skipping invalid service: AWSXRay
Skipping invalid service: AlexaTopSites
Skipping invalid service: AlexaWebInfoService
Skipping invalid service: AmazonA2I
Skipping invalid service: AmazonApiGateway
Skipping invalid service: AmazonAppStream
Skipping invalid service: AmazonAthena
Skipping invalid service: AmazonBedrockService
Skipping invalid service: AmazonBedrock
Skipping invalid service: AmazonBraket
Skipping invalid service: AmazonChimeBusinessCalling
Skipping invalid service: AmazonChimeCallMeAMCS
Skipping invalid service: AmazonChimeCallMe
Skipping invalid service: AmazonChimeDialInAMCS
Skipping invalid service: AmazonChimeDialin
Skipping invalid service: AmazonChimeFeatures
Skipping invalid service: AmazonChimeServices
Skipping invalid service: AmazonChimeVoiceConnector
Skipping invalid service: AmazonChime
Skipping invalid service: AmazonCloudDirectory
Skipping invalid service: AmazonCloudFront
Skipping invalid service: AmazonCloudSearch
Skipping invalid service: AmazonCloudWatch
Skipping invalid service: AmazonCodeWhisperer
Skipping invalid service: AmazonCognitoSync
Skipping invalid service: AmazonCognito
Skipping invalid service: AmazonConnectCases
Skipping invalid service: AmazonConnectVoiceID
Skipping invalid service: AmazonConnect
Skipping invalid service: AmazonDAX
Skipping invalid service: AmazonDataZone
Skipping invalid service: AmazonDeadline
Skipping invalid service: AmazonDetective
Skipping invalid service: AmazonDevOpsGuru
Skipping invalid service: AmazonDocDB
Skipping invalid service: AmazonDynamoDB
Skipping invalid service: AmazonEC2
Skipping invalid service: AmazonECRPublic
Skipping invalid service: AmazonECR
Skipping invalid service: AmazonECS
Skipping invalid service: AmazonEFS
Skipping invalid service: AmazonEI
Skipping invalid service: AmazonEKSAnywhere
Skipping invalid service: AmazonEKS
Skipping invalid service: AmazonES
Skipping invalid service: AmazonETS
Skipping invalid service: AmazonEVS
Skipping invalid service: AmazonElastiCache
Skipping invalid service: AmazonFSx
Skipping invalid service: AmazonFinSpace
Skipping invalid service: AmazonForecast
Skipping invalid service: AmazonFraudDetector
Skipping invalid service: AmazonGameLiftStreams
Skipping invalid service: AmazonGameLift
Skipping invalid service: AmazonGlacier
Skipping invalid service: AmazonGrafana
Skipping invalid service: AmazonGuardDuty
Skipping invalid service: AmazonHealthLake
Skipping invalid service: AmazonHoneycode
Skipping invalid service: AmazonIVSChat
Skipping invalid service: AmazonIVS
Skipping invalid service: AmazonInspectorV2
Skipping invalid service: AmazonInspector
Skipping invalid service: AmazonKendra
Skipping invalid service: AmazonKinesisAnalytics
Skipping invalid service: AmazonKinesisFirehose
Skipping invalid service: AmazonKinesisVideo
Skipping invalid service: AmazonKinesis
Skipping invalid service: AmazonLex
Skipping invalid service: AmazonLightsail
Skipping invalid service: AmazonLocationService
Skipping invalid service: AmazonLookoutEquipment
Skipping invalid service: AmazonLookoutMetrics
Skipping invalid service: AmazonLookoutVision
Skipping invalid service: AmazonMCS
Skipping invalid service: AmazonML
Skipping invalid service: AmazonMQ
Skipping invalid service: AmazonMSK
Skipping invalid service: AmazonMWAA
Skipping invalid service: AmazonMacie
Skipping invalid service: AmazonManagedBlockchain
Skipping invalid service: AmazonMedicalImaging
Skipping invalid service: AmazonMemoryDB
Skipping invalid service: AmazonMonitron
Skipping invalid service: AmazonNeptune
Skipping invalid service: AmazonOmics
Skipping invalid service: AmazonPersonalize
Skipping invalid service: AmazonPinpoint
Skipping invalid service: AmazonPolly
Skipping invalid service: AmazonPrometheus
Skipping invalid service: AmazonQLDB
Skipping invalid service: AmazonQ
Skipping invalid service: AmazonQuickSight
Skipping invalid service: AmazonRDS
Skipping invalid service: AmazonRedshift
Skipping invalid service: AmazonRekognition
Skipping invalid service: AmazonRoute53
Skipping invalid service: AmazonS3GlacierDeepArchive
Skipping invalid service: AmazonS3
Skipping invalid service: AmazonSES
Skipping invalid service: AmazonSNS
Skipping invalid service: AmazonSWF
Skipping invalid service: AmazonSageMaker
Skipping invalid service: AmazonSecurityLake
Skipping invalid service: AmazonSimpleDB
Skipping invalid service: AmazonStates
Skipping invalid service: AmazonSumerian
Skipping invalid service: AmazonTextract
Skipping invalid service: AmazonTimestream
Skipping invalid service: AmazonVPC
Skipping invalid service: AmazonVerifiedPermissions
Skipping invalid service: AmazonWAM
Skipping invalid service: AmazonWorkDocs
Skipping invalid service: AmazonWorkLink
Skipping invalid service: AmazonWorkMail
Skipping invalid service: AmazonWorkSpacesThinClient
Skipping invalid service: AmazonWorkSpacesWeb
Skipping invalid service: AmazonWorkSpaces
Skipping invalid service: AuroraDSQL
Skipping invalid service: CodeGuru
Skipping invalid service: ContactCenterTelecommKR
Skipping invalid service: ContactCenterTelecommZA
Skipping invalid service: ContactCenterTelecomm
Skipping invalid service: ContactLensAmazonConnect
Skipping invalid service: CustomerProfiles
Skipping invalid service: ElasticMapReduce
Skipping invalid service: IngestionServiceSnowball
Skipping invalid service: IngestionService
Skipping invalid service: IoTDeviceDefender
Skipping invalid service: IoTDeviceManagement
Skipping invalid service: OpsWorks
Skipping invalid service: OracleDbAtAWS
Skipping invalid service: PaymentCryptography
Skipping invalid service: SSMSAP
Skipping invalid service: SnowballExtraDays
Skipping invalid service: VMwareCloudOnAWS
Skipping invalid service: awskms
Skipping invalid service: awswaf
Skipping invalid service: mobileanalytics
Skipping invalid service: nimble
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-south-2 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-south-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in eu-north-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in eu-west-3 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in eu-west-2 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in eu-west-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-northeast-3 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-northeast-2 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-northeast-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ca-central-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in sa-east-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-southeast-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in ap-southeast-2 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in eu-central-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in us-east-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in us-east-2 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in us-west-1 including free tier.
Retrieved costs for 0 services from 2025-07-21 to 2025-09-19 in us-west-2 including free tier.
Skipping invalid service: A4B
Skipping invalid service: AWSAmplify
Skipping invalid service: AWSAppFabric
Skipping invalid service: AWSAppRunner
Skipping invalid service: AWSAppStudio
Skipping invalid service: AWSAppSync
Skipping invalid service: AWSApplicationMigrationSvc
Skipping invalid service: AWSB2Bi
Skipping invalid service: AWSBCMPricingCalculator
Skipping invalid service: AWSBackup
Skipping invalid service: AWSBillingConductor
Skipping invalid service: AWSBudgets
Skipping invalid service: AWSCertificateManager
Skipping invalid service: AWSCleanRooms
Skipping invalid service: AWSCloudFormation
Skipping invalid service: AWSCloudMap
Skipping invalid service: AWSCloudTrail
Skipping invalid service: AWSCloudWAN
Skipping invalid service: AWSCodeArtifact
Skipping invalid service: AWSCodeCommit
Skipping invalid service: AWSCodeDeploy
Skipping invalid service: AWSCodePipeline
Skipping invalid service: AWSComputeOptimizer
Skipping invalid service: AWSConfig
Skipping invalid service: AWSCostExplorer
Skipping invalid service: AWSDataExchange
Skipping invalid service: AWSDataSync
Skipping invalid service: AWSDataTransfer
Skipping invalid service: AWSDatabaseMigrationSvc
Skipping invalid service: AWSDeepRacer
Skipping invalid service: AWSDeveloperSupport
Skipping invalid service: AWSDeviceFarm
Skipping invalid service: AWSDirectConnect
Skipping invalid service: AWSDirectoryService
Skipping invalid service: AWSELB
Skipping invalid service: AWSElasticDisasterRecovery
Skipping invalid service: AWSElementalMediaConvert
Skipping invalid service: AWSElementalMediaLive
Skipping invalid service: AWSElementalMediaPackage
Skipping invalid service: AWSElementalMediaStore
Skipping invalid service: AWSElementalMediaTailor
Skipping invalid service: AWSEndUserMessaging3pFees
Skipping invalid service: AWSEnterpriseOnRamp
Skipping invalid service: AWSEntityResolution
Skipping invalid service: AWSEvents
Skipping invalid service: AWSFIS
Skipping invalid service: AWSFMS
Skipping invalid service: AWSGlobalAccelerator
Skipping invalid service: AWSGlueElasticViews
Skipping invalid service: AWSGlue
Skipping invalid service: AWSGreengrass
Skipping invalid service: AWSGroundStation
Skipping invalid service: AWSIAMAccessAnalyzer
Skipping invalid service: AWSIoT1Click
Skipping invalid service: AWSIoTAnalytics
Skipping invalid service: AWSIoTEvents
Skipping invalid service: AWSIoTFleetWise
Skipping invalid service: AWSIoTSiteWise
Skipping invalid service: AWSIoTThingsGraph
Skipping invalid service: AWSIoT
Skipping invalid service: AWSLakeFormation
Skipping invalid service: AWSLambda
Skipping invalid service: AWSM2
Skipping invalid service: AWSMDC
Skipping invalid service: AWSManagedServices
Skipping invalid service: AWSMediaConnect
Skipping invalid service: AWSMigrationHubRefactorSpaces
Skipping invalid service: AWSNetworkFirewall
Skipping invalid service: AWSOutposts
Skipping invalid service: AWSPCS
Skipping invalid service: AWSPrivate5G
Skipping invalid service: AWSQueueService
Skipping invalid service: AWSR53AppRecoveryController
Skipping invalid service: AWSResilienceHub
Skipping invalid service: AWSRoboMaker
Skipping invalid service: AWSSecretsManager
Skipping invalid service: AWSSecurityHub
Skipping invalid service: AWSServiceCatalog
Skipping invalid service: AWSShield
Skipping invalid service: AWSStorageGatewayDeepArchive
Skipping invalid service: AWSStorageGateway
Skipping invalid service: AWSSupplyChain
Skipping invalid service: AWSSupportBusiness
Skipping invalid service: AWSSupportEnterprise
Skipping invalid service: AWSSystemsManager
Skipping invalid service: AWSTelcoNetworkBuilder
Skipping invalid service: AWSTransfer
Skipping invalid service: AWSWickr
Skipping invalid service: AWSWisdom
Skipping invalid service: AWSXRay
Skipping invalid service: AlexaTopSites
Skipping invalid service: AlexaWebInfoService
Skipping invalid service: AmazonA2I
Skipping invalid service: AmazonApiGateway
Skipping invalid service: AmazonAppStream
Skipping invalid service: AmazonAthena
Skipping invalid service: AmazonBedrockService
Skipping invalid service: AmazonBedrock
Skipping invalid service: AmazonBraket
Skipping invalid service: AmazonChimeBusinessCalling
Skipping invalid service: AmazonChimeCallMeAMCS
Skipping invalid service: AmazonChimeCallMe
Skipping invalid service: AmazonChimeDialInAMCS
Skipping invalid service: AmazonChimeDialin
Skipping invalid service: AmazonChimeFeatures
Skipping invalid service: AmazonChimeServices
Skipping invalid service: AmazonChimeVoiceConnector
Skipping invalid service: AmazonChime
Skipping invalid service: AmazonCloudDirectory
Skipping invalid service: AmazonCloudFront
Skipping invalid service: AmazonCloudSearch
Skipping invalid service: AmazonCloudWatch
Skipping invalid service: AmazonCodeWhisperer
Skipping invalid service: AmazonCognitoSync
Skipping invalid service: AmazonCognito
Skipping invalid service: AmazonConnectCases
Skipping invalid service: AmazonConnectVoiceID
Skipping invalid service: AmazonConnect
Skipping invalid service: AmazonDAX
Skipping invalid service: AmazonDataZone
Skipping invalid service: AmazonDeadline
Skipping invalid service: AmazonDetective
Skipping invalid service: AmazonDevOpsGuru
Skipping invalid service: AmazonDocDB
Skipping invalid service: AmazonDynamoDB
Skipping invalid service: AmazonEC2
Skipping invalid service: AmazonECRPublic
Skipping invalid service: AmazonECR
Skipping invalid service: AmazonECS
Skipping invalid service: AmazonEFS
Skipping invalid service: AmazonEI
Skipping invalid service: AmazonEKSAnywhere
Skipping invalid service: AmazonEKS
Skipping invalid service: AmazonES
Skipping invalid service: AmazonETS
Skipping invalid service: AmazonEVS
Skipping invalid service: AmazonElastiCache
Skipping invalid service: AmazonFSx
Skipping invalid service: AmazonFinSpace
Skipping invalid service: AmazonForecast
Skipping invalid service: AmazonFraudDetector
Skipping invalid service: AmazonGameLiftStreams
Skipping invalid service: AmazonGameLift
Skipping invalid service: AmazonGlacier
Skipping invalid service: AmazonGrafana
Skipping invalid service: AmazonGuardDuty
Skipping invalid service: AmazonHealthLake
Skipping invalid service: AmazonHoneycode
Skipping invalid service: AmazonIVSChat
Skipping invalid service: AmazonIVS
Skipping invalid service: AmazonInspectorV2
Skipping invalid service: AmazonInspector
Skipping invalid service: AmazonKendra
Skipping invalid service: AmazonKinesisAnalytics
Skipping invalid service: AmazonKinesisFirehose
Skipping invalid service: AmazonKinesisVideo
Skipping invalid service: AmazonKinesis
Skipping invalid service: AmazonLex
Skipping invalid service: AmazonLightsail
Skipping invalid service: AmazonLocationService
Skipping invalid service: AmazonLookoutEquipment
Skipping invalid service: AmazonLookoutMetrics
Skipping invalid service: AmazonLookoutVision
Skipping invalid service: AmazonMCS
Skipping invalid service: AmazonML
Skipping invalid service: AmazonMQ
Skipping invalid service: AmazonMSK
Skipping invalid service: AmazonMWAA
Skipping invalid service: AmazonMacie
Skipping invalid service: AmazonManagedBlockchain
Skipping invalid service: AmazonMedicalImaging
Skipping invalid service: AmazonMemoryDB
Skipping invalid service: AmazonMonitron
Skipping invalid service: AmazonNeptune
Skipping invalid service: AmazonOmics
Skipping invalid service: AmazonPersonalize
Skipping invalid service: AmazonPinpoint
Skipping invalid service: AmazonPolly
Skipping invalid service: AmazonPrometheus
Skipping invalid service: AmazonQLDB
Skipping invalid service: AmazonQ
Skipping invalid service: AmazonQuickSight
Skipping invalid service: AmazonRDS
Skipping invalid service: AmazonRedshift
Skipping invalid service: AmazonRekognition
Skipping invalid service: AmazonRoute53
Skipping invalid service: AmazonS3GlacierDeepArchive
Skipping invalid service: AmazonS3
Skipping invalid service: AmazonSES
Skipping invalid service: AmazonSNS
Skipping invalid service: AmazonSWF
Skipping invalid service: AmazonSageMaker
Skipping invalid service: AmazonSecurityLake
Skipping invalid service: AmazonSimpleDB
Skipping invalid service: AmazonStates
Skipping invalid service: AmazonSumerian
Skipping invalid service: AmazonTextract
Skipping invalid service: AmazonTimestream
Skipping invalid service: AmazonVPC
Skipping invalid service: AmazonVerifiedPermissions
Skipping invalid service: AmazonWAM
Skipping invalid service: AmazonWorkDocs
Skipping invalid service: AmazonWorkLink
Skipping invalid service: AmazonWorkMail
Skipping invalid service: AmazonWorkSpacesThinClient
Skipping invalid service: AmazonWorkSpacesWeb
Skipping invalid service: AmazonWorkSpaces
Skipping invalid service: AuroraDSQL
Skipping invalid service: CodeGuru
Skipping invalid service: ContactCenterTelecommKR
Skipping invalid service: ContactCenterTelecommZA
Skipping invalid service: ContactCenterTelecomm
Skipping invalid service: ContactLensAmazonConnect
Skipping invalid service: CustomerProfiles
Skipping invalid service: ElasticMapReduce
Skipping invalid service: IngestionServiceSnowball
Skipping invalid service: IngestionService
Skipping invalid service: IoTDeviceDefender
Skipping invalid service: IoTDeviceManagement
Skipping invalid service: OpsWorks
Skipping invalid service: OracleDbAtAWS
Skipping invalid service: PaymentCryptography
Skipping invalid service: SSMSAP
Skipping invalid service: SnowballExtraDays
Skipping invalid service: VMwareCloudOnAWS
Skipping invalid service: awskms
Skipping invalid service: awswaf
Skipping invalid service: mobileanalytics
Skipping invalid service: nimble
+----------+-----------+------------+-----------+----------+---------------+-----------+----------+
| Period   | Service   | Cost ($)   | Account   | Action   | Savings ($)   | Details   | Region   |
+==========+===========+============+===========+==========+===============+===========+==========+      in free thre it show like this 
+----------+-----------+------------+-----------+----------+---------------+-----------+----------+
Recommendation report saved to aws_optimization_report_20250919_164309.json

^Z
[1]+  Stopped                 ./cloudcostbox.py
ubuntu@ip-172-31-32-78:~/test$ cat aws_optimization_report_20250919_164309.json
{
    "5 minutes": {
        "services": {}
    },
    "7 days": {
        "services": {}
    },
    "15 days": {
        "services": {}
    },
    "30 days": {
        "services": {}
    },
    "60 days": {
        "services": {}
    }
}
============================EXPECT OUPUT =====================================================================================================
Starting optimization run at 04:02:00 IST, 2025-09-19
Retrieved 200 AWS services.
Adjusted 5 minutes period start_date to 2025-09-19 for valid range.
Retrieved costs for 5 services from 2025-09-19 to 2025-09-19 in us-east-1 including free tier.
[... Similar logs for other regions ...]
+------------+--------------+----------+----------+----------+-------------+-----------------------------------------------------------+----------+
| Period     | Service      | Cost ($) | Account  | Action   | Savings ($) | Details                                                   | Region   |
+============+==============+==========+==========+==========+=============+===========================================================+==========+
| 5 minutes  | Amazon EC2   | 0.01     | 123456789012 | Optimize | 0.01        | Stop Amazon EC2 instance i-1234567890 (no activity, reduce cost by 100%) | us-east-1 |
| 7 days     | Amazon EC2   | 0.07     | 123456789012 | Optimize | 0.07        | Stop Amazon EC2 instance i-1234567890 (no activity, reduce cost by 100%) | us-east-1 |
| ...        | ...          | ...      | ...      | ...      | ...         | ...                                                       | ...      |
+------------+--------------+----------+----------+----------+-------------+-----------------------------------------------------------+----------+
Recommendation report saved to aws_optimization_report_20250919_040200.json

====================================================================================================================================================
Notes
Free Tier Detection: The script uses a simple heuristic (non-zero cost) to detect exceedance. This assumes free tier usage is $0.00, which may not account for delays in cost data (up to 24 hours). You might not see the table until the next day’s cost data is available.
Current Usage: With 1 hour and 57 minutes, you’re far from the 750-hour limit. To test the table output, you’d need to simulate exceedance (e.g., by launching additional instances or metrics, though this risks charges).
API Limits: The 5-minute loop may hit the 1,000 API request limit. Consider increasing time.sleep(300) to time.sleep(900) if errors occur.

