#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Amazon Software License (the "License"). You may not   #
#  use this file except in compliance with the License. A copy of the        #
#  License is located at                                                     #
#                                                                            #
#      http://aws.amazon.com/asl/                                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is distributed #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,        #
#  express or implied. See the License for the specific language governing   #
#  permissions and limitations under the License.                            #
##############################################################################

from lib.workspaces_helper import WorkspacesHelper
from lib.metrics_helper import MetricsHelper

def test_process_workspace(monkeypatch):

    workspacesHelper = WorkspacesHelper({
        'region': 'us-west-2',
        'hourlyLimits': {
            'VALUE': 5,
            'STANDARD': 5,
            'PERFORMANCE': 5,
            'GRAPHICS': 5
        },
        'testEndOfMonth': False,
        'isDryRun': True,
        'startTime': '2018-02-01T00:00:00Z',
        'endTime': '2018-02-01T12:00:00Z'
    })

    def mock_get_bundle_type(BundleIds = 'wsb-xxxxxxxxx'):
        return 'VALUE'

    monkeypatch.setattr(workspacesHelper, 'get_bundle_type', mock_get_bundle_type)

    def mock_check_for_skip_tag(workspaceID):
        return False

    monkeypatch.setattr(workspacesHelper, 'check_for_skip_tag', mock_check_for_skip_tag)

    def mock_get_billable_time(workspaceID, workspaceRunningMode, startTime, endTime):
        return 10

    monkeypatch.setattr(workspacesHelper.metricsHelper, 'get_billable_time', mock_get_billable_time)

    def mock_modify_workspace_properties(workspaceID, newRunningMode, isDryRun):
        return '-M-'

    monkeypatch.setattr(workspacesHelper, 'modify_workspace_properties', mock_modify_workspace_properties)

    result = workspacesHelper.process_workspace({
        "UserName": "username",
        "DirectoryId": "d-xxxxxxxxx",
        "WorkspaceProperties": {
            "UserVolumeSizeGib": 50,
            "RunningModeAutoStopTimeoutInMinutes": 60,
            "RunningMode": "AUTO_STOP",
            "RootVolumeSizeGib": 80,
            "ComputeTypeName": "STANDARD"
        },
        "ModificationStates": [],
        "State": "STOPPED",
        "WorkspaceId": "ws-xxxxxxxxx",
        "BundleId": "wsb-xxxxxxxxx"
    })

    assert result['workspaceID'] == 'ws-xxxxxxxxx'
    assert result['optimizationResult'] == '-M-'
    assert result['billableTime'] == 10
    assert result['hourlyThreshold'] == 5
    assert result['bundleType'] == 'VALUE'

def test_process_workspace_skip(monkeypatch):

    workspacesHelper = WorkspacesHelper({
        'region': 'us-west-2',
        'hourlyLimits': {
            'VALUE': 5,
            'STANDARD': 5,
            'PERFORMANCE': 5,
            'GRAPHICS': 5
        },
        'testEndOfMonth': False,
        'isDryRun': True,
        'startTime': '2018-02-01T00:00:00Z',
        'endTime': '2018-02-01T12:00:00Z'
    })

    def mock_describe_tags(ResourceId='ws-xxxxxxxxx'):
        return {
            'ResponseMetadata': {
                'RetryAttempts': 0,
                'HTTPStatusCode': 200,
                'RequestId': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'HTTPHeaders': {
                    'x-amzn-requestid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                    'date': 'Thu, 07 Feb 1988 11:00:00 GMT',
                    'content-length': '42',
                    'content-type': 'application/x-amz-json-1.1'
                }
            },
            'TagList': [
                {
                    'Value': 'True',
                    'Key':'Skip_Convert'
                }
            ]
        }

    monkeypatch.setattr(workspacesHelper.client, 'describe_tags', mock_describe_tags)

    def mock_get_bundle_type(BundleIds = 'wsb-xxxxxxxxx'):
        return 'VALUE'

    monkeypatch.setattr(workspacesHelper, 'get_bundle_type', mock_get_bundle_type)

    def mock_get_billable_time(workspaceID, workspaceRunningMode, startTime, endTime):
        return 0

    monkeypatch.setattr(workspacesHelper.metricsHelper, 'get_billable_time', mock_get_billable_time)


    result = workspacesHelper.process_workspace({
        "UserName": "username",
        "DirectoryId": "d-xxxxxxxxx",
        "WorkspaceProperties": {
            "UserVolumeSizeGib": 50,
            "RunningModeAutoStopTimeoutInMinutes": 60,
            "RunningMode": "AUTO_STOP",
            "RootVolumeSizeGib": 80,
            "ComputeTypeName": "STANDARD"
        },
        "ModificationStates": [],
        "State": "STOPPED",
        "WorkspaceId": "ws-xxxxxxxxx",
        "BundleId": "wsb-xxxxxxxxx"
    })

    assert result['workspaceID'] == 'ws-xxxxxxxxx'
    assert result['optimizationResult'] == '-S-'
    assert result['billableTime'] == 0
    assert result['hourlyThreshold'] == 'n/a'
    assert result['bundleType'] == 'VALUE'
