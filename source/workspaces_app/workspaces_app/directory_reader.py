#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import datetime
import os
import time
import typing

# AWS Libraries
import boto3
from aws_lambda_powertools import Logger

# Cost Optimizer for Amazon Workspaces
from .utils.dashboard_metrics import DashboardMetrics
from .utils.s3_utils import upload_report
from .utils.usage_table_dao import UsageTableDAO
from .workspace_record import WorkspaceDescription, WorkspaceRecord
from .workspaces_helper import WorkspacesHelper

# Initialize logger
logger = Logger(service="directory_reader")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)


class DirectoryReader:
    def __init__(self, session: boto3.session.Session, region: str) -> None:
        self._session = session
        self.region = region
        self.usage_table_dao = UsageTableDAO(
            boto3.session.Session(), os.environ.get("UsageTable"), region
        )  # provide default session so as not to use assumed role session

    def process_directory(
        self,
        stack_parameters: dict,
        directory_parameters: dict,
        dashboard_metrics: DashboardMetrics,
    ) -> typing.Tuple[int, typing.List[dict], str]:
        workspace_count = 0
        list_processed_workspaces = []
        directory_csv = ""
        is_dry_run = self.get_dry_run(stack_parameters)
        test_end_of_month = self.get_end_of_month(stack_parameters)
        directory_id = directory_parameters.get("DirectoryId")
        directory_info = directory_parameters.get("Directory", {})
        report_csv = WorkspaceRecord.csv_header()

        # List of bundles with specific hourly limits
        workspaces_helper = WorkspacesHelper(
            self._session,
            {
                "region": self.region,
                "usageTable": stack_parameters.get("UsageTable"),
                "userSessionTable": stack_parameters.get("UserSessionTable"),
                "hourlyLimits": {
                    "VALUE": stack_parameters.get("ValueLimit"),
                    "STANDARD": stack_parameters.get("StandardLimit"),
                    "PERFORMANCE": stack_parameters.get("PerformanceLimit"),
                    "POWER": stack_parameters.get("PowerLimit"),
                    "POWERPRO": stack_parameters.get("PowerProLimit"),
                    "GRAPHICS_G4DN": stack_parameters.get("GraphicsG4dnLimit"),
                    "GRAPHICSPRO_G4DN": stack_parameters.get("GraphicsProG4dnLimit"),
                },
                "testEndOfMonth": test_end_of_month,
                "isDryRun": is_dry_run,
                "dateTimeValues": directory_parameters.get("DateTimeValues"),
                "terminateUnusedWorkspaces": stack_parameters.get(
                    "TerminateUnusedWorkspaces"
                ),
                "directoryInfo": directory_info,
            },
        )
        list_workspaces = workspaces_helper.get_workspaces_for_directory(directory_id)
        for workspace in list_workspaces:
            try:
                logger.debug("Processing workspace {}".format(workspace))
                bundle_type = workspace.get("WorkspaceProperties").get(
                    "ComputeTypeName"
                )
                usage_threshold = (
                    workspaces_helper.get_hourly_threshold_for_bundle_type(bundle_type)
                )
                account = self.get_account()
                workspace_count = workspace_count + 1
                ws_description = WorkspaceDescription(
                    account=account,
                    region=self.region,
                    directory_id=directory_id,
                    workspace_id=workspace.get("WorkspaceId"),
                    initial_mode=workspace.get("WorkspaceProperties").get(
                        "RunningMode"
                    ),
                    usage_threshold=usage_threshold,
                    bundle_type=bundle_type,
                    username=workspace.get("UserName", ""),
                    computer_name=workspace.get("ComputerName", ""),
                )
                ws_record = self.usage_table_dao.get_workspace_ddb_item(ws_description)
                if isinstance(ws_record, WorkspaceRecord) and self.is_prev_month_data(
                    ws_record
                ):
                    # If the current month is different from the last reported month,
                    # treat it as if there is no previous data available
                    ws_record = ws_description

                new_ws_record = workspaces_helper.process_workspace(
                    ws_record,
                    workspace.get("WorkspaceProperties").get(
                        "RunningModeAutoStopTimeoutInMinutes"
                    ),
                    dashboard_metrics,
                )
                report_csv += new_ws_record.to_csv()
                directory_csv += new_ws_record.to_csv()
                workspace_processed = {
                    "previousMode": new_ws_record.description.initial_mode,
                    "newMode": new_ws_record.billing_data.new_mode,
                    "bundleType": new_ws_record.description.bundle_type,
                    "hourlyThreshold": new_ws_record.description.usage_threshold,
                    "billableTime": new_ws_record.billing_data.billable_hours,
                    "workspaceType": new_ws_record.workspace_type,
                }
                list_processed_workspaces.append(workspace_processed)
                self.usage_table_dao.update_ddb_item(new_ws_record)
            except Exception as e:
                logger.exception(
                    f"Error processing the workspace {workspace.get('WorkspaceId')}: {e}"
                )
            # Upload with default session, rather than delegated
            upload_report(
                boto3.session.Session(),
                directory_parameters.get("DateTimeValues"),
                stack_parameters,
                report_csv,
                directory_id,
                self.region,
                self.get_account(),
            )
        return workspace_count, list_processed_workspaces, directory_csv

    def get_account(self) -> str:
        sts_client = self._session.client("sts")
        return sts_client.get_caller_identity().get("Account")

    def get_dry_run(self, stack_parameters: dict[str, any]) -> bool:
        return stack_parameters.get("DryRun") == "Yes"

    def get_end_of_month(self, stack_parameters: dict[str, any]) -> bool:
        return stack_parameters.get("TestEndOfMonth") == "Yes"

    def is_prev_month_data(self, ws_record: WorkspaceRecord) -> bool:
        current_month = time.gmtime().tm_mon
        last_reported_month = datetime.datetime.strptime(
            ws_record.last_reported_metric_period, "%Y-%m-%dT%H:%M:%SZ"
        ).month
        is_prev_month_data = current_month != last_reported_month
        if current_month != last_reported_month:
            logger.debug(
                f"For workspace {ws_record.description.workspace_id}, the current month({current_month}) is different from last reported month({last_reported_month})"
            )
        return is_prev_month_data
