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


class WorkspacesHelper(object):

    def __init__(self, settings):
        self.settings = settings
        self.maxRetries = 20
        self.client = boto3.client(
            'workspaces',
            region_name=self.settings.get('region'),
            config=botoConfig
        )
        self.metricsHelper = MetricsHelper(self.settings.get('region'))

    def append_entry(self, oldCsv, result):
        s = ','
        csv = oldCsv + s.join((
            result['workspaceID'],
            str(result['billableTime']),
            str(result['hourlyThreshold']),
            result['optimizationResult'],
            result['bundleType'],
            result['initialMode'],
            result['newMode'],
            result['userName'],
            result['directoryId'],
            ''.join(('"', str(result['tags']), '"')) + '\n'  # Adding quotes to the string to help with csv format
        ))

        return csv

    '''
    returns str
    '''

    def expand_csv(self, rawCSV):
        csv = rawCSV.replace(',-M-', ',ToMonthly').replace(',-H-', ',ToHourly'). \
            replace(',-E-', ',Failed to change the mode').replace(',-N-', ',No Change').replace(',-S-', ',Skipped')
        return csv

    '''
    returns {
        workspaceID: str,
        billableTime: int,
        hourlyThreshold: int,
        optimizationResult: str,
        initialMode: str,
        newMode: str,
        bundleType: str
    }
    '''

    def process_workspace(self, workspace):
        workspaceID = workspace['WorkspaceId']
        log.debug('workspaceID: %s', workspaceID)

        workspaceRunningMode = workspace['WorkspaceProperties']['RunningMode']
        log.debug('workspaceRunningMode: %s', workspaceRunningMode)

        workspaceBundleType = workspace['WorkspaceProperties']['ComputeTypeName']
        log.debug('workspaceBundleType: %s', workspaceBundleType)

        billableTime = self.metricsHelper.get_billable_hours(
            self.settings['startTime'],
            self.settings['endTime'],
            workspace
        )
        tags = self.get_tags(workspaceID)

        if self.check_for_skip_tag(tags):
            log.info('Skipping WorkSpace %s due to Skip_Convert tag', workspaceID)
            optimizationResult = {
                'resultCode': '-S-',
                'newMode': workspaceRunningMode
            }
            hourlyThreshold = "n/a"
        else:
            hourlyThreshold = self.get_hourly_threshold(workspaceBundleType)

            optimizationResult = self.compare_usage_metrics(
                workspaceID,
                billableTime,
                hourlyThreshold,
                workspaceRunningMode
            )

        return {
            'workspaceID': workspaceID,
            'billableTime': billableTime,
            'hourlyThreshold': hourlyThreshold,
            'optimizationResult': optimizationResult['resultCode'],
            'newMode': optimizationResult['newMode'],
            'bundleType': workspaceBundleType,
            'initialMode': workspaceRunningMode,
            'userName': workspace['UserName'],
            'directoryId': workspace['DirectoryId'],
            'tags': tags
        }

    '''
    returns str
    '''

    '''
    returns int
    '''

    def get_hourly_threshold(self, bundleType):
        if bundleType in self.settings.get('hourlyLimits'):
            return int(self.settings.get('hourlyLimits')[bundleType])
        else:
            return None

    '''
    returns {
        Workspaces: [obj...],
        NextToken: str
    }
    '''

    def get_workspaces_page(self, directoryID, nextToken):
        try:
            if nextToken == 'None':
                result = self.client.describe_workspaces(
                    DirectoryId=directoryID
                )
            else:
                result = self.client.describe_workspaces(
                    DirectoryId=directoryID,
                    NextToken=nextToken
                )

            return result
        except botocore.exceptions.ClientError as e:
            log.error("Error while getting the list of Workspaces: {}".format(e))
            raise

    '''
    returns bool
    '''

    def check_for_skip_tag(self, tags):
        # Added for case insensitive matching.  Works with standard alphanumeric tags
        for tagPair in tags:
            if tagPair['Key'].lower() == 'Skip_Convert'.lower():
                return True

        return False

    '''
    returns [
        {
            'Key': 'str',
            'Value': 'str'
        }, ...
    ]
    '''

    def get_tags(self, workspaceID):
        tags = []
        try:
            workspaceTags = self.client.describe_tags(
                ResourceId=workspaceID
            )
            log.debug(workspaceTags)

            tags = workspaceTags['TagList']

        except botocore.exceptions.ClientError as e:
            log.error(e)

        return tags

    '''
    returns str
    '''

    def modify_workspace_properties(self, workspaceID, newRunningMode):
        log.debug('modifyWorkspaceProperties')
        if not self.settings.get('isDryRun'):
            try:
                self.client.modify_workspace_properties(
                    WorkspaceId=workspaceID,
                    WorkspaceProperties={'RunningMode': newRunningMode}
                )
            except Exception as e:
                log.error('Exceeded retries for %s due to error: %s', workspaceID, e)
                return '-E-'  # return the status to indicate that the workspace was not processed.
        else:
            log.info('Skipping modifyWorkspaceProperties for Workspace %s due to dry run', workspaceID)

        if newRunningMode == ALWAYS_ON:
            result = '-M-'
        else:
            result = '-H-'
        return result

    '''
    returns {
        'resultCode': str,
        'newMode': str
    }
    '''

    def compare_usage_metrics(self, workspaceID, billableTime, hourlyThreshold, workspaceRunningMode):

        if hourlyThreshold is None:
            return {
                'resultCode': '-S-',
                'newMode': workspaceRunningMode
            }

        # If the Workspace is in Auto Stop (hourly)
        if workspaceRunningMode == AUTO_STOP:
            log.debug('workspaceRunningMode {} == AUTO_STOP'.format(workspaceRunningMode))

            # If billable time is over the threshold for this bundle type
            if billableTime > hourlyThreshold:
                log.debug('billableTime {} > hourlyThreshold {}'.format(billableTime, hourlyThreshold))

                # Change the workspace to ALWAYS_ON
                resultCode = self.modify_workspace_properties(workspaceID, ALWAYS_ON)
                # if there was an exception in the modify workspace API call, new mode is same as old mode
                if resultCode == '-E-':
                    newMode = AUTO_STOP
                else:
                    newMode = ALWAYS_ON

            # Otherwise, report no change for the Workspace
            elif billableTime <= hourlyThreshold:
                log.debug('billableTime {} <= hourlyThreshold {}'.format(billableTime, hourlyThreshold))
                resultCode = '-N-'
                newMode = AUTO_STOP

        # Or if the Workspace is Always On (monthly)
        elif workspaceRunningMode == ALWAYS_ON:
            log.debug('workspaceRunningMode {} == ALWAYS_ON'.format(workspaceRunningMode))

            # Only perform metrics gathering for ALWAYS_ON Workspaces at the end of the month.
            if self.settings.get('testEndOfMonth'):
                log.debug('testEndOfMonth {} == True'.format(self.settings.get('testEndOfMonth')))

                # If billable time is under the threshold for this bundle type
                if billableTime <= hourlyThreshold:
                    log.debug('billableTime {} < hourlyThreshold {}'.format(billableTime, hourlyThreshold))

                    # Change the workspace to AUTO_STOP
                    resultCode = self.modify_workspace_properties(workspaceID, AUTO_STOP)
                    # if there was an exception in the modify workspace API call, new mode is same as old mode
                    if resultCode == '-E-':
                        newMode = ALWAYS_ON
                    else:
                        newMode = AUTO_STOP

                # Otherwise, report no change for the Workspace
                elif billableTime > hourlyThreshold:
                    log.debug('billableTime {} >= hourlyThreshold {}'.format(billableTime, hourlyThreshold))
                    resultCode = '-N-'
                    newMode = ALWAYS_ON
            else:
                log.debug('testEndOfMonth {} == False'.format(self.settings.get('testEndOfMonth')))
                resultCode = '-N-'
                newMode = ALWAYS_ON

        # Otherwise, we don't know what it is so skip.
        else:
            log.warning(
                'workspaceRunningMode {} is unrecognized for workspace {}'.format(workspaceRunningMode, workspaceID))
            resultCode = '-S-'
            newMode = workspaceRunningMode

        return {
            'resultCode': resultCode,
            'newMode': newMode
        }
