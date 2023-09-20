#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from typing import Tuple, Union, Any, List

from workspaces_app.account_registry import AccountRegistry, get_account_registry
from workspaces_app.directory_reader import DirectoryReader
from workspaces_app.utils.solution_metrics import SolutionMetricsHelper
from workspaces_app.utils.s3_utils import upload_report
import workspaces_app.utils.date_utils as date_utils
import botocore
import boto3
import calendar
import logging
import time
import os
import sys
import typing

logger = logging.getLogger(__name__)

boto_config = botocore.config.Config(
    max_pool_connections=100,
    retries={
        'max_attempts': 20,
        'mode': 'standard'
    },
    user_agent_extra=os.getenv('UserAgentString')
)


def configure_logging() -> None:
    """Configure root logger level based on `LogLevel` environment variable."""
    log_level = getattr(logging, str(os.getenv('LogLevel', 'INFO')))
    logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', level=log_level)


def ecs_handler() -> None:
    """Perform workspaces management tasks and upload reports."""
    configure_logging()
    logger.info("Begin ECS task handler.")
    stack_parameters = get_stack_parameters()
    date_time_values = date_utils.get_date_time_values_for_processing()
    solution_metrics_helper = SolutionMetricsHelper(stack_parameters)
    solution_metrics_helper.start_timer()
    partition = get_partition()
    valid_workspaces_regions = get_valid_workspaces_regions(partition)
    regions = process_input_regions(os.getenv('Regions'), valid_workspaces_regions)
    current_account = get_account()
    # Policy: always perform workspaces management on the current account
    accounts = [current_account]
    account_registry: AccountRegistry = get_account_registry(boto3.session.Session())
    accounts.extend(account_registry.get_accounts())

    total_workspaces = 0
    aggregated_csv = 'WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode,' \
                     'Username,Computer Name,DirectoryId,WorkspaceTerminated,Tags,ReportDate\n'
    total_directories = 0
    list_workspaces_processed = []
    sts_client = boto3.client('sts', config=boto_config)
    for account in accounts:
        try:
            spoke_session = None
            if account != current_account:
                response = sts_client.assume_role(
                    RoleArn=account.role_name,
                    RoleSessionName='SessionName')
                spoke_session = boto3.session.Session(
                    aws_access_key_id=response.get('Credentials').get('AccessKeyId'),
                    aws_secret_access_key=response.get('Credentials').get('SecretAccessKey'),
                    aws_session_token=response.get('Credentials').get('SessionToken')
                )
            else:
                spoke_session = boto3.session.Session()

            workspaces_count, report_csv, directory_count, workspaces_processed = process_directories(spoke_session, regions, stack_parameters, date_time_values)

            total_workspaces = total_workspaces + workspaces_count
            aggregated_csv = aggregated_csv + report_csv
            total_directories = total_directories + directory_count
            list_workspaces_processed.append(workspaces_processed)
        except Exception as e:
            logger.error(f"Error processing workspaces for account {account}: {str(e)}")

    upload_report(boto3.session.Session(), date_time_values, stack_parameters, aggregated_csv)

    solution_metrics_helper.report_metrics(list_workspaces_processed, total_workspaces, total_directories, len(regions))

    logger.info("Completed ECS task handler.")


def get_stack_parameters() -> dict:
    """This method gets the input parameters for the stack."""
    logger.debug("Setting the stack parameters")
    stack_parameters = {}
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
        value = os.environ[parameter]
        if value.isspace():
            message = "No value for stack parameter: {}".format(parameter)
            logger.error(message)
            raise ValueError(message)
        stack_parameters[parameter] = value
        logger.info('Parameter: %s, Value: %s', parameter, value)

    # Override stack param if it is actually the last day of the month
    set_end_of_month(stack_parameters)

    logger.debug("Successfully set the stack parameters")
    return stack_parameters


def set_end_of_month(stack_parameters: dict) -> None:
    """This method sets the end of the month property for the object `stack_parameter`"""
    logger.debug("Setting the TestEndOfMonth parameter")
    today = int(time.strftime('%d', time.gmtime()))
    last_day = calendar.monthrange(int(time.strftime("%Y", time.gmtime())), int(time.strftime("%m", time.gmtime())))[1]
    if today == last_day:
        stack_parameters['TestEndOfMonth'] = 'Yes'
        logger.info('Last day of month, setting TestEndOfMonth to Yes')
        logger.info('It is the last day of the month, last day is %s and today is %s', last_day, today)
    else:
        logger.info('It is NOT the last day of the month, last day is %s and today is %s', last_day, today)
    logger.debug("Set the TestEndOfMonth parameter as {}".format(stack_parameters['TestEndOfMonth']))


def get_partition():
    """
    This method gets the partition based the STS caller identity.
    """
    logger.debug("Getting the value for the partition")
    my_session = boto3.session.Session()
    sts_client = my_session.client('sts', config=boto_config)
    partition = sts_client.get_caller_identity()['Arn'].split(':')[1]
    logger.debug("Returning the partition value as {}".format(partition))
    return partition


