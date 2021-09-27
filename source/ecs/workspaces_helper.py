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

# This file reads the AWS workspaces properties and will change the billing preference if necessary
# It calls the metrics_helper to determine if changes are required

import boto3
import botocore
from botocore.config import Config
from botocore.exceptions import ClientError
import logging
import os
import time
import calendar
import datetime
from ecs.metrics_helper import MetricsHelper

log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)

botoConfig = Config(
    max_pool_connections=100,
    retries={
        'max_attempts': 20,
        'mode': 'standard'
    },
    user_agent_extra=os.getenv('UserAgentString')
)

ALWAYS_ON = "ALWAYS_ON"
AUTO_STOP = "AUTO_STOP"
TERMINATE_UNUSED_WORKSPACES = os.getenv('TerminateUnusedWorkspaces')
today = int(time.strftime('%d', time.gmtime()))
last_day = calendar.monthrange(int(time.strftime("%Y", time.gmtime())), int(time.strftime("%m", time.gmtime())))[1]
year_month_string = "%Y-%m"
first_day = time.strftime(year_month_string, time.gmtime()) + '-01T00:00:00Z'  # get the first day of the month
second_day = time.strftime(year_month_string, time.gmtime()) + '-02T00:00:00Z'  # get the second day of the month
current_month_first_day = datetime.datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()


