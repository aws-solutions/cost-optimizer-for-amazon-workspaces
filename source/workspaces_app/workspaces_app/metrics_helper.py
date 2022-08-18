#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import boto3
import botocore
import logging
from datetime import timedelta, datetime
import os
import math
import typing

log = logging.getLogger(__name__)

ALWAYS_ON = 'ALWAYS_ON'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
NUMBER_OF_DAYS = 5
START_TIME = 'start_time'
END_TIME = 'end_time'


def get_autostop_timeout_hours() -> int:
    env_var_name = 'AutoStopTimeoutHours'
    autostop_timeout_hours = os.getenv(env_var_name)
    try:
        return int(autostop_timeout_hours)
    except (TypeError, ValueError):
        log.error(f'Expected integer environment variable "{env_var_name}"')
        raise


class MetricsHelper():
    def __init__(self, session: boto3.session.Session, region: str) -> None:
        self.region = region
        boto_config = botocore.config.Config(
            max_pool_connections=100,
            retries={
                'max_attempts': 20,
                'mode': 'standard'
            },
        )
        self.client = session.client('cloudwatch', region_name=self.region, config=boto_config)

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
        if list_metric_data_points_user_connected:
            list_user_session_data_points = self.get_list_user_session_data_points(list_metric_data_points_user_connected)
            list_user_sessions = self.get_user_sessions(list_user_session_data_points, workspace)
            user_connected_hours = self.get_user_connected_hours(list_user_sessions, workspace)
            log.debug("Calculated user connected hours: {}".format(user_connected_hours))
            return user_connected_hours
        else:
            return None

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
                log.error("Error occurred while processing workspace {}, {}".format(workspace_id, error))
                return None
            for metric_data in metrics['Datapoints']:
                list_data_points.append(metric_data)
        log.debug("The cloudwatch metrics list for workspace id {} is {}".format(workspace_id, list_data_points))
        return list_data_points

    def get_list_user_session_data_points(self, list_metric_data_points):
        """
        This method returns the sorted list of data points
        :param list_metric_data_points:
        :return: sorted list of data points
        """
        log.debug("Getting the list of user session data points for metric data points {}".
                  format(list_metric_data_points))
        list_user_session_data_points = []
        sorted_list_metric_data_points = sorted(list_metric_data_points, key=lambda x: x['Timestamp'])
        for metric in sorted_list_metric_data_points:
            list_user_session_data_points.append(metric['Maximum'])
        log.debug("List of user sessions is {}".format(list_user_session_data_points))
        return list_user_session_data_points

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
            idle_time_in_hours = get_autostop_timeout_hours()
        else:
            idle_time_in_hours = workspace['WorkspaceProperties']['RunningModeAutoStopTimeoutInMinutes'] / 60

        for session in list_user_sessions:
            user_connected_hours = user_connected_hours + session + idle_time_in_hours  ## ADD PATCHING HOURS TO WORKSPACES
        return user_connected_hours

    def get_user_sessions(self, list_user_session_data_points, workspace):
        """
        This method returns user session hours from list of user sessions for a given workspace
        :param list_user_session_data_points:
        :param workspace:
        :return:
        """
        list_user_sessions = []
        session_start = False
        zeroes_count = 0
        end_session_index = 0
        start_session_index = 0

        for i in range(len(list_user_session_data_points)):
            if list_user_session_data_points[i] == 1:
                if not session_start:
                    session_start = True
                    zeroes_count = 0
                    start_session_index = i
                    end_session_index = i + 1  # set this to account for user session [1,0,0....0]
                else:
                    zeroes_count = 0  # Reset the zero count if a value of 1 is encountered
                    end_session_index = i + 1
            elif list_user_session_data_points[i] == 0 and session_start:
                zeroes_count = zeroes_count + 1
                if zeroes_count == self.get_zero_count(workspace):
                    user_session_hours = math.ceil((end_session_index - start_session_index) / 12)
                    list_user_sessions.append(user_session_hours)
                    session_start = False
                    end_session_index = 0
                    start_session_index = 0
        user_session_hours = math.ceil((end_session_index - start_session_index) / 12)
        if user_session_hours:
            list_user_sessions.append(user_session_hours)
        return list_user_sessions

    def get_zero_count(self, workspace):
        """
        This method returns the number of continuous zeroes which will indicate end of user session based on the
        property RunningModeAutoStopTimeoutInMinutes
        :param workspace:
        :return: the number of continuous zeros in user session to determine end of user session
        """
        if workspace['WorkspaceProperties']['RunningMode'] == ALWAYS_ON:
            # This constant represents the number of 5 minutes sessions in AUTO_STOP_TIMEOUT_HOURS
            number_zero_count = get_autostop_timeout_hours() * 60 / 5
        else:
            number_zero_count = workspace['WorkspaceProperties']['RunningModeAutoStopTimeoutInMinutes'] / 5
        log.debug("The zero count for the workspace {} is {}".format(workspace, number_zero_count))
        return int(number_zero_count)
