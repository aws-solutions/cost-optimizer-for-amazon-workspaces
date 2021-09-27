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
from ecs.utils.s3_utils import upload_report

# Set default logging level
logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', level=logging.INFO)
log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)

# Setting the boto config
boto_config = Config(
    max_pool_connections=100,
    retries={
        'max_attempts': 20,
        'mode': 'standard'
    },
    user_agent_extra=os.getenv('UserAgentString')
)

# Get start time and end time
start_time = time.strftime("%Y-%m", time.gmtime()) + '-01T00:00:00Z'
end_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
today = int(time.strftime('%d', time.gmtime()))
last_day = calendar.monthrange(int(time.strftime("%Y", time.gmtime())), int(time.strftime("%m", time.gmtime())))[1]

# End point to send metrics data
metrics_endpoint = 'https://metrics.awssolutionsbuilder.com/generic'

# uuid for the solution
run_uuid = str(uuid.uuid4())

# Declare variables
REGIONS = (os.getenv('Regions'))
list_workspaces_processed = []
total_workspaces = 0
region_count = 0
directory_count = 0
max_retries = 3
aggregated_csv = 'WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode,' \
                 'Username,Computer Name,DirectoryId,WorkspaceTerminated,Tags\n'

# Initialize stack parameters
stack_parameters = {}


def ecs_handler():
    log.info("Begin ECS task handler.")
    global region_count
    ecs_task_start_time = time.perf_counter()
    set_stack_parameters()
    set_end_of_month()
    partition = get_partition()
    valid_workspaces_regions = get_valid_workspaces_regions(partition)
    set_workspaces_regions = process_input_regions(valid_workspaces_regions)
    region_count = len(set_workspaces_regions)
    process_directories(set_workspaces_regions)
    upload_report(stack_parameters, aggregated_csv)
    ecs_task_end_time = time.perf_counter()
    ecs_task_execution_time = math.ceil(ecs_task_end_time - ecs_task_start_time)
    send_workspaces_metrics(ecs_task_execution_time)
    log.info("Completed ECS task handler.")


def set_stack_parameters():
    """
    This method adds the input parameters for the stack to the stack_parameter object.
    """
    log.debug("Setting the stack parameters")
    for parameter in {
        'LogLevel',
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
        'GraphicsProLimit',
        'TerminateUnusedWorkspaces'
    }:
        stack_parameters[parameter] = os.environ[parameter]

    for parameter in stack_parameters:
        if stack_parameters[parameter] and not stack_parameters[parameter].isspace():
            log.info('Parameter: %s, Value: %s', parameter, stack_parameters[parameter])
        else:
            log.error('No value for stack parameter: %s', parameter)
            sys.exit()
    log.debug("Successfully set the stack parameters")


def set_end_of_month():
    """
    This method sets the end of the month property for the object stack_parameter
    """
    log.debug("Setting the TestEndOfMonth parameter")
    if today == last_day:
        stack_parameters['TestEndOfMonth'] = 'Yes'
        log.info('Last day of month, setting TestEndOfMonth to Yes')
        log.info('It is the last day of the month, last day is %s and today is %s', last_day, today)
    else:
        log.info('It is NOT the last day of the month, last day is %s and today is %s', last_day, today)
    log.debug("Set the TestEndOfMonth parameter as {}".format(stack_parameters['TestEndOfMonth']))


def get_partition():
    """
    This method gets the partition based on the region of deployment.
    """
    log.debug("Getting the value for the partition")
    my_session = boto3.session.Session()
    my_region = my_session.region_name
    log.debug("The region is {}".format(my_region))
    if 'gov' in my_region:
        partition = 'aws-us-gov'
    elif 'cn' in my_region:
        partition = 'aws-cn'
    else:
        partition = 'aws'
    log.debug("Returning the partition value as {}".format(partition))
    return partition


