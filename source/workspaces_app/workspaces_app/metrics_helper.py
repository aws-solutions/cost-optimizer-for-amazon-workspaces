#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import bisect
import math
import os
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from statistics import mean

# AWS Libraries
import boto3
import botocore
from aws_lambda_powertools import Logger

# Cost Optimizer for Amazon Workspaces
from .user_session import UserSession
from .utils.user_session_dao import UserSessionDAO
from .workspace_record import (
    WeightedAverage,
    WorkspaceDescription,
    WorkspacePerformanceMetrics,
    WorkspaceRecord,
)

# Initialize logger
logger = Logger(service="metrics_helper")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)

ALWAYS_ON = "ALWAYS_ON"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
START_TIME = "start_time"
END_TIME = "end_time"
METRIC_LIST = [
    "UserConnected",
    "InSessionLatency",
    "CPUUsage",
    "MemoryUsage",
    "RootVolumeDiskUsage",
    "UserVolumeDiskUsage",
    "UDPPacketLossRate",
]


def get_autostop_timeout_hours() -> int:
    env_var_name = "AutoStopTimeoutHours"
    autostop_timeout_hours = os.getenv(env_var_name)
    try:
        return int(autostop_timeout_hours)
    except (TypeError, ValueError):
        logger.error(f'Expected integer environment variable "{env_var_name}"')
        raise


