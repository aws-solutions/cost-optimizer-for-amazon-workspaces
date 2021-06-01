#!/usr/bin/python 
# -*- coding: utf-8 -*- 
######################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
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

# wco.py
# This is the main program that reads the CloudFormationTempate (CFT) and scans for workspace directories
# It accesses AWS cloud formation and workspaces apis, then calls directory_reader to process each directory
# Regardless of CFT deployment, this processes ALL regions, ALL directories and ALL workspaces for the account

import boto3
import botocore
from botocore.exceptions import ClientError
from botocore.config import Config
import calendar
import logging
import sys
import time
import uuid
import os
import math

from ecs.directory_reader import DirectoryReader
from ecs.utils.solution_metrics import send_metrics

# Set default logging level
ecs_task_start_time = time.perf_counter()
logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', level=logging.INFO)
log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)

endTime = time.strftime("%Y-%m-%dT%H:%M:%SZ")
startTime = time.strftime("%Y-%m") + '-01T00:00:00Z'
lastDay = calendar.monthrange(int(time.strftime("%Y")), int(time.strftime("%m")))[1]
maxRetries = 3
runUUID = str(uuid.uuid4())
anonymousDataEndpoint = 'https://metrics.awssolutionsbuilder.com/generic'
regionCount = 0
directoryCount = 0
botoConfig = Config(
    max_pool_connections=100,
    retries={
        'max_attempts': 20,
        'mode': 'standard'
    },
    user_agent_extra=os.getenv('UserAgentString')
)
list_workspaces_processed = []
totalWorkspaces = 0

# Pull Stack Parameters from environment
# These are assigned by CloudFormation as container environment variables in production,
# or as online params (docker) shell vars when testing

stackParams = {}
for param in {'LogLevel',
              'DryRun',
              'TestEndOfMonth',
              'SendAnonymousData',
              'SolutionVersion',
              'SolutionID',
              'UUID',
              'BucketName',
              'ValueLimit',
              'StandardLimit',
              'PerformanceLimit',
              'PowerLimit',
              'PowerProLimit',
              'GraphicsLimit',
              'GraphicsProLimit'
              }:
    stackParams[param] = os.environ[param]

# Check to make sure we have values for all expected stack parameters, otherwise exit with appropriate log errors

for param in stackParams:
    if stackParams[param] and not stackParams[param].isspace():
        log.info('Parameter: %s, Value: %s', param, stackParams[param])
    else:
        log.error('No value for stack parameter: %s', param)
        sys.exit()

theDay = int(time.strftime('%d'))
# Determine if we should run end-of-month routine.
if theDay == int(lastDay):
    stackParams['TestEndOfMonth'] = 'Yes'
    log.info('Last day of month, setting TestEndOfMonth to Yes')
    log.info('It is the last day of the month, last day is %s and today is %s', lastDay, theDay)
else:
    log.info('It is NOT the last day of the month, last day is %s and today is %s', lastDay, theDay)

# Get all regions that run Workspaces
my_session = boto3.session.Session()
my_region = my_session.region_name

if 'gov' in my_region:
    partition = 'aws-us-gov'
elif 'cn' in my_region:
    partition = 'aws-cn'
else:
    partition = 'aws'

log.debug("Partition is {}".format(partition))

try:
    wsRegions = boto3.session.Session().get_available_regions('workspaces', partition)
except Exception as e:
    log.error("Error getting the regions for the workspaces : {}".format(e))
    raise

# Iterate over list of AWS Regions
for wsRegion in wsRegions:
    regionCount += 1
    wsClient = boto3.client(
        'workspaces',
        region_name=wsRegion,
        config=botoConfig
    )
    log.info('Scanning Workspace Directories for Region %s', wsRegion)

    # Get all the directories within the region
    try:
        response = wsClient.describe_workspace_directories()
        directories = response.get('Directories', [])
        next_token = response.get('NextToken', None)
        while next_token is not None:
            response = wsClient.describe_workspace_directories(
                NextToken=next_token
            )
            directories.extend(response.get('Directories', []))
            next_token = response.get('NextToken', None)
    except botocore.exceptions.ClientError as e:
        log.error("Error while getting the list of Directories for region {}. Error: {}".format(wsRegion, e))
        raise

    for directory in directories:
        directoryCount += 1
        directoryParams = {
            "DirectoryId": directory["DirectoryId"],
            "Region": wsRegion,
            "EndTime": endTime,
            "StartTime": startTime,
            "LastDay": str(lastDay),
            "RunUUID": runUUID,
            "AnonymousDataEndpoint": anonymousDataEndpoint
        }
        log.info('Calling directory reader')
        directoryReader = DirectoryReader()
        workspaceCount, list_workspaces = directoryReader.read_directory(wsRegion, stackParams, directoryParams)
        totalWorkspaces = totalWorkspaces + workspaceCount
        list_workspaces_processed.append(list_workspaces)

ecs_task_end_time = time.perf_counter()
ecs_task_execution_time = math.ceil(ecs_task_end_time - ecs_task_start_time)

if os.getenv('SendAnonymousData').lower() == 'true':
    stackParams.pop("BucketName", None)
    data = {
        "List_of_Workspaces": list_workspaces_processed,
        "Total_Workspaces": totalWorkspaces,
        "Total_Directories": directoryCount,
        "Total_Regions": regionCount,
        "Stack_Parameters": stackParams,
        "ECS_Task_Execution_Time": ecs_task_execution_time
    }
    send_metrics(data)
log.info('Successfully invoked directory_reader for %d workspaces in %d directories across %d regions.',
         totalWorkspaces, directoryCount, regionCount)
