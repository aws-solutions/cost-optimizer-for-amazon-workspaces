#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from ..directory_reader import DirectoryReader
import boto3
import pytest
import unittest
import datetime

@pytest.fixture(scope='module')
def session():
    yield boto3.session.Session()

def test_construct(session):
    DirectoryReader(session)

@pytest.fixture()
def stack_parameters():
    yield {
        'DryRun': 'No',
        'TestEndOfMonth': 'No',
        'ValueLimit': 0,
        'StandardLimit': 0,
        'PerformanceLimit': 0,
        'PowerLimit': 0,
        'PowerProLimit': 0,
        'GraphicsLimit': 0,
        'GraphicsProLimit': 0,
        'TerminateUnusedWorkspaces': 'No'
    }

@pytest.fixture()
def directory_parameters():
    yield {
        'StartTime': datetime.datetime.now(),
        'EndTime': datetime.datetime.now(),
        'DirectoryId': 'foobarbazqux'
    }

@unittest.mock.patch(DirectoryReader.__module__ + '.WorkspacesHelper')
def test_process_directory_no_workspaces(MockWorkspacesHelper, session, stack_parameters, directory_parameters):
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = []
    directory_reader = DirectoryReader(session)
    result = directory_reader.process_directory('us-east-1', stack_parameters, directory_parameters)
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.assert_called_once()
    assert result[0] == 0
    assert result[1] == []
    assert result[2] == ''

@unittest.mock.patch('boto3.session.Session')
@unittest.mock.patch(DirectoryReader.__module__ + '.upload_report')
@unittest.mock.patch(DirectoryReader.__module__ + '.WorkspacesHelper')
def test_process_directory(MockWorkspacesHelper, mock_upload_report, mock_session, stack_parameters, directory_parameters):
    previous_mode = 'previous_mode'
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = [
        {
            'WorkspaceId': 'string',
            'DirectoryId': 'string',
            'UserName': 'string',
            'IpAddress': 'string',
            'State': 'AVAILABLE',
            'BundleId': 'string',
            'SubnetId': 'string',
            'ErrorMessage': 'string',
            'ErrorCode': 'string',
            'ComputerName': 'string',
            'VolumeEncryptionKey': 'string',
            'UserVolumeEncryptionEnabled': False,
            'RootVolumeEncryptionEnabled': False,
            'WorkspaceProperties': {
                'RunningMode': previous_mode,
                'RunningModeAutoStopTimeoutInMinutes': 123,
                'RootVolumeSizeGib': 123,
                'UserVolumeSizeGib': 123,
                'ComputeTypeName': 'STANDARD'
            },
            'ModificationStates': []
        }
    ]
    new_mode = 'new_mode'
    bundle_type = 'bundle_type'
    hourly_threshold = 10
    billable_time = 50
    MockWorkspacesHelper.return_value.process_workspace.return_value = {
        'workspaceID': 'string',
        'billableTime': billable_time,
        'hourlyThreshold': hourly_threshold,
        'optimizationResult': new_mode,
        'newMode': new_mode,
        'bundleType': bundle_type,
        'initialMode': previous_mode,
        'userName': 'string',
        'computerName': 'string',
        'directoryId': 'string',
        'tags': [],
        'workspaceTerminated': 'string'
    }
    MockWorkspacesHelper.return_value.append_entry.return_value = ''
    MockWorkspacesHelper.return_value.expand_csv.return_value = ''
    account = '111111111111'
    mock_session.return_value.client.return_value.get_caller_identity.return_value = {'Account': account}
    directory_reader = DirectoryReader(mock_session())
    region = 'us-east-1'
    result = directory_reader.process_directory(region, stack_parameters, directory_parameters)
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.assert_called_once()
    assert result[0] == 1
    assert result[1] == [
        {
            'previousMode': previous_mode,
            'newMode': new_mode,
            'bundleType': bundle_type,
            'hourlyThreshold': hourly_threshold,
            'billableTime': billable_time
        }
    ]
    assert result[2] == ''
    mock_upload_report.assert_called_once_with(mock_session.return_value, stack_parameters, '', directory_parameters['DirectoryId'], region, account)

def test_get_dry_run(session):
    directory_reader = DirectoryReader(session)
    assert directory_reader.get_dry_run({'DryRun': 'Yes'})
    assert not directory_reader.get_dry_run({'DryRun': 'No'})

def test_get_end_of_month(session):
    directory_reader = DirectoryReader(session)
    assert directory_reader.get_end_of_month({'TestEndOfMonth': 'Yes'})
    assert not directory_reader.get_end_of_month({'TestEndOfMonth': 'No'})