class MetricsHelper:
    def __init__(
        self, session: boto3.session.Session, region: str, session_table
    ) -> None:
        self.region = region
        boto_config = botocore.config.Config(
            max_pool_connections=100,
            retries={"max_attempts": 20, "mode": "standard"},
        )
        self.client = session.client(
            "cloudwatch", region_name=self.region, config=boto_config
        )
        # use default boto session instead of the passed in assumed role session
        self.session_table = UserSessionDAO(
            boto3.session.Session(), session_table, region
        )

    def get_billable_hours_and_performance(
        self,
        start_of_month: str,
        current_time: str,
        ws_record: WorkspaceRecord | WorkspaceDescription,
        autostop_timeout_minutes: int,
    ) -> dict[str, int | WorkspacePerformanceMetrics] | None:
        """
        This method returns the billable hours and performance metrics for the given workspace
        :param start_time: Start time for the calculating hours
        :param end_time: End time for calculating hours
        :param ws_record: The record of workspace usage for the month from the db or description if
        the db record doesn't exist
        :param autostop_timeout_minutes: The autostop timeout for the given workspace
        :return: billable hours and performance metircs for the workspace
        """
        ws_description = (
            ws_record.description
            if isinstance(ws_record, WorkspaceRecord)
            else ws_record
        )
        logger.debug(
            "Calculating user connected hours for the workspace {} with start time {} and end time {}".format(
                ws_description.workspace_id, start_of_month, current_time
            )
        )
        last_reported_time = getattr(ws_record, "last_reported_metric_period", None)
        time_range = self.get_time_range(
            start_of_month, current_time, last_reported_time
        )
        list_metric_data_points = self.get_cloudwatch_metric_data_points(
            ws_description.workspace_id, time_range
        )
        if list_metric_data_points:
            metric_data_points = self.get_list_data_points(list_metric_data_points)
            user_sessions = self.get_user_sessions(
                metric_data_points,
                ws_description,
                ws_description.initial_mode,
                autostop_timeout_minutes,
            )
            if user_sessions:
                self.session_table.update_ddb_items(user_sessions)
            billable_hours = self.get_user_connected_hours(
                user_sessions,
                ws_description.workspace_id,
                ws_description.initial_mode,
                autostop_timeout_minutes,
                getattr(ws_record, "billable_hours", None),
            )
            performance_metrics = self.process_performance_metrics(
                metric_data_points, getattr(ws_record, "performance_metrics", None)
            )
            logger.debug("Calculated user connected hours: {}".format(billable_hours))

            return {
                "billable_hours": billable_hours,
                "performance_metrics": performance_metrics,
            }
        else:
            return None

    def get_time_range(
        self, start_of_month: str, end_time: str, last_reported_time: str
    ) -> dict:
        """
        This method determines the time range to be used for the get_metric_data query. It uses
        the last report time as the start, if that last report time isn't available it uses
        the first of the month.
        :param start_of_month: Date string for the beginning of the month
        :param end_time: Date string to be used for the end of the time range
        :param last_reported_time: The time when the data for the workspace was last analyzed
        :return: dictionary containing time range
        """
        start_time = last_reported_time or start_of_month
        time_range_start = datetime.strptime(start_time, TIME_FORMAT)
        time_range_end = datetime.strptime(end_time, TIME_FORMAT)
        time_range = {
            START_TIME: time_range_start.strftime(TIME_FORMAT),
            END_TIME: time_range_end.strftime(TIME_FORMAT),
        }
        logger.debug(
            "the start time and end time for the get_metric_data query is {}".format(
                time_range
            )
        )
        return time_range

    def build_query(self, metric: str, workspace_id: str) -> dict:
        """
        This method creates a query for a metric to be used with get_metric_data
        :param metric: The name of the metric to request
        :param workspace_id: The workspace for which to get metrics
        :return: A query to be used with get_metric_data
        """
        stat = "Maximum" if metric == "UserConnected" else "Average"
        return {
            "Id": metric.lower(),
            "MetricStat": {
                "Metric": {
                    "Dimensions": [{"Name": "WorkspaceId", "Value": workspace_id}],
                    "Namespace": "AWS/WorkSpaces",
                    "MetricName": metric,
                },
                "Period": 300,
                "Stat": stat,
            },
        }

    def get_cloudwatch_metric_data_points(
        self, workspace_id: str, time_range: list[str]
    ):
        """
        This method returns the cloudwatch metric datapoints for given workspace id and time ranges.
        :param metric: metric to use to query cloudwatch metrics
        :param workspace_id:
        :param time_range: List of time ranges to query and get the metrics for
        :return: list of Datapoints for the cloudwatch metrics
        """
        logger.debug(
            "Getting the cloudwatch metrics for the workspace id {}".format(
                workspace_id
            )
        )
        list_data_points = []
        metric_queries = [
            self.build_query(metric, workspace_id) for metric in METRIC_LIST
        ]
        try:
            metrics_paginator = self.client.get_paginator("get_metric_data")
            metrics_iterator = metrics_paginator.paginate(
                MetricDataQueries=metric_queries,
                StartTime=time_range[START_TIME],
                EndTime=time_range[END_TIME],
                ScanBy="TimestampAscending",
                PaginationConfig={"PageSize": 100800},
            )
            for page in metrics_iterator:
                list_data_points.extend(page.get("MetricDataResults"))
        except Exception as error:
            logger.exception(
                "Error occurred while processing workspace {}, {}".format(
                    workspace_id, error
                )
            )
            return None
        logger.debug(
            "The cloudwatch metrics list for workspace id {} is {}".format(
                workspace_id, list_data_points
            )
        )
        return list_data_points

    def get_list_data_points(self, list_metric_data_points):
        """
        This method returns the sorted list of data points
        :param list_metric_data_points: a list of MetricDataResults from a get_metric_data query
        :return: sorted list of data points
        """
        logger.debug(
            "Getting the list of user session data points for metric data points {}".format(
                list_metric_data_points
            )
        )
        metric_data_points = {}
        for data_point in list_metric_data_points:
            metric_id = data_point.get("Id")
            metric_data_points.setdefault(metric_id, defaultdict(list))
            metric_data_points[metric_id]["timestamps"].extend(data_point["Timestamps"])
            metric_data_points[metric_id]["values"].extend(data_point["Values"])
            metric_data_points[metric_id] = dict(metric_data_points[metric_id])
        return metric_data_points

    def get_user_connected_hours(
        self,
        list_user_sessions: list[UserSession],
        ws_id: str,
        ws_running_mode: str,
        autostop_timeout_minutes: int,
        previous_billable_hours: int | None,
    ) -> int:
        """
        This method returns user connected hours from list of user sessions for a given workspace
        :param list_user_sessions: a list of user session data points
        :param ws_id: The workspace id
        :param ws_running_mode: The initial running mode of the workspace
        :param autostop_timeout_minutes: The auto-stop timeout for the workspace
        :param previous_billable_hours: The previously calculated billable hours for the workspace
        :return: The number of hours a user was connected
        """
        logger.debug(
            "Calculating user connected hours for workspace {} and user sessions {}".format(
                ws_id, list_user_sessions
            )
        )
        user_connected_hours = 0
        if ws_running_mode == ALWAYS_ON:
            idle_time_in_hours = get_autostop_timeout_hours()
        else:
            idle_time_in_hours = autostop_timeout_minutes / 60

        for session in list_user_sessions:
            user_connected_hours = (
                user_connected_hours + session.duration_hours + idle_time_in_hours
            )  ## ADD PATCHING HOURS TO WORKSPACES

        user_connected_hours = user_connected_hours + (previous_billable_hours or 0)
        return int(user_connected_hours)

    def get_user_sessions(
        self,
        metric_data: dict[str, list[datetime] | list[float]],
        ws_description: WorkspaceDescription,
        ws_running_mode: str,
        autostop_timeout_minutes: int,
    ) -> list[UserSession]:
        """
        This method returns user session hours from list of user sessions for a given workspace
        :param list_user_session_data_points: a list of user session data values
        :param ws_id: The id of the workspace
        :param ws_running_mode: The initial running mode of the workspace
        :param autostop_timeout_minutes: The autostop timeout in minutes for the workspace
        :return: Returns a list of user sessions
        """
        user_sessions = []
        active_sessions = []
        session_metrics = {}
        list_user_sessions = metric_data.pop("userconnected")
        list_user_session_timestamps = list_user_sessions.get("timestamps")
        list_user_session_data_points = list_user_sessions.get("values")
        session_start = False
        zeroes_count = 0
        end_session_index = 0
        start_session_index = 0
        workspace_zero_count = self.get_zero_count(
            ws_description.workspace_id, ws_running_mode, autostop_timeout_minutes
        )
        ws_session_description = {
            "workspace_id": ws_description.workspace_id,
            "directory_id": ws_description.directory_id,
            "region": ws_description.region,
            "account": ws_description.account,
            "username": ws_description.username,
        }
        for i in range(len(list_user_session_data_points)):
            if list_user_session_data_points[i] == 1:
                if not session_start:
                    session_start = True
                    zeroes_count = 0
                    session_metrics = {}
                    start_session_index = i
                    end_session_index = (
                        i + 1
                    )  # set this to account for user session [1,0,0....0]
                    active_sessions = [list_user_session_timestamps[i]]
                    session_metrics = {
                        **session_metrics,
                        **self.get_performance_for_period(
                            metric_data,
                            session_metrics,
                            list_user_session_timestamps[i],
                        ),
                    }
                else:
                    zeroes_count = (
                        0  # Reset the zero count if a value of 1 is encountered
                    )
                    end_session_index = i + 1
                    active_sessions.append(list_user_session_timestamps[i])
                    session_metrics = {
                        **session_metrics,
                        **self.get_performance_for_period(
                            metric_data,
                            session_metrics,
                            list_user_session_timestamps[i],
                        ),
                    }
            elif list_user_session_data_points[i] == 0 and session_start:
                zeroes_count = zeroes_count + 1
                if zeroes_count == workspace_zero_count:
                    user_session_hours = math.ceil(
                        (end_session_index - start_session_index) / 12
                    )
                    user_sessions.append(
                        UserSession.from_json(
                            {
                                **ws_session_description,
                                "active_sessions": active_sessions,
                                "duration_hours": user_session_hours,
                                **{
                                    UserSession.ddb_attr_to_class_field(
                                        metric
                                    ): Decimal(round(metric_wa.avg, 2))
                                    for metric, metric_wa in session_metrics.items()
                                },
                            }
                        )
                    )
                    session_start = False
                    end_session_index = 0
                    start_session_index = 0
        user_session_hours = math.ceil((end_session_index - start_session_index) / 12)
        if user_session_hours:
            user_sessions.append(
                UserSession.from_json(
                    {
                        **ws_session_description,
                        "active_sessions": active_sessions,
                        "duration_hours": int(user_session_hours),
                        **{
                            UserSession.ddb_attr_to_class_field(metric): Decimal(
                                round(metric_wa.avg, 2)
                            )
                            for metric, metric_wa in session_metrics.items()
                        },
                    }
                )
            )
        return user_sessions

    def get_zero_count(
        self, ws_id: str, running_mode: str, autostop_timeout_minutes: int
    ):
        """
        This method returns the number of continuous zeroes which will indicate end of user session based on the
        property RunningModeAutoStopTimeoutInMinutes
        :param workspace:
        :return: the number of continuous zeros in user session to determine end of user session
        """
        if running_mode == ALWAYS_ON:
            # This constant represents the number of 5 minutes sessions in AUTO_STOP_TIMEOUT_HOURS
            number_zero_count = get_autostop_timeout_hours() * 60 / 5
        else:
            number_zero_count = autostop_timeout_minutes / 5
        logger.debug(
            "The zero count for the workspace {} is {}".format(ws_id, number_zero_count)
        )
        return int(number_zero_count)

    def metric_id_to_name(self, metric_id: str) -> str | None:
        """
        This method converts a metric id to its corresponding
        metric name
        :param metric_id: the metric id which corresponds to a
        metric from get_metric_data_results
        :return: The metric name to which a metric id corresponds
        """
        for metric in METRIC_LIST:
            if metric_id == metric.lower():
                return metric
        return None

    def get_performance_for_period(
        self,
        data: dict[str, list[datetime] | list[float]],
        session_metrics: dict[str, WeightedAverage],
        time: datetime,
    ):
        """
        This method gets the performance metrics at a specified time
        :param data: the list of data from get_metric_data
        :param session_metrics: a list of metrics for a given session
        :param time: the time for which to get the corresponding metric
        :return: the metrics for the given time
        """
        new_session_metrics = {}
        for metric_id, data in data.items():
            metric = self.metric_id_to_name(metric_id)
            metric_running_average = session_metrics.get(metric)
            idx = bisect.bisect_left(data["timestamps"], time)
            if data.get("timestamps") and data["timestamps"][idx] == time:
                average_at_time = Decimal(str(data["values"][idx]))
                average_at_time = WeightedAverage(average_at_time, 1)

                if metric_running_average:
                    new_session_metrics[metric] = metric_running_average.merge(
                        average_at_time
                    )
                else:
                    new_session_metrics[metric] = average_at_time
        return new_session_metrics

    def process_performance_metrics(
        self,
        metric_data_points: dict[str, dict[str, list]],
        prev_metrics: WorkspacePerformanceMetrics | None,
    ) -> WorkspacePerformanceMetrics:
        """
        This method calculates the averages of the metric data points for each metric.
        :param metric_data_points: a dictionary of metric data points containing a list of
        timestamps and values for each.
        :param prev_metrics: a PerformanceMetrics instance with previously analyzed
        performance metric results
        """
        performance_metrics = {}
        for metric_id, data_list in metric_data_points.items():
            metric_name = self.metric_id_to_name(metric_id)
            data_values = data_list["values"]
            ws_record_field = WorkspaceRecord.ddb_attr_to_class_field(metric_name)
            if WorkspacePerformanceMetrics.is_performance_metric(ws_record_field):
                current_count = len(data_values)
                current_avg = (
                    Decimal(str(mean(data_values))) if current_count > 0 else None
                )
                current_metric = WeightedAverage(avg=current_avg, count=current_count)
                prev_metric = getattr(prev_metrics, ws_record_field, None)
                if prev_metric:
                    performance_metrics |= {
                        ws_record_field: prev_metric.merge(current_metric)
                    }
                else:
                    performance_metrics |= {ws_record_field: current_metric}

        return WorkspacePerformanceMetrics(**performance_metrics)