def get_account() -> str:
    """This method gets the partition based the STS caller identity."""
    logger.debug('Getting the value for the account')
    my_session = boto3.session.Session()
    sts_client = my_session.client('sts', config=boto_config)
    account = sts_client.get_caller_identity()['Account']
    logger.debug('Returning the account value as %s', account)
    return account


def get_valid_workspaces_regions(partition):
    """
    :param: partition: AWS partition
    :return: List of supported AWS region
    This method returns the list of AWS regions where the Worskapces service is supported.
    """
    logger.debug("Getting the regions where Workspace service is supported for partition {}".format(partition))
    list_valid_workspaces_regions = []
    if partition == 'aws-us-gov':
        list_valid_workspaces_regions = ['us-gov-west-1']
    elif partition == 'aws-cn':
        list_valid_workspaces_regions = ['cn-northwest-1']
    elif partition == 'aws':
        list_valid_workspaces_regions = ['ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'ap-southeast-1',
                                            'ap-southeast-2', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2',
                                            'sa-east-1', 'us-east-1', 'us-west-2', 'af-south-1']
    elif partition == 'aws-iso':
        list_valid_workspaces_regions = ['us-iso-east-1', 'us-iso-west-1']
    elif partition == 'aws-iso-b':
        list_valid_workspaces_regions = ['us-isob-east-1']
    try:
        list_valid_workspaces_regions = boto3.session.Session().get_available_regions('workspaces', partition)
    except Exception as e:
        logger.error("Error getting the regions for the workspaces. Defaulting to set valid regions: {}".format(e))

    logger.debug("Returning the regions where Workspace service is supported as {}".format(list_valid_workspaces_regions))
    return list_valid_workspaces_regions


def process_input_regions(requested_regions: str, valid_workspaces_regions: typing.List[str]) -> typing.Set[str]:
    """
    :param:valid_workspaces_regions: List of AWS regions where Workspace service is supported.
    :return: List of AWS regions which the solution will process based on the customer input
    This function returns the list of AWS regions which are intersection of customer input regions and valid workspaces regions.
    """
    logger.debug("Checking the input regions for the solution and finding the valid regions")
    logger.debug("The input regions for the solution are: {}".format(requested_regions))
    if len(requested_regions):
        input_regions = [region.replace('"', '').strip() for region in requested_regions.split(",")]
        set_workspace_regions = set(valid_workspaces_regions).intersection(input_regions)
    else:
        set_workspace_regions = set(valid_workspaces_regions)
    logger.debug("The final list of regions to process based on the input regions is {}".format(set_workspace_regions))
    return set_workspace_regions


def get_workspaces_directories(session: boto3.session.Session, region: str) -> typing.List[dict]:
    """
    :param: AWS region
    :return: List of workspace directories for a given region.
    This method returns the list of AWS directories in the given region.
    """
    logger.debug("Getting the workspace directories for the region {}".format(region))
    list_directories = []
    try:
        workspace_client = session.client(
            'workspaces',
            region_name=region,
            config=boto_config
        )
        logger.info('Scanning Workspace Directories for Region %s', region)
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
        logger.error("Error while getting the list of Directories for region {}. Error: {}".format(region, e))
    logger.debug("Returning the list of directories as {}".format(list_directories))
    return list_directories


def process_directories(
        session: boto3.session.Session,
        workspaces_regions: typing.Set[str],
        stack_parameters: dict,
        date_time_values: dict
        ) -> tuple[Union[int, Any], Union[str, Any], Union[int, Any], list[list[dict]]]:
    """
    :param: List of AWS regions.
    This method processes all the workspaces for the given list of AWS regions.
    """
    logger.debug("Processing the workspaces for the list of regions {}".format(workspaces_regions))
    total_workspaces = 0
    aggregated_csv = ''
    directory_count = 0
    list_workspaces_processed = []
    for region in workspaces_regions:
        list_directories = get_workspaces_directories(session, region)
        for directory in list_directories:
            try:
                logger.debug("Processing the directory {}".format(directory))
                directory_count = directory_count + 1
                directory_params = {
                    "DirectoryId": directory.get("DirectoryId"),
                    "Region": region,
                    "DateTimeValues": date_time_values,
                    "AnonymousDataEndpoint": 'https://metrics.awssolutionsbuilder.com/generic'
                }
                directory_reader = DirectoryReader(session)
                workspace_count, list_workspaces, directory_csv = directory_reader.process_directory(
                    region,
                    stack_parameters,
                    directory_params
                )
                total_workspaces = total_workspaces + workspace_count
                list_workspaces_processed.append(list_workspaces)
                aggregated_csv = aggregated_csv + directory_csv
            except Exception:
                logger.error("Error while processing the directory {}".format(directory.get("DirectoryId")))

    return total_workspaces, aggregated_csv, directory_count, list_workspaces_processed


if __name__ == "__main__":
    ecs_handler()
