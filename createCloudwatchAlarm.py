#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#                           |\__/|
#       Welcome             /     \
#                          /_.~ ~,_\
#                             \@/
#
#   #################################
#   #          written by           #
#   #    k.michael@protonmail.ch    #
#   #################################

import boto3
from pprint import pprint
from argparse import ArgumentParser
from sys import argv, exit
import config as c


def listsAllRDS():
    ######### RDS CLIENT ###################
    rds_client = session.client('rds')

    listOfNameRdsInstances = []
    describeRdsInstances = rds_client.describe_db_instances()['DBInstances']
    for i in range(len(describeRdsInstances)):
        if "prod" in describeRdsInstances[i]['DBInstanceIdentifier']:
            listOfNameRdsInstances.append(
                describeRdsInstances[i]['DBInstanceIdentifier'])
        elif "dev" in describeRdsInstances[i]['DBInstanceIdentifier']:
            listOfNameRdsInstances.append(
                describeRdsInstances[i]['DBInstanceIdentifier'])
    return listOfNameRdsInstances


def listsAllEcsServices(cluster_name):
    ######## ECS CLIENT ##########
    ecs_client = session.client("ecs")

    response = ecs_client.list_services(cluster=cluster_name)
    paginator = ecs_client.get_paginator('list_services')

    def paginate(next_token):
        response_iterator = paginator.paginate(
            cluster=cluster_name,
            PaginationConfig={
                'MaxItems': 100,
                'PageSize': 100,
                'StartingToken': next_token,
            },
        )

        listOfNamesServices = [
            name for names in [
                services_name.split('/') for i in response_iterator
                for services_name in i['serviceArns']
            ] for name in names if 'Code' in name
        ]
        return listOfNamesServices

    while 'nextToken' in response:
        services_list = paginate(response['nextToken'])
        return services_list

    return paginate(next_token=None)


def listOfAllClusters():
    ######## ECS CLIENT ##########
    ecs_client = session.client("ecs")

    response = ecs_client.list_clusters()
    lists_clusters = [
        clusters[1] for clusters in [
            clusters_list.split("/")
            for clusters_list in response["clusterArns"]
        ]
    ]
    return lists_clusters


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
    return f"La alarma para el servicio {service_name} se ha creado con exito"

def createRDSAlarm(db_name, sns_topic, threshold):

    cloudwatch_client.put_metric_alarm(
        AlarmName=f"Motor RDS {db_name}-OVER-{threshold}%-HIGH-CPU",
        ComparisonOperator="GreaterThanThreshold",
        EvaluationPeriods=2,
        MetricName="CPUUtilization",
        Namespace="AWS/RDS",
        Period=300,
        Statistic="Average",
        Threshold=threshold,
        ActionsEnabled=True,
        AlarmDescription=
        f"El motor RDS '{db_name}' ha superado el {threshold}% del CPU por mas de 5 minutos",
        AlarmActions=[sns_topic],
        TreatMissingData="missing",
        Dimensions=[{
            "Name": "DBInstanceIdentifier",
            "Value": db_name
        }],
        Unit='Percent')
    return f"La alarma para la DB {db_name} se ha creado con exito"

