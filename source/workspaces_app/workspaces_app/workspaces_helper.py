#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
import time
import typing

# AWS Libraries
import boto3
import botocore
from aws_lambda_powertools import Logger

# Cost Optimizer for Amazon Workspaces
from . import metrics_helper
from .utils import workspace_utils
from .utils.dashboard_metrics import DashboardMetrics
from .workspace_record import (
    WorkspaceBillingData,
    WorkspaceDescription,
    WorkspaceRecord,
)

# Initialize logger
logger = Logger(service="workspaces_helper")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)

botoConfig = botocore.config.Config(
    max_pool_connections=100,
    retries={"max_attempts": 20, "mode": "standard"},
    user_agent_extra=os.getenv("UserAgentString"),
)

ALWAYS_ON = "ALWAYS_ON"
AUTO_STOP = "AUTO_STOP"


class WorkspacesHelper(object):
    def __init__(self, session: boto3.session.Session, settings: dict) -> None:
        self.settings = settings
        self._session = session
        self.metrics_helper = metrics_helper.MetricsHelper(
            session, self.settings.get("region"), settings.get("userSessionTable")
        )
        self.workspaces_client = session.client(
            "workspaces", region_name=self.settings.get("region"), config=botoConfig
        )
        self.cloudwatch_client = session.client(
            "cloudwatch", region_name=self.settings.get("region"), config=botoConfig
        )

    def process_workspace(
        self,
        ws_record: WorkspaceRecord | WorkspaceDescription,
        autostop_timeout_minutes: int | None,
        dashboard_metrics: DashboardMetrics,
    ) -> WorkspaceRecord:
        """
        This method processes the given workspace and returns a workspace record instance
        :param workspace: a preliminary workspace record instance
        :return: A workspace record instance filled out with the most current data.
        """
        description = (
            ws_record
            if isinstance(ws_record, WorkspaceDescription)
            else ws_record.description
        )
        workspace_id = description.workspace_id
        logger.debug(f"workspaceID: {workspace_id}")
        workspace_running_mode = description.initial_mode
        logger.debug(f"workspaceRunningMode: {workspace_running_mode}")
        workspace_bundle_type = description.bundle_type
        workspace_hourly_threshold = description.usage_threshold

        logger.debug(f"workspaceBundleType: {workspace_bundle_type}")
        last_known_user_connection = None
        calculated_metrics = self.metrics_helper.get_billable_hours_and_performance(
            self.settings.get("dateTimeValues").get("start_time_for_current_month"),
            self.settings.get("dateTimeValues").get("end_time_for_current_month"),
            ws_record,
            autostop_timeout_minutes,
        )
        billable_hours = calculated_metrics.get("billable_hours")
        performance_metrics = calculated_metrics.get("performance_metrics")
        tags = self.get_list_tags_for_workspace(workspace_id)
        if workspace_utils.check_for_skip_tag(tags):
            logger.info(f"Skipping WorkSpace {workspace_id} due to Skip_Convert tag")
            workspace_terminated = ""
            optimization_result = {
                "resultCode": "-S-",
                "newMode": workspace_running_mode,
            }
        else:
            (
                workspace_terminated,
                last_known_user_connection,
            ) = self.get_termination_status(workspace_id, billable_hours, tags)
            optimization_result = self.compare_usage_metrics(
                workspace_id,
                billable_hours,
                workspace_hourly_threshold,
                workspace_running_mode,
            )

        # Update metrics based on the optimization result
        if optimization_result["resultCode"] == "-M-":
            dashboard_metrics.update_conversion_metrics("hourly_to_monthly")
        elif optimization_result["resultCode"] == "-H-":
            dashboard_metrics.update_conversion_metrics("monthly_to_hourly")
        elif optimization_result["resultCode"] == "-E-":
            dashboard_metrics.update_conversion_metrics("conversion_errors")
        elif optimization_result["resultCode"] == "-S-":
            dashboard_metrics.update_conversion_metrics("conversion_skips")

        if workspace_terminated:
            dashboard_metrics.update_termination_metrics()

        if optimization_result["newMode"] == "AUTO_STOP":
            dashboard_metrics.update_billing_metrics("hourly_billed")
        elif optimization_result["newMode"] == "ALWAYS_ON":
            dashboard_metrics.update_billing_metrics("monthly_billed")

        billing_data = WorkspaceBillingData(
            billable_hours=billable_hours,
            change_reported=optimization_result["resultCode"],
            new_mode=optimization_result["newMode"],
            workspace_terminated=workspace_terminated,
        )
        return WorkspaceRecord(
            description=description,
            billing_data=billing_data,
            performance_metrics=performance_metrics,
            report_date=self.settings.get("dateTimeValues").get("date_today"),
            last_reported_metric_period=self.settings.get("dateTimeValues").get(
                "end_time_for_current_month"
            ),
            last_known_user_connection=last_known_user_connection,
        )

    def get_hourly_threshold_for_bundle_type(self, bundle_type):
        if bundle_type in self.settings.get("hourlyLimits"):
            return int(self.settings.get("hourlyLimits")[bundle_type])
        else:
            return None

    def get_list_tags_for_workspace(self, workspace_id):
        try:
            workspace_tags = self.workspaces_client.describe_tags(
                ResourceId=workspace_id
            )
            logger.debug(workspace_tags)
            tags = workspace_tags.get("TagList", [])
        except botocore.exceptions.ClientError as error:
            logger.exception(
                f"Error {error} while getting tags for the workspace {workspace_id}"
            )
            return None
        return tags

    def modify_workspace_properties(self, workspace_id, new_running_mode):
        """
        This method changes the running mode of the workspace to the give new running mode
        :param workspace_id:
        :param new_running_mode:
        :return: Result code to indicate new running mode for the workspace
        """
        logger.debug("modifyWorkspaceProperties")
        if not self.settings.get("isDryRun"):
            try:
                self.workspaces_client.modify_workspace_properties(
                    WorkspaceId=workspace_id,
                    WorkspaceProperties={"RunningMode": new_running_mode},
                )
            except Exception as e:
                logger.exception(
                    f"Exceeded retries for {workspace_id} due to error: {e}"
                )
                return "-E-"  # return the status to indicate that the workspace was not processed.
        else:
            logger.info(
                f"Skipping modifyWorkspaceProperties for Workspace {workspace_id} due to dry run"
            )

        if new_running_mode == ALWAYS_ON:
            result = "-M-"
        else:
            result = "-H-"
        return result

    def get_workspaces_for_directory(self, directory_id: str) -> typing.List[dict]:
        """
        :param: directory_id
        :return: List of workspaces for a given directory.
        This method returns the list of AWS workspaces in the given directory.
        """
        logger.debug(f"Getting the workspace  for the directory {directory_id}")
        list_workspaces = []
        try:
            response = self.workspaces_client.describe_workspaces(
                DirectoryId=directory_id
            )
            list_workspaces = response.get("Workspaces", [])
            next_token = response.get("NextToken", None)
            while next_token is not None:
                response = self.workspaces_client.describe_workspaces(
                    DirectoryId=directory_id, NextToken=next_token
                )
                list_workspaces.extend(response.get("Workspaces", []))
                next_token = response.get("NextToken", None)
        except botocore.exceptions.ClientError as e:
            logger.exception(
                f"Error while getting the list of workspace for directory ID "
                f"{directory_id}: Error: {e}"
            )
        logger.debug(f"Returning the list of workspaces as {list_workspaces}")
        return list_workspaces

    def get_termination_status(self, workspace_id, billable_time, tags):
        """
        This method returns whether the workspace needs to be terminated
        :param workspace_id:
        :param billable_time:
        :param tags:
        :return: 'Yes' if the workspace is terminated and '' if not.
        """
        # Set value to empty string which will be the default value for the terminated column in the report
        workspace_terminated = ""
        last_known_user_connection_timestamp = None
        logger.debug(
            f"Getting the termination status for workspace: "
            f"{workspace_id}, billable time: {billable_time} and tags {tags}"
        )
        logger.debug(
            f"The value for last month check is {self.settings.get('dateTimeValues').get('current_month_last_day')}"
        )
        try:
            last_known_user_connection_timestamp = (
                self.get_last_known_user_connection_timestamp(workspace_id)
            )
            if workspace_utils.is_terminate_workspace_enabled() and (
                self.settings.get("dateTimeValues").get("current_month_last_day")
                or (self.settings.get("testEndOfMonth"))
            ):
                logger.debug(
                    f"The value for current_month_last_day is {self.settings.get('dateTimeValues').get('current_month_last_day')}"
                )
                logger.debug(
                    f"The value for testEndOfMonth is {(self.settings.get('testEndOfMonth'))}"
                )
                logger.debug(f"Processing further for workspace id {workspace_id}")
                logger.debug(
                    f"Last known user connection time stamp is {last_known_user_connection_timestamp}"
                )
                workspace_available_on_first_day_of_selected_month = (
                    self.check_if_workspace_available_on_first_day_selected_month(
                        workspace_id
                    )
                )
                logger.debug(
                    (
                        f"The value for workspace available on first day of selected period is "
                        f"{workspace_available_on_first_day_of_selected_month}"
                    )
                )
                workspace_used_in_selected_period = (
                    workspace_utils.check_if_workspace_used_for_selected_period(
                        last_known_user_connection_timestamp,
                        self.settings.get("dateTimeValues").get(
                            "first_day_selected_month"
                        ),
                    )
                )
                logger.debug(
                    f"The value for workspace used in selected period is {workspace_used_in_selected_period}"
                )
                if (
                    workspace_available_on_first_day_of_selected_month
                    and not workspace_used_in_selected_period
                ):
                    workspace_terminated = (
                        self.check_if_workspace_needs_to_be_terminated(workspace_id)
                    )
        except Exception as error:
            logger.exception(
                f"Error {error} while checking the workspace termination status for workspace : {workspace_id}"
            )
        logger.debug(f"Returning the termination status as {workspace_terminated}")
        if (
            last_known_user_connection_timestamp is not None
            and last_known_user_connection_timestamp != "ResourceUnavailable"
        ):
            last_known_user_connection_timestamp = time.strftime(
                "%Y-%m-%d", last_known_user_connection_timestamp.timetuple()
            )
        return workspace_terminated, last_known_user_connection_timestamp

    def get_last_known_user_connection_timestamp(self, workspace_id):
        """
        This method return the LastKnownUserConnectionTimestamp for the given workspace_id
        :param: ID for the given workspace
        :return: LastKnownUserConnectionTimestamp for the workspace
        """
        logger.debug(
            f"Getting the last known user connection timestamp for the workspace_id {workspace_id}"
        )
        try:
            response = self.workspaces_client.describe_workspaces_connection_status(
                WorkspaceIds=[workspace_id]
            )
            last_known_timestamp = response["WorkspacesConnectionStatus"][0].get(
                "LastKnownUserConnectionTimestamp"
            )
        except Exception as error:
            logger.exception(
                f"Setting the value for last_known_timestamp to ResourceUnavailable due to the error {error}"
            )
            last_known_timestamp = "ResourceUnavailable"
        logger.debug(f"Returning the last known timestamp as {last_known_timestamp}")
        return last_known_timestamp

    def check_if_workspace_available_on_first_day_selected_month(self, workspace_id):
        """
        This method checks if the workspace was available on the give date
        :param workspace_id: Workspace ID for the workspace
        """
        workspace_available = False
        star_time_selected_date = self.settings.get("dateTimeValues").get(
            "start_time_selected_date"
        )
        end_time_selected_date = self.settings.get("dateTimeValues").get(
            "end_time_selected_date"
        )
        logger.debug(
            f"Checking if the workspace {workspace_id} was available between first day {star_time_selected_date}"
            f" and second day {end_time_selected_date}"
        )
        try:
            metrics = self.cloudwatch_client.get_metric_statistics(
                Dimensions=[{"Name": "WorkspaceId", "Value": workspace_id}],
                Namespace="AWS/WorkSpaces",
                MetricName="Available",
                StartTime=star_time_selected_date,
                EndTime=end_time_selected_date,
                Period=3600,
                Statistics=["Maximum"],
            )
            if metrics.get("Datapoints", None):
                workspace_available = True
        except Exception as error:
            logger.error(error)
        logger.debug(
            f"Returning the value {workspace_available} for workspace available."
        )
        return workspace_available

    def check_if_workspace_needs_to_be_terminated(self, workspace_id):
        """
        This method checks if the workspace needs to terminated based on the usage
        :param workspace_id:
        :return: A string value 'Yes' if the workspace is terminated and an empty string '' if not terminated
        """
        workspace_terminated = ""
        if self.settings.get("terminateUnusedWorkspaces") == "Dry Run":
            logger.debug(
                f"Termination option for workspace {workspace_id} is set to DryRun. The report was updated but the"
                " terminate action was not called"
            )
            workspace_terminated = "Yes - Dry Run"
        elif (
            self.settings.get("terminateUnusedWorkspaces") == "Yes"
            and not self.settings.get("isDryRun")
            and self.settings.get("dateTimeValues").get("current_month_last_day")
        ):
            logger.debug(
                f"All the criteria for termination of workspace {workspace_id} are met. "
                f"Calling the terminate action."
            )
            workspace_terminated = self.terminate_unused_workspace(workspace_id)
        return workspace_terminated

    def terminate_unused_workspace(self, workspace_id):
        """
        This method terminates the given workspace
        :param workspace_id: Workspace ID for the workspace
        """
        logger.debug(f"Terminating the workspace with workspace id {workspace_id}")
        workspace_terminated = ""
        try:
            response = self.workspaces_client.terminate_workspaces(
                TerminateWorkspaceRequests=[
                    {"WorkspaceId": workspace_id},
                ]
            )
            if not response.get("FailedRequests"):
                workspace_terminated = "Yes"
                logger.debug(
                    f"Successfully terminated the workspace with workspace id {workspace_id}"
                )
        except Exception as error:
            logger.exception(
                f"Error {error} occurred when terminating workspace {workspace_id}"
            )
        return workspace_terminated

    def compare_usage_metrics(
        self, workspace_id, billable_time, hourly_threshold, workspace_running_mode
    ):
        """
        This method compares the usage metrics for the workspace
        :param workspace_id: workspace id
        :param billable_time: billable time
        :param hourly_threshold: hourly threshold for the bundle type
        :param workspace_running_mode: new running mode
        :return: The result code and the new running mode for the workspace
        """
        if billable_time is None:
            result_code = "-E-"
            new_mode = workspace_running_mode
        elif hourly_threshold is None:
            result_code = "-S-"
            new_mode = workspace_running_mode
        elif workspace_running_mode == AUTO_STOP:
            result_code, new_mode = self.compare_usage_metrics_for_auto_stop(
                workspace_id, billable_time, hourly_threshold, workspace_running_mode
            )
        elif workspace_running_mode == ALWAYS_ON:
            result_code, new_mode = self.compare_usage_metrics_for_always_on(
                workspace_id, billable_time, hourly_threshold, workspace_running_mode
            )
        else:
            logger.error(
                f"workspaceRunningMode {workspace_running_mode} is unrecognized for workspace {workspace_id}"
            )
            result_code = "-S-"
            new_mode = workspace_running_mode

        return {"resultCode": result_code, "newMode": new_mode}

    def compare_usage_metrics_for_auto_stop(
        self,
        workspace_id: str,
        billable_time: int,
        hourly_threshold: int,
        workspace_running_mode: str,
    ) -> tuple[str, str]:
        """
        This method compares the usage metrics for Auto stop mode
        :param workspace_id: workspace id
        :param billable_time: billable time
        :param hourly_threshold: hourly threshold
        :param workspace_running_mode: workspace running mode
        :return: Result code and new running mode
        """
        logger.debug(f"workspaceRunningMode {workspace_running_mode} == AUTO_STOP")

        # If billable time is over the threshold for this bundle type
        if billable_time > hourly_threshold:
            logger.debug(
                f"billableTime {billable_time} > hourlyThreshold {hourly_threshold}"
            )

            # Change the workspace to ALWAYS_ON
            result_code = self.modify_workspace_properties(workspace_id, ALWAYS_ON)
            # if there was an exception in the modify_workspace API call, new mode is same as old mode
            if result_code == "-E-":
                new_mode = AUTO_STOP
            else:
                new_mode = ALWAYS_ON

        # Otherwise, report no change for the Workspace
        else:  # billable_time <= hourly_threshold:
            logger.debug(
                f"billableTime {billable_time} <= hourlyThreshold {hourly_threshold}"
            )
            result_code = "-N-"
            new_mode = AUTO_STOP

        return result_code, new_mode

    def compare_usage_metrics_for_always_on(
        self, workspace_id, billable_time, hourly_threshold, workspace_running_mode
    ):
        """
        This method compares the usage metrics for Always ON mode
        :param workspace_id: workspace id
        :param billable_time: billable time
        :param hourly_threshold: hourly threshold
        :param workspace_running_mode: workspace running mode
        :return: Result code and new running mode
        """
        logger.debug(f"workspaceRunningMode {workspace_running_mode} == ALWAYS_ON")

        # Only perform metrics gathering for ALWAYS_ON Workspaces at the end of the month.
        if self.settings.get("testEndOfMonth"):
            logger.debug(
                f"testEndOfMonth {self.settings.get('testEndOfMonth')} == True"
            )

            # If billable time is under the threshold for this bundle type
            if billable_time <= hourly_threshold:
                logger.debug(
                    f"billableTime {billable_time} < hourlyThreshold {hourly_threshold}"
                )

                # Change the workspace to AUTO_STOP
                result_code = self.modify_workspace_properties(workspace_id, AUTO_STOP)
                # if there was an exception in the modify_workspace API call, new mode is same as old mode
                if result_code == "-E-":
                    new_mode = ALWAYS_ON
                else:
                    new_mode = AUTO_STOP

            # Otherwise, report no change for the Workspace
            else:  # billable_time > hourly_threshold:
                logger.debug(
                    f"billableTime {billable_time} >= hourlyThreshold {hourly_threshold}"
                )
                result_code = "-N-"
                new_mode = ALWAYS_ON
        else:
            logger.debug(
                f"testEndOfMonth {self.settings.get('testEndOfMonth')} == False"
            )
            result_code = "-N-"
            new_mode = ALWAYS_ON

        return result_code, new_mode
