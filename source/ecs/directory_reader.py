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

# This file calls the workspaces_helper module to read cloudwatch logs.  The only AWS activity in this file
# is writing the CSV file to S3 and making a call to our tracking url.

import logging
import os
from ecs.workspaces_helper import WorkspacesHelper
from ecs.utils.s3_utils import upload_report

log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)


class DirectoryReader(object):

    def __init__(self):
        return

    def process_directory(self, region, stack_parameters, directory_parameters):
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
        workspaces_helper = WorkspacesHelper({
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
        })
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
            upload_report(stack_parameters, log_body, directory_id, region)
        return workspace_count, list_processed_workspaces, log_body_directory_csv

    def get_dry_run(self, stack_parameters):
        return stack_parameters['DryRun'] == 'Yes'


    def get_end_of_month(self, stack_parameters):
        return stack_parameters['TestEndOfMonth'] == 'Yes'