def createECSAlarmCPU(service_name, cluster_name, sns_topic, threshold):

    cloudwatch_client.put_metric_alarm(
        AlarmName=f'CPU del servicio {service_name}-OVER-{threshold}%-HIGH-CPU',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='CPUUtilization',
        Namespace='AWS/ECS',
        Period=120,
        Statistic='Average',
        Threshold=threshold,
        ActionsEnabled=True,
        AlarmDescription=
        f'El CPU del servicio {service_name} ha estado sobre los {threshold}% en 2 periodos de 2 minutos',
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
    return f"La alarma para el servicio {service_name} se ha creado con exito"
    
def createECSAlarmMEM(service_name, cluster_name, sns_topic, threshold):

    cloudwatch_client.put_metric_alarm(
        AlarmName=f'MemoryUtilization del servicio {service_name}-OVER-{threshold}%-HIGH-MEM',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='MemoryUtilization',
        Namespace='AWS/ECS',
        Period=120,
        Statistic='Average',
        Threshold=threshold,
        ActionsEnabled=True,
        AlarmDescription=
        f'La memoria del servicio {service_name} ha estado sobre los {threshold}% en 2 periodos de 2 minutos',
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
    return f"La alarma para el servicio {service_name} se ha creado con exito"

# Leyendo parametros entregados por la terminal
parser = ArgumentParser(
    description="Crea alarmas en cloudwatch para los servicios ECS y RDS. \
    Tambien pueden ser listados todos los servicios.")

parser.add_argument(
    "-s",
    "--service",
    help="tipo de servicio al cual se le creara la alarma, ej: ecs, rds",
    required=True)
parser.add_argument("-e",
                    "--enviroment",
                    help="Enviroment de trabajo ej: wdev, wstage, wprod",
                    required=True)
parser.add_argument("-t", "--threshold", type=int, help="Threshold entre 0 a 100")
parser.add_argument(
    "-l",
    "--lists",metavar='NOMBRE DEL CLUSTER o all',
    help=
    "Listar motores RDS o servicios actualmente corriendo en el cluster ECS elegido",
    nargs='?')
parser.add_argument(
    "-c",
    "--create", metavar='NOMBRE DEL CLUSTER o RDS o SERVICIO o all',
    help=
    "Crea alarmas para un servicio o todos los servicios de un cluster ECS o RDS \
     ejemplos: -c all, esto mostrara una lista de todos los cluster disponibles y preguntara por una opcion. \
     despues de ingresar la opcion -c creara alarmas para todos los servicios del cluster seleccionado"
)
parser.parse_args(args=None if argv[1:] else ['--help'])

args = parser.parse_args()
env = c.PROFILES[args.enviroment]
sns_topic = c.SNS_TOPIC[args.enviroment]

######### CLIENT SESSION ###############
session = boto3.Session(profile_name=env)

######### CLOUDWATCH CLIENT ############
cloudwatch_client = session.client('cloudwatch')

class Switcher(object):
    def service(self, argument):
        option = getattr(self, argument, lambda: "Invalid option")
        return option()

    def create(self):
        if args.create != "all" and args.service == "ecs":
            if args.enviroment in args.create.split('-'):
                clustername = args.create.split(
                    '-')[0] + "-" + args.create.split('-')[1]
                if "Service" in args.create:
                    metrics = input("Ingrese metrics(parametros disponibles, down, cpu, mem): ")

                    if metrics == "down":
                        response = createEcsAlarm(args.create, clustername, sns_topic)
                        return response
                    elif metrics == "cpu":
                        threshold = input("Ingrese threshold entre 0 a 100: ")
                        response = createECSAlarmCPU(args.create, clustername, sns_topic, int(threshold))
                        return response
                    elif metrics == "mem":
                        threshold = input("Ingrese threshold entre 0 a 100: ")
                        response = createECSAlarmMEM(args.create, clustername, sns_topic, int(threshold))
                        return response
                else:
                    return "El parametro -c debe ser un servicio" 

        elif args.create == "all" and args.service == "ecs":
            print("\nLista de todos los cluster diponibles del ambiente \n")
            print(listOfAllClusters())
            clustername = input("Ingrese el nombre del cluster: ")
            metrics = input("Ingrese metrics(parametros disponibles, down, cpu, mem): ")
            if metrics == "down":
                for i in listsAllEcsServices(clustername):
                    response = createEcsAlarm(i, clustername, sns_topic)
                    return response
            elif metrics == "cpu":
                threshold = input("Ingrese threshold entre 0 a 100: ")
                for i in listsAllEcsServices(clustername):
                    response = createECSAlarmCPU(i, clustername, sns_topic, int(threshold))
                    return response
            elif metrics == "mem":
                threshold = input("Ingrese threshold entre 0 a 100: ")
                for i in listsAllEcsServices(clustername):
                    response = createECSAlarmMEM(i, clustername, sns_topic, int(threshold))
                    return response
        else:
            if args.create == "all" and args.threshold != None and args.service == "rds":
                for i in listsAllRDS():
                    response = createRDSAlarm(i, sns_topic, args.threshold)
                    return response
            elif args.create != "all" and args.service == "rds" and args.threshold != None:
                response = createRDSAlarm(args.create, sns_topic,
                                          args.threshold)
                return response
            else:
                return "Parametro threshold no esta definido"

    def rds(self):
        if args.lists == "all":
            response = listsAllRDS()
            return response
        else:
            if args.create != None:
                return self.create()

    def ecs(self):
        if args.lists != None and args.lists != "all":
            response = listsAllEcsServices(args.lists)
            return response
        elif args.lists == "all":
            return listOfAllClusters()
        elif args.create:
            return self.create()

try:

    s = Switcher()
    response = s.service(args.service)
    print(response)

except Exception as e:
    print(f"Exception occured:{e}")