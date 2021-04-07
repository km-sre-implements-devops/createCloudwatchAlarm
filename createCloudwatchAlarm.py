import boto3
from pprint import pprint
from sys import argv

## args from terminal
profile_name = argv[1]
cluster_name = argv[2]

session = boto3.Session(profile_name=profile_name)

dev_client = session.client('ecs')
cloudwatch_client = session.client('cloudwatch')

response = dev_client.list_services(cluster=cluster_name)

next_token = (response['nextToken'])

paginator = dev_client.get_paginator('list_services')

response_iterator = paginator.paginate(cluster=cluster_name,
                                       PaginationConfig={
                                           'MaxItems': 100,
                                           'PageSize': 100,
                                           'StartingToken': next_token
                                       })

services_names = [
    name for names in [
        services_name.split('/') for i in response_iterator
        for services_name in i['serviceArns']
    ] for name in names if 'Code' in name
]

service_name = ''
sns_topic =''

def createEcsAlarm(service_name, cluster_name, sns_topic):
    cloudwatch_client.put_metric_alarm(
        AlarmName=f'{service_name}-is-DOWN',
        ComparisonOperator='LessThanThreshold',
        EvaluationPeriods=1,
        MetricName='CPUUtilization',
        Namespace='AWS/ECS',
        Period=60,
        Statistic='SampleCount',
        Threshold=1,
        ActionsEnabled=True,
        AlarmDescription=
        f'El servicio {service_name} ha estado caido por mas de 1 minuto',
        AlarmActions=[sns_topic],
        TreatMissingData="missing",
        Dimensions=[
            {
                'Name': 'ClusterName',
                'Value': cluster_name
            },
            {
                'Name': 'ServiceName',
                'Value': service_name
            },
        ],
    )
