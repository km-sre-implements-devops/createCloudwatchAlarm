import boto3
from pprint import pprint
import os

session = boto3.Session(profile_name="")

dev_client = session.client('ecs')
cloudwatch_client = session.client('cloudwatch')
cluster_name = ""
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

# Crea la alarma
service_name = ''
cloudwatch_client.put_metric_alarm(
    AlarmName=f'{service_name}-is-DOWN',
    ComparisonOperator='LessThanThreshold',
    EvaluationPeriods=1,
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Period=60,
    Statistic='SampleCount',
    Threshold=1,
    AlarmDescription=
    f'El servicio {service_name} ha estado caido por mas de 1 minuto',
    AlarmActions=[''],
    Dimensions=[
        {
            'Name': 'ClusterName',
            'Value': cluster_name
        },
        {
            'Name': 'InstanceId',
            'Value': service_name
        },
    ])
