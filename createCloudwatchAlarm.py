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
#from argparse import ArgumentParser
#from configparser import ConfigParser
from sys import argv, exit
#from os import environ

## args from terminal
args = len(argv)
profile = argv[1]
if args == 2 and profile == "dev":
    profile_name = c.PROFILES[profile]
elif args == 2 and profile == "prod":
    profile_name = c.PROFILES[profile]
else:
    cluster_name = ""
if args == 3:
    cluster_name = argv[2]
if args == 4:
    services_alarm = argv[3]

######### CLIENT SESSION ###############
session = boto3.Session(profile_name=profile_name)

######### CLOUDWATCH CLIENT ############
cloudwatch_client = session.client("cloudwatch")


def listsAllRDS():
    ######### RDS CLIENT ###################
    try:
        rds_client = session.client("rds")
    except Exception as err:
        return err

    listOfNameRdsInstances = []
    describeRdsInstances = rds_client.describe_db_instances()["DBInstances"]
    for i in range(len(describeRdsInstances)):
        if "prod" in describeRdsInstances[i]["DBInstanceIdentifier"]:
            listOfNameRdsInstances.append(
                describeRdsInstances[i]["DBInstanceIdentifier"]
            )
        elif "dev" in describeRdsInstances[i]["DBInstanceIdentifier"]:
            listOfNameRdsInstances.append(
                describeRdsInstances[i]["DBInstanceIdentifier"]
            )
    return listOfNameRdsInstances


def listsAllECS(services_alarm, cluster_name):
    ######## ECS CLIENT ##########

    try:
        ecs_client = session.client("ecs")
    except Exception as err:
        return err

    response = ecs_client.list_services(cluster=cluster_name)
    next_token = response["nextToken"]
    paginator = ecs_client.get_paginator("list_services")
    response_iterator = paginator.paginate(
        cluster=cluster_name,
        PaginationConfig={
            "MaxItems": 100,
            "PageSize": 100,
            "StartingToken": next_token,
        },
    )
    listOfNamesServices = [
        name
        for names in [
            services_name.split("/")
            for i in response_iterator
            for services_name in i["serviceArns"]
        ]
        for name in names
        if "Code" in name
    ]
    return listOfNamesServices


def createECSAlarm(service_name, cluster_name, sns_topic):
    try:
        cloudwatch_client.put_metric_alarm(
            AlarmName=f"{service_name}-is-DOWN",
            ComparisonOperator="LessThanThreshold",
            EvaluationPeriods=1,
            MetricName="CPUUtilization",
            Namespace="AWS/ECS",
            Period=60,
            Statistic="SampleCount",
            Threshold=1,
            ActionsEnabled=True,
            AlarmDescription=f"El servicio {service_name} ha estado caido por mas de 1 minuto",
            AlarmActions=[sns_topic],
            TreatMissingData="missing",
            Dimensions=[
                {"Name": "ClusterName", "Value": cluster_name},
                {"Name": "ServiceName", "Value": service_name},
            ],
        )
        return f"La alarma para el {service_name} se ha creado con exito"
    except Exception as err:
        return err


def createRDSAlarm(db_name, sns_topic, threshold):
    try:
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
            AlarmDescription=f"El motor RDS '{db_name}' ha superado el {threshold}% del CPU por mas de 5 minutos",
            AlarmActions=[sns_topic],
            TreatMissingData="missing",
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_name}],
            Unit="Percent",
        )
        return f"La alarma para la DB {db_name} se ha creado con exito"
    except Exception as err:
        return err