def get_valid_workspaces_regions(partition):
    """
    :param: parition: AWS parition
    :return: List of supported AWS region
    This method returns the list of AWS regions where the Worskapces service is supported.
    """
    log.debug("Getting the regions where Workspace service is supported for partition {}".format(partition))
    list_valid_workspaces_regions = []
    if partition == 'aws-us-gov':
        list_valid_workspaces_regions = ['us-gov-west-1']
    elif partition == 'aws-cn':
        list_valid_workspaces_regions = ['cn-northwest-1']
    elif partition == 'aws':
        list_valid_workspaces_regions = ['ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'ap-southeast-1',
                                         'ap-southeast-2', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2',
                                         'sa-east-1', 'us-east-1', 'us-west-2']
    try:
        list_valid_workspaces_regions = boto3.session.Session().get_available_regions('workspaces', partition)
    except Exception as e:
        log.error("Error getting the regions for the workspaces. Defaulting to set valid regions: {}".format(e))

    log.debug("Returning the regions where Workspace service is supported as {}".format(list_valid_workspaces_regions))
    return list_valid_workspaces_regions


def process_input_regions(valid_workspaces_regions):
    """
    :param:valid_workspaces_regions: List of AWS regions where Workspace service is supported.
    :return: List of AWS regions which the solution will process based on the customer input
    This function returns the list of AWS regions which are intersection of customer input regions and valid workspaces regions.
    """
    log.debug("Checking the input regions for the solution and finding the valid regions")
    log.debug("The input regions for the solution are: {}".format(REGIONS))
    if len(REGIONS):
        input_regions = [region.replace('"', '').strip() for region in REGIONS.split(",")]
        set_workspace_regions = set(valid_workspaces_regions).intersection(input_regions)
    else:
        set_workspace_regions = set(valid_workspaces_regions)
    log.debug("The final list of regions to process based on the input regions is {}".format(set_workspace_regions))
    return set_workspace_regions


def get_workspaces_directories(region):
    """
    :param: AWS region
    :return: List of workspace directories for a given region.
    This method returns the list of AWS directories in the given region.
    """
    log.debug("Getting the workspace directories for the region {}".format(region))
    list_directories = []
    try:
        workspace_client = boto3.client(
            'workspaces',
            region_name=region,
            config=boto_config
        )
        log.info('Scanning Workspace Directories for Region %s', region)
        response = workspace_client.describe_workspace_directories()
        list_directories = response.get('Directories', [])
        next_token = response.get('NextToken', None)
        while next_token is not None:
            response = workspace_client.describe_workspace_directories(
                NextToken=next_token
            )
            list_directories.extend(response.get('Directories', []))
            next_token = response.get('NextToken', None)
    except botocore.exceptions.ClientError as e:
        log.error("Error while getting the list of Directories for region {}. Error: {}".format(region, e))
    log.debug("Returning the list of directories as {}".format(list_directories))
    return list_directories


def process_directories(workspaces_regions):
    """
    :param: List of AWS regions.
    This method processes all the workspaces for the given list of AWS regions.
    """
    log.debug("Processing the workspaces for the list of regions {}".format(workspaces_regions))
    global total_workspaces, aggregated_csv, directory_count
    for region in workspaces_regions:
        list_directories = get_workspaces_directories(region)
        for directory in list_directories:
            log.debug("Processing the directory {}".format(directory))
            directory_count = directory_count + 1
            directory_params = {
                "DirectoryId": directory["DirectoryId"],
                "Region": region,
                "EndTime": end_time,
                "StartTime": start_time,
                "LastDay": str(last_day),
                "RunUUID": run_uuid,
                "AnonymousDataEndpoint": metrics_endpoint
            }
            directory_reader = DirectoryReader()
            workspace_count, list_workspaces, directory_csv = directory_reader.process_directory(region, stack_parameters, directory_params)
            total_workspaces = total_workspaces + workspace_count
            list_workspaces_processed.append(list_workspaces)
            aggregated_csv = aggregated_csv + directory_csv


def send_workspaces_metrics(task_execution_time):
    """
    :param: task_execution_time: ecs task execution time.
    This methods sends the metrics for the wco solution.
    """
    if os.getenv('SendAnonymousData').lower() == 'true':
        stack_parameters.pop("BucketName", None)
        data = {
            "List_of_Workspaces": list_workspaces_processed,
            "Total_Workspaces": total_workspaces,
            "Total_Directories": directory_count,
            "Total_Regions": region_count,
            "Stack_Parameters": stack_parameters,
            "ECS_Task_Execution_Time": task_execution_time
        }
        send_metrics(data)


if __name__ == "__main__":
    ecs_handler()