class WorkspacesHelper(object):

    def __init__(self, settings):
        self.settings = settings
        self.max_retries = 20
        self.metrics_helper = MetricsHelper(self.settings.get('region'))
        self.workspaces_client = boto3.client(
            'workspaces',
            region_name=self.settings.get('region'),
            config=botoConfig
        )
        self.cloudwatch_client = boto3.client(
            'cloudwatch',
            region_name=self.settings.get('region'),
            config=botoConfig
        )

    def process_workspace(self, workspace):
        """
        This method processes the given workspace and returns an object with the result
        :param workspace:
        :return: Object with the results of optimization
        """
        workspace_id = workspace['WorkspaceId']
        log.debug('workspaceID: %s', workspace_id)
        workspace_running_mode = workspace['WorkspaceProperties']['RunningMode']
        log.debug('workspaceRunningMode: %s', workspace_running_mode)
        workspace_bundle_type = workspace['WorkspaceProperties']['ComputeTypeName']
        log.debug('workspaceBundleType: %s', workspace_bundle_type)
        billable_time = self.metrics_helper.get_billable_hours(self.settings['startTime'], self.settings['endTime'],
                                                               workspace)
        tags = self.get_tags(workspace_id)
        if self.check_for_skip_tag(tags):
            log.info('Skipping WorkSpace %s due to Skip_Convert tag', workspace_id)
            hourly_threshold = "n/a"
            workspace_terminated = ''
            optimization_result = {
                'resultCode': '-S-',
                'newMode': workspace_running_mode
            }
        else:
            hourly_threshold = self.get_hourly_threshold(workspace_bundle_type)
            workspace_terminated = self.get_termination_status(workspace_id, billable_time, tags)
            optimization_result = self.compare_usage_metrics(workspace_id, billable_time, hourly_threshold,
                                                             workspace_running_mode)
        return {
            'workspaceID': workspace_id,
            'billableTime': billable_time,
            'hourlyThreshold': hourly_threshold,
            'optimizationResult': optimization_result['resultCode'],
            'newMode': optimization_result['newMode'],
            'bundleType': workspace_bundle_type,
            'initialMode': workspace_running_mode,
            'userName': workspace['UserName'],
            'computerName': workspace['ComputerName'],
            'directoryId': workspace['DirectoryId'],
            'tags': tags,
            'workspaceTerminated': workspace_terminated
        }

    def get_hourly_threshold(self, bundle_type):
        """
        Returns the hourly threshold value for the given bundle type.
        :param bundle_type:
        :return:
        """
        if bundle_type in self.settings.get('hourlyLimits'):
            return int(self.settings.get('hourlyLimits')[bundle_type])
        else:
            return None

    def check_for_skip_tag(self, tags):
        """
        Return a boolean value to indicate if the workspace needs to be skipped from the solution workflow
        :param tags:
        :return: True or False to indicate if the workspace can be skipped
        """
        # Added for case insensitive matching.  Works with standard alphanumeric tags
        if tags is None:
            return True
        else:
            for tag_pair in tags:
                if tag_pair['Key'].lower() == 'Skip_Convert'.lower():
                    return True

        return False

    def get_tags(self, workspace_id):
        """
        Return the list of the tags on the given workspace.
        :param workspace_id:
        :return: List of tags for the workspace
        """
        try:
            workspace_tags = self.workspaces_client.describe_tags(
                ResourceId=workspace_id
            )
            log.debug(workspace_tags)
            tags = workspace_tags['TagList']
        except botocore.exceptions.ClientError as error:
            log.error("Error {} while getting tags for the workspace {}".format(error, workspace_id))
            return None
        return tags

    def modify_workspace_properties(self, workspace_id, new_running_mode):
        """
        This method changes the running mode of the workspace to the give new running mode.
        :param workspace_id:
        :param new_running_mode:
        :return: Result code to indicate new running mode for the workspace
        """
        log.debug('modifyWorkspaceProperties')
        if not self.settings.get('isDryRun'):
            try:
                self.workspaces_client.modify_workspace_properties(
                    WorkspaceId=workspace_id,
                    WorkspaceProperties={'RunningMode': new_running_mode}
                )
            except Exception as e:
                log.error('Exceeded retries for %s due to error: %s', workspace_id, e)
                return '-E-'  # return the status to indicate that the workspace was not processed.
        else:
            log.info('Skipping modifyWorkspaceProperties for Workspace %s due to dry run', workspace_id)

        if new_running_mode == ALWAYS_ON:
            result = '-M-'
        else:
            result = '-H-'
        return result

    def get_workspaces_for_directory(self, directory_id):
        """
        :param: AWS region
        :return: List of workspaces for a given directory.
        This method returns the list of AWS directories in the given region.
        """
        log.debug("Getting the workspace  for the directory {}".format(directory_id))
        list_workspaces = []
        try:
            response = self.workspaces_client.describe_workspaces(
                DirectoryId=directory_id
            )
            list_workspaces = response.get('Workspaces', [])
            next_token = response.get('NextToken', None)
            while next_token is not None:
                response = self.workspaces_client.describe_workspaces(
                    DirectoryId=directory_id,
                    NextToken=next_token
                )
                list_workspaces.extend(response.get('Directories', []))
                next_token = response.get('NextToken', None)
        except botocore.exceptions.ClientError as e:
            log.error(
                "Error while getting the list of workspace for directory ID {}. Error: {}".format(directory_id, e))
        log.debug("Returning the list of directories as {}".format(list_workspaces))
        return list_workspaces

    def get_termination_status(self, workspace_id, billable_time, tags):
        """
        This method returns whether the workspace needs to be terminated.
        :param workspace_id:
        :param billable_time:
        :param tags:
        :return: 'Yes' if the workspace is terminated and '' if not.
        """

        log.debug("Today is {}".format(today))
        log.debug("Last day is {}".format(last_day))
        log.debug("Getting the termination status for workspace: {}, billable time: {} and tags {}".
                  format(workspace_id, billable_time, tags))
        log.debug("Terminate unused workspaces parameter is set to {}".format(TERMINATE_UNUSED_WORKSPACES))
        log.debug("Current month first day is {}".format(current_month_first_day))
        workspace_terminated = ''
        try:  # change this back after testing
            if (TERMINATE_UNUSED_WORKSPACES == "Yes" or TERMINATE_UNUSED_WORKSPACES == "Dry Run") and today == last_day:
                log.debug("Today is the last day of the month. Processing further.")
                last_known_user_connection_timestamp = self.get_last_known_user_connection_timestamp(workspace_id)
                workspace_used_in_current_month = self.check_workspace_usage_for_current_month(
                    last_known_user_connection_timestamp)
                workspace_available_on_first_day_of_month = self.check_if_workspace_available_on_first_day(workspace_id)
                log.debug(
                    "For workspace {}, billable time is {}, tags are {}, workspace_available_on_first_day_of_month"
                    " is {}, workspace_used_in_current_month is {}".format(workspace_id, billable_time, tags,
                                                                           workspace_available_on_first_day_of_month,
                                                                           workspace_used_in_current_month))
                if not workspace_used_in_current_month and workspace_available_on_first_day_of_month and billable_time == 0:
                    log.debug("The workspace {} was not used in current month. Checking other criteria for "
                              "termination.".format(workspace_id))
                    workspace_terminated = self.check_if_workspace_needs_to_be_terminated(workspace_id)
        except Exception as error:
            log.error("Error {} while checking the workspace termination status for workspace : {}".format(error,
                                                                                                           workspace_id))
        log.debug("Returning the termination status as {}".format(workspace_terminated))
        return workspace_terminated

    def get_last_known_user_connection_timestamp(self, workspace_id):
        """
        This method return the LastKnownUserConnectionTimestamp for the given workspace_id
        :param: ID for the given workspace
        :return: LastKnownUserConnectionTimestamp for the workspace
        """
        log.debug("Getting the last known user connection timestamp for the workspace_id {}".format(workspace_id))
        try:
            response = self.workspaces_client.describe_workspaces_connection_status(
                WorkspaceIds=[workspace_id]
            )
            last_known_timestamp = response['WorkspacesConnectionStatus'][0].get('LastKnownUserConnectionTimestamp')
        except Exception as error:
            log.error(error)
            return None
        log.debug("Returning the last known timestamp as {}".format(last_known_timestamp))
        return last_known_timestamp

    def check_workspace_usage_for_current_month(self, last_known_user_connection_timestamp):
        """
        This method returns a boolean value to indicate if the workspace was used in current month
        :param: last_known_user_connection_timestamp: Last known connection timestamp
        :return: returns a boolean value to indicate if the workspace was used in current month
        """
        log.debug("Checking the workspace usage for the current month")
        workspace_used_in_current_month = True
        try:
            if last_known_user_connection_timestamp is not None:
                log.debug("Last know timestamp value is not None. Processing further.")
                log.debug("Current month first day is {}".format(current_month_first_day))
                last_known_user_connection_day = last_known_user_connection_timestamp.date()
                workspace_used_in_current_month = not last_known_user_connection_day < current_month_first_day
        except Exception as error:
            log.error("Error occurred while checking the workspace usage for the workspace: {}".format(error))
        log.debug("Returning the workspace usage in current month as {}".format(workspace_used_in_current_month))
        return workspace_used_in_current_month

    def check_if_workspace_available_on_first_day(self, workspace_id):
        """
        This methods checks if the workspace was available on the first day of the month
        :param workspace_id: Workspace ID for the workspace
        """

        workspace_available = False
        log.debug("Checking if the workspace {} was available between first day {} and "
                  "second day {} ".format(workspace_id, first_day, second_day))
        try:
            metrics = self.cloudwatch_client.get_metric_statistics(
                Dimensions=[{
                    'Name': 'WorkspaceId',
                    'Value': workspace_id
                }],
                Namespace='AWS/WorkSpaces',
                MetricName='Available',
                StartTime=first_day,
                EndTime=second_day,
                Period=300,
                Statistics=['Maximum']
            )
            if metrics.get('Datapoints', None):
                workspace_available = True
        except Exception as error:
            log.error(error)
        log.debug("Returning the value {} for workspace available.".format(workspace_available))
        return workspace_available

    def check_if_workspace_needs_to_be_terminated(self, workspace_id):
        """
        This method checks if the workspace needs to terminated based on the usage.
        :param workspace_id:
        :param billable_time:
        :param tags:
        :return: A string value 'Yes' if the workspace is terminate and an empty string '' if not terminated
        """
        workspace_terminated = ''
        if self.settings.get('terminateUnusedWorkspaces') == 'Dry Run':
            log.debug("Termination option for workspace {} is set to DryRun. The report was updated but the "
                      "terminate action was not called".format(workspace_id))
            workspace_terminated = 'Yes - Dry Run'
        elif self.settings.get('terminateUnusedWorkspaces') == 'Yes' and not self.settings.get('isDryRun'):
            log.debug('All the criteria for termination of workspace {} are met. Calling the terminate '
                      'action.'.format(workspace_id))
            workspace_terminated = self.terminate_unused_workspace(workspace_id)
        return workspace_terminated

    def terminate_unused_workspace(self, workspace_id):
        """
        This methods terminates the given workspace.
        :param workspace_id: Workspace ID for the workspace
        """
        log.debug("Terminating the workspace with workspace id {}".format(workspace_id))
        workspace_terminated = ''
        try:
            response = self.workspaces_client.terminate_workspaces(
                TerminateWorkspaceRequests=[
                    {
                        'WorkspaceId': workspace_id
                    },
                ]
            )
            if not response.get('FailedRequests'):
                workspace_terminated = 'Yes'
                log.debug("Successfully terminated the workspace with workspace id {}".format(workspace_id))
        except Exception as error:
            log.error("Error {} occurred when terminating workspace {}".format(error, workspace_id))
        return workspace_terminated

    def compare_usage_metrics(self, workspace_id, billable_time, hourly_threshold, workspace_running_mode):
        """
        This method compares the usage metrics for the workspace
        :param workspace_id: workspace id
        :param billable_time: billable time
        :param hourly_threshold: hourly threshold for the bundle type
        :param workspace_running_mode: new running mode
        :return: The result code and the new running mode for the workspace
        """
        if billable_time is None:
            result_code = '-E-'
            new_mode = workspace_running_mode
        elif hourly_threshold is None:
            result_code = '-S-'
            new_mode = workspace_running_mode
        elif workspace_running_mode == AUTO_STOP:
            result_code, new_mode = self.compare_usage_metrics_for_auto_stop(workspace_id, billable_time,
                                                                             hourly_threshold, workspace_running_mode)
        elif workspace_running_mode == ALWAYS_ON:
            result_code, new_mode = self.compare_usage_metrics_for_always_on(workspace_id, billable_time,
                                                                             hourly_threshold, workspace_running_mode)
        else:
            log.error(
                'workspaceRunningMode {} is unrecognized for workspace {}'.format(workspace_running_mode, workspace_id))
            result_code = '-S-'
            new_mode = workspace_running_mode

        return {
            'resultCode': result_code,
            'newMode': new_mode
        }

    def compare_usage_metrics_for_auto_stop(self, workspace_id, billable_time, hourly_threshold,
                                            workspace_running_mode):
        """
        This method compares the usage metrics for Auto stop mode
        :param workspace_id: workspace id
        :param billable_time: billable time
        :param hourly_threshold: hourly threshold
        :param workspace_running_mode: workspace running mode
        :return: Result code and new running mode
        """
        log.debug('workspaceRunningMode {} == AUTO_STOP'.format(workspace_running_mode))

        # If billable time is over the threshold for this bundle type
        if billable_time > hourly_threshold:
            log.debug('billableTime {} > hourlyThreshold {}'.format(billable_time, hourly_threshold))

            # Change the workspace to ALWAYS_ON
            result_code = self.modify_workspace_properties(workspace_id, ALWAYS_ON)
            # if there was an exception in the modify workspace API call, new mode is same as old mode
            if result_code == '-E-':
                new_mode = AUTO_STOP
            else:
                new_mode = ALWAYS_ON

        # Otherwise, report no change for the Workspace
        else:  # billable_time <= hourly_threshold:
            log.debug('billableTime {} <= hourlyThreshold {}'.format(billable_time, hourly_threshold))
            result_code = '-N-'
            new_mode = AUTO_STOP

        return result_code, new_mode

    def compare_usage_metrics_for_always_on(self, workspace_id, billable_time, hourly_threshold,
                                            workspace_running_mode):
        """
        This method compares the usage metrics for Always ON mode
        :param workspace_id: workspace id
        :param billable_time: billable time
        :param hourly_threshold: hourly threshold
        :param workspace_running_mode: workspace running mode
        :return: Result code and new running mode
        """
        log.debug('workspaceRunningMode {} == ALWAYS_ON'.format(workspace_running_mode))

        # Only perform metrics gathering for ALWAYS_ON Workspaces at the end of the month.
        if self.settings.get('testEndOfMonth'):
            log.debug('testEndOfMonth {} == True'.format(self.settings.get('testEndOfMonth')))

            # If billable time is under the threshold for this bundle type
            if billable_time <= hourly_threshold:
                log.debug('billableTime {} < hourlyThreshold {}'.format(billable_time, hourly_threshold))

                # Change the workspace to AUTO_STOP
                result_code = self.modify_workspace_properties(workspace_id, AUTO_STOP)
                # if there was an exception in the modify workspace API call, new mode is same as old mode
                if result_code == '-E-':
                    new_mode = ALWAYS_ON
                else:
                    new_mode = AUTO_STOP

            # Otherwise, report no change for the Workspace
            else:  # billable_time > hourly_threshold:
                log.debug('billableTime {} >= hourlyThreshold {}'.format(billable_time, hourly_threshold))
                result_code = '-N-'
                new_mode = ALWAYS_ON
        else:
            log.debug('testEndOfMonth {} == False'.format(self.settings.get('testEndOfMonth')))
            result_code = '-N-'
            new_mode = ALWAYS_ON

        return result_code, new_mode

    def append_entry(self, old_csv, result):
        s = ','
        csv = old_csv + s.join((
            result['workspaceID'],
            str(result['billableTime']),
            str(result['hourlyThreshold']),
            result['optimizationResult'],
            result['bundleType'],
            result['initialMode'],
            result['newMode'],
            result['userName'],
            result['computerName'],
            result['directoryId'],
            result['workspaceTerminated'],
            ''.join(('"', str(result['tags']), '"')) + '\n'  # Adding quotes to the string to help with csv format
        ))

        return csv

    def expand_csv(self, raw_csv):
        csv = raw_csv.replace(',-M-', ',ToMonthly').replace(',-H-', ',ToHourly'). \
            replace(',-E-', ',Failed to change the mode').replace(',-N-', ',No Change').replace(',-S-', ',Skipped')
        return csv
