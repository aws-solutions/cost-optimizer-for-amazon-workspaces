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
        'DirectoryId': 'foobarbazqux',
        'DateTimeValues': {}
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
    previous_mode = 'AUTO_STOP'
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = [
        {
            'WorkspaceId': 'ws-wert1234',
            'DirectoryId': 'foobarbazqux',
            'UserName': 'test',
            'IpAddress': 'test',
            'State': 'AVAILABLE',
            'BundleId': 'testid123',
            'SubnetId': 'subnetid123',
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
    new_mode = 'ALWAYS_ON'
    bundle_type = 'Value_Limit'
    hourly_threshold = 10
    billable_time = 50
    MockWorkspacesHelper.return_value.process_workspace.return_value = {
        'workspaceID': 'ws-111',
        'billableTime': billable_time,
        'hourlyThreshold': hourly_threshold,
        'optimizationResult': new_mode,
        'newMode': new_mode,
        'bundleType': bundle_type,
        'initialMode': previous_mode,
        'userName': 'test_user',
        'computerName': 'test_computer',
        'directoryId': 'foobarbazqux',
        'tags': [],
        'workspaceTerminated': '',
        'reportDate': 'testDate'
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
    report_header = 'WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode,Username,Computer Name,DirectoryId,WorkspaceTerminated,Tags,ReportDate,\n'
    list_processed_workspaces = 'ws-111,50,10,ALWAYS_ON,Value_Limit,AUTO_STOP,ALWAYS_ON,test_user,test_computer,foobarbazqux,,"[]",testDate\n'
    assert result[2] == list_processed_workspaces
    log_body = report_header+list_processed_workspaces
    mock_upload_report.assert_called_once_with(mock_session.return_value, directory_parameters.get('DateTimeValues'), stack_parameters,log_body, directory_parameters['DirectoryId'], region, account)


def test_get_dry_run(session):
    directory_reader = DirectoryReader(session)
    assert directory_reader.get_dry_run({'DryRun': 'Yes'})
    assert not directory_reader.get_dry_run({'DryRun': 'No'})


def test_get_end_of_month(session):
    directory_reader = DirectoryReader(session)
    assert directory_reader.get_end_of_month({'TestEndOfMonth': 'Yes'})
    assert not directory_reader.get_end_of_month({'TestEndOfMonth': 'No'})
