#!/usr/bin/python 
# -*- coding: utf-8 -*- 
######################################################################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# create-task.py
# This code creates a task based on an existing task definition, it is run from a lambda service
# The task will be scheduled using normal CloudWatch events scheduler defined in the CloudFormation template
# We will replace scheduling with a Fargate scheduled task once that feature is available in the SDK or CloudFormation
# Cluster, TaskDefinition, and Subnets are provided as cached environment variables via CloudFormation

import boto3
import os
import logging
from botocore.config import Config

botoConfig = Config(user_agent_extra=os.getenv('USER_AGENT_STRING'))


def lambda_handler(event, context):
    log = logging.getLogger()
    LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
    log.setLevel(LOG_LEVEL)

    CLUSTER = os.getenv('CLUSTER')
    TASKDEFINITION = os.getenv('TASK_DEFINITION')
    SUBNETS = os.getenv('SUBNETS').split(',')
    SECURITYGROUPS = os.getenv('SECURITY_GROUPS').split(',')

    log.info('Cluster: %s', CLUSTER)
    log.info('Task Definition: %s', TASKDEFINITION)
    log.info('Subnets: %s', SUBNETS)
    log.info('Security Groups: %s', SECURITYGROUPS)

    client = boto3.client('ecs', config=botoConfig)

    response = client.run_task(
        cluster=CLUSTER,
        launchType='FARGATE',
        taskDefinition=TASKDEFINITION,
        count=1,
        platformVersion='LATEST',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': SUBNETS,
                'securityGroups': SECURITYGROUPS,
                'assignPublicIp': 'ENABLED'
            }
        })
    return str(response)
