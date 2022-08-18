#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from .workspaces_helper import WorkspacesHelper
from .utils.s3_utils import upload_report
import boto3
import logging
import os
import typing

log = logging.getLogger(__name__)

class DirectoryReader():
    def __init__(self, session: boto3.session.Session) -> None:
        self._session = session

    def process_directory(self, region: str, stack_parameters: dict, directory_parameters: dict) -> typing.Tuple[int, typing.List[dict], str]:
        workspace_count = 0
        end_time = directory_parameters['EndTime']
        start_time = directory_parameters['StartTime']
        list_processed_workspaces = []
        directory_csv = ''
        log_body_directory_csv = ''
        is_dry_run = self.get_dry_run(stack_parameters)
        test_end_of_month = self.get_end_of_month(stack_parameters)
        directory_id = directory_parameters['DirectoryId']
        report_csv = 'WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode,Username,Computer Name,DirectoryId,WorkspaceTerminated,Tags\n'

        # List of bundles with specific hourly limits
        workspaces_helper = WorkspacesHelper(
            self._session,
            {
                'region': region,
                'hourlyLimits': {
                    'VALUE': stack_parameters['ValueLimit'],
                    'STANDARD': stack_parameters['StandardLimit'],
                    'PERFORMANCE': stack_parameters['PerformanceLimit'],
                    'POWER': stack_parameters['PowerLimit'],
                    'POWERPRO': stack_parameters['PowerProLimit'],
                    'GRAPHICS': stack_parameters['GraphicsLimit'],
                    'GRAPHICSPRO': stack_parameters['GraphicsProLimit']
                },
                'testEndOfMonth': test_end_of_month,
                'isDryRun': is_dry_run,
                'startTime': start_time,
                'endTime': end_time,
                'terminateUnusedWorkspaces': stack_parameters['TerminateUnusedWorkspaces']
            }
        )
        list_workspaces = workspaces_helper.get_workspaces_for_directory(directory_id)
        for workspace in list_workspaces:
            log.debug("Processing workspace {}".format(workspace))
            workspace_count = workspace_count + 1
            result = workspaces_helper.process_workspace(workspace)
            report_csv = workspaces_helper.append_entry(report_csv, result)  # Append result data to the CSV
            directory_csv = workspaces_helper.append_entry(directory_csv, result)  # Append result for aggregated report
            try:
                workspace_processed = {
                    'previousMode': result['initialMode'],
                    'newMode': result['newMode'],
                    'bundleType': result['bundleType'],
                    'hourlyThreshold': result['hourlyThreshold'],
                    'billableTime': result['billableTime']
                }
                list_processed_workspaces.append(workspace_processed)
            except Exception:
                log.debug("Could not append workspace for metrics. Skipping this workspace")
            log_body = workspaces_helper.expand_csv(report_csv)
            log_body_directory_csv = workspaces_helper.expand_csv(directory_csv)
            # Upload with default session, rather than delegated
            upload_report(boto3.session.Session(), stack_parameters, log_body, directory_id, region, self.get_account())
        return workspace_count, list_processed_workspaces, log_body_directory_csv

    def get_account(self) -> str:
        sts_client = self._session.client('sts')
        return sts_client.get_caller_identity()['Account']

    def get_dry_run(self, stack_parameters: dict) -> bool:
        return stack_parameters['DryRun'] == 'Yes'

    def get_end_of_month(self, stack_parameters: dict) -> bool:
        return stack_parameters['TestEndOfMonth'] == 'Yes'
