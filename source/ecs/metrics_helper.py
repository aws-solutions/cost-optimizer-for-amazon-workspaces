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

# This file reads the AWS cloudwatch metrics for a given workspace
# This is where we will change the algorithm to determine billing preference

import boto3
import logging
import os
import math
from botocore.config import Config
from datetime import timedelta, datetime
from itertools import groupby

botoConfig = Config(
    max_pool_connections=100,
    retries={
        'max_attempts': 20,
        'mode': 'standard'
    },
)

log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)

AUTO_STOP = 'AUTO_STOP'
ALWAYS_ON = 'ALWAYS_ON'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
NUMBER_OF_DAYS = 5
START_TIME = 'start_time'
END_TIME = 'end_time'
AUTO_STOP_TIMEOUT_HOURS = os.getenv('AutoStopTimeoutHours')


class MetricsHelper(object):

    def __init__(self, region):
        self.region = region
        self.client = boto3.client('cloudwatch', region_name=self.region, config=botoConfig)

    def get_billable_hours(self, start_time, end_time, workspace):
        """
        This method returns the billable hours for the given workspace
        :param start_time: Start time for the calculating hours
        :param end_time: End time for calculating hours
        :param workspace: Workspace object to use to calculate hours
        :return: billable hours for the workspace
        """
        log.debug("Calculating user connected hours for the workspace {} with start time {} and end time {}".
                  format(workspace, start_time, end_time))
        list_time_ranges = self.get_list_time_ranges(start_time, end_time)
        list_metric_data_points_user_connected = \
            self.get_cloudwatch_metric_data_points(workspace['WorkspaceId'], list_time_ranges, 'UserConnected')
        list_user_sessions_user_connected = self.get_list_user_session_data_points(
            list_metric_data_points_user_connected)
        user_connected_hours = self.get_user_connected_hours(list_user_sessions_user_connected, workspace)
        log.debug("Calculated user connected hours: {}".format(user_connected_hours))
        return user_connected_hours

    def get_list_time_ranges(self, start_time, end_time):
        """
        This method returns list of time ranges for the given start and end time. Each time range if of 5 days.
        :param start_time:
        :param end_time:
        :return: list of time ranges
        """
        log.debug("Getting time ranges for start time {} and end time {}".format(start_time, end_time))
        list_time_ranges = []
        start_time_new_format = datetime.strptime(start_time, TIME_FORMAT)
        end_time_new_format = datetime.strptime(end_time, TIME_FORMAT)
        time_diff = end_time_new_format - start_time_new_format
        number_of_time_ranges = math.ceil(
            time_diff / timedelta(days=NUMBER_OF_DAYS))  # Round the number to the next integer

        for item in range(number_of_time_ranges):
            start_time = start_time_new_format + item * timedelta(days=NUMBER_OF_DAYS)
            end_time = start_time + timedelta(days=NUMBER_OF_DAYS)
            time_range = {
                START_TIME: start_time.strftime(TIME_FORMAT),
                END_TIME: end_time.strftime(TIME_FORMAT)
            }
            list_time_ranges.append(time_range)
        log.debug("List of time ranges for start time {} and end time {} is {}".
                  format(start_time, end_time, list_time_ranges))
        return list_time_ranges

    def get_cloudwatch_metric_data_points(self, workspace_id, list_time_ranges, metric):
        """
        This method returns the cloudwatch metric datapoints for given workspace id and time ranges.
        :param metric: metric to use to query cloudwatch metrics
        :param workspace_id:
        :param list_time_ranges: List of time ranges to query and get the metrics for
        :return: list of Datapoints for the cloudwatch metrics
        """
        log.debug("Getting the cloudwatch metrics for the workspace id {}".format(workspace_id))
        list_data_points = []
        for time_range in list_time_ranges:
            try:
                metrics = self.client.get_metric_statistics(
                    Dimensions=[{
                        'Name': 'WorkspaceId',
                        'Value': workspace_id
                    }],
                    Namespace='AWS/WorkSpaces',
                    MetricName=metric,
                    StartTime=time_range[START_TIME],
                    EndTime=time_range[END_TIME],
                    Period=300,
                    Statistics=['Maximum']
                )
            except Exception as error:
                log.error(error)
                raise
            for metric_data in metrics['Datapoints']:
                list_data_points.append(metric_data)
        log.debug("The cloudwatch metrics list for workspace id {} is {}".format(workspace_id, list_data_points))
        return list_data_points

    def get_list_user_session_data_points(self, list_metric_data_points):
        """
        This method returns the list of data points per user session.
        :param list_metric_data_points:
        :return: list of data points per user session
        """
        log.debug("Getting the list of user session data points for metric data points {}".
                  format(list_metric_data_points))
        list_data_points = []
        sorted_list_metric_data_points = sorted(list_metric_data_points, key=lambda x: x['Timestamp'])
        for metric in sorted_list_metric_data_points:
            list_data_points.append(metric['Maximum'])
        # Use groupby to find continuous patterns of data point 1.0
        list_user_sessions = [list(g) for k, g in groupby(list_data_points) if k == 1.0]
        log.debug("List of user sessions is {}".format(list_user_sessions))
        return list_user_sessions

    def get_user_connected_hours(self, list_user_sessions, workspace):
        """
        This method returns user connected hours from list of user sessions for a given workspace
        :param list_user_sessions:
        :param workspace:
        :return:
        """
        log.debug("Calculating user connected hours for workspace {} and user sessions {}".
                  format(workspace, list_user_sessions))
        user_connected_hours = 0
        if workspace['WorkspaceProperties']['RunningMode'] == ALWAYS_ON:
            idle_time_in_hours = int(AUTO_STOP_TIMEOUT_HOURS)
        else:
            idle_time_in_hours = workspace['WorkspaceProperties']['RunningModeAutoStopTimeoutInMinutes'] / 60

        for session in list_user_sessions:
            # Divide each session by 12 to convert the 5 min intervals to hour and idle time per session
            user_connected_hours = user_connected_hours + math.ceil(len(session) / 12) + idle_time_in_hours
        return user_connected_hours
