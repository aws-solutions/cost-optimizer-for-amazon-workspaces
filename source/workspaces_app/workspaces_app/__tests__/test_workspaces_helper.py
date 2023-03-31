#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
import pytest
import datetime
import time
from .. import workspaces_helper
from ..utils import workspace_utils
from botocore.stub import Stubber
from dateutil.tz import tzutc


@pytest.fixture(scope='module')
def session():
    yield boto3.session.Session()


def test_skip_tag_true_process_standard_workspace(mocker, session):
    workspace = {
        'WorkspaceId': 'ws-68h123hty',
        'DirectoryId': 'd-901230bb84',
        'UserName': 'test_user',
        'IpAddress': '111.16.1.233',
        'State': 'AVAILABLE',
        'BundleId': 'wsb-cl123qzj1',
        'SubnetId': 'subnet-05d421387eaa7cf86',
        'ComputerName': 'A-APPW123KP4NP',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON',
            'RootVolumeSizeGib': 80,
            'UserVolumeSizeGib': 50,
            'ComputeTypeName': 'STANDARD'
        },
        'ModificationStates': []
    }

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": '',
            "end_time_selected_date": '',
            "current_month_last_day": '',
            "date_today": '',
            "date_for_s3_key": ''
        }
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mocker.patch.object(workspace_helper.metrics_helper, 'get_billable_hours')
    workspace_helper.metrics_helper.get_billable_hours.return_value = 444
    mocker.patch.object(workspace_helper, 'get_list_tags_for_workspace')
    mocker.patch.object(workspace_utils, 'check_for_skip_tag')
    workspace_utils.check_for_skip_tag.return_value = True
    result = workspace_helper.process_workspace(workspace)
    assert result['bundleType'] == 'STANDARD'
    assert result['newMode'] == 'ALWAYS_ON'  # The old mode should not be changed as the skip tag is True


def test_bundle_type_returned_process_workspace(mocker, session):
    workspace = {
        'WorkspaceId': 'ws-68h123hty',
        'DirectoryId': 'd-901230bb84',
        'UserName': 'test_user',
        'IpAddress': '111.16.1.233',
        'State': 'AVAILABLE',
        'BundleId': 'wsb-cl123qzj1',
        'SubnetId': 'subnet-05d421387eaa7cf86',
        'ComputerName': 'A-APPW123KP4NP',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON',
            'RootVolumeSizeGib': 80,
            'UserVolumeSizeGib': 50,
            'ComputeTypeName': 'PERFORMANCE'
        },
        'ModificationStates': []
    }

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": '',
            "end_time_selected_date": '',
            "current_month_last_day": '',
            "date_today": '',
            "date_for_s3_key": ''
        }
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mocker.patch.object(workspace_helper.metrics_helper, 'get_billable_hours')
    workspace_helper.metrics_helper.get_billable_hours.return_value = 100
    mocker.patch.object(workspace_helper, 'get_list_tags_for_workspace')
    mocker.patch.object(workspace_utils, 'check_for_skip_tag')
    workspace_utils.check_for_skip_tag.return_value = False
    mocker.patch.object(workspace_helper, 'get_hourly_threshold_for_bundle_type')
    workspace_helper.get_hourly_threshold_for_bundle_type.return_value = 5
    mocker.patch.object(workspace_helper, 'compare_usage_metrics')
    workspace_helper.compare_usage_metrics.return_value = {
        'resultCode': '-N-',
        'newMode': 'ALWAYS_ON'
    }
    mocker.patch.object(workspace_helper, 'get_termination_status')
    result = workspace_helper.process_workspace(workspace)
    assert result['bundleType'] == 'PERFORMANCE'
    assert result['billableTime'] == 100


def test_modify_workspace_properties_returns_always_on(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {'RunningMode': 'ALWAYS_ON'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'ALWAYS_ON'
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-M-'


def test_modify_workspace_properties_returns_auto_stop(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {'RunningMode': 'AUTO_STOP'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'AUTO_STOP'
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-H-'
    client_stubber.deactivate()


def test_modify_workspace_properties_returns_exception_error_code(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        'WorkspaceProperties': {'RunningMode': 'AUTO_STOP'}
    }

    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'AUTO_STOP'
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-E-'


def test_modify_workspace_api_is_not_called_for_dry_run_true_auto_stop(session):
    # validate that the stubber call is not made when Dry Run is set to True
    # send an invalid request using stubber and validate that the does not method throws exception

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        'WorkspaceProperties': {'RunningMode': 'AUTO_STOP'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'AUTO_STOP'
    # check if the method throws exception and validate that the stubber was not called
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-H-'
    client_stubber.deactivate()


def test_modify_workspace_api_is_not_called_for_dry_run_true_always_on(session):
    # validate that the stubber call is not made when Dry Run is set to True
    # send an invalid request using stubber and validate that the does not method throws exception

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        'WorkspaceProperties': {'RunningMode': 'ALWAYS_ON'}
    }
    client_stubber.add_response('modify_workspace_properties', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    new_running_mode = 'ALWAYS_ON'
    # check if the method throws exception and validate that the stubber was not called
    result = workspace_helper.modify_workspace_properties(workspace_id, new_running_mode)
    assert result == '-M-'
    client_stubber.deactivate()


def test_check_for_skip_tag_returns_true_for_skip_convert_tag():
    tags = [{'Key': 'skip_convert', 'Value': 'True'}]
    result = workspace_utils.check_for_skip_tag(tags)
    assert result is True


def test_check_for_skip_tag_returns_false_if_skip_convert_tag_absent():
    tags = [{'Key': 'nothing', 'Value': 'True'}]
    result = workspace_utils.check_for_skip_tag(tags)
    assert result is False


def test_terminate_unused_workspace_returns_yes_when_workspace_terminated_successfully(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {'TerminateWorkspaceRequests': [{'WorkspaceId': '123qwer'}]}
    client_stubber.add_response('terminate_workspaces', response, expected_params)
    client_stubber.activate()
    workspace_id = '123qwer'
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == 'Yes'
    client_stubber.deactivate()


def test_terminate_unused_workspace_returns_empty_string_when_workspace_not_terminated(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('TerminateWorkspaceRequests', "Invalid_request")
    client_stubber.activate()
    workspace_id = '123qwer'
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == ''
    client_stubber.deactivate()


def test_check_if_workspace_available_on_first_day_selected_month_returns_true(session):
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": '',
            "date_today": '',
            "date_for_s3_key": ''
        }
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = '123qwer'
    response = {
        'Datapoints': [
            {'Timestamp': datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'}
        ]
    }
    expected_params = {
        'Dimensions': [
            {
                'Name': 'WorkspaceId',
                'Value': workspace_id
            }
        ],
        'Namespace': 'AWS/WorkSpaces',
        'MetricName': 'Available',
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 3600,
        'Statistics': ['Maximum']
    }
    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day_selected_month(workspace_id)
    assert result is True
    client_stubber.deactivate()


def test_check_if_workspace_available_on_first_day_selected_month_returns_false(session):
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": '',
            "date_today": '',
            "date_for_s3_key": ''
        }
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = '123qwer'
    response = {
        'Datapoints': []
    }
    expected_params = {
        'Dimensions': [
            {
                'Name': 'WorkspaceId',
                'Value': workspace_id
            }
        ],
        'Namespace': 'AWS/WorkSpaces',
        'MetricName': 'Available',
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 3600,
        'Statistics': ['Maximum']
    }
    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day_selected_month(workspace_id)
    assert result is False
    client_stubber.deactivate()


def test_check_if_workspace_available_on_first_day_selected_month_returns_false_for_exception(session):
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": '',
            "date_today": '',
            "date_for_s3_key": ''
        }
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = '123qwer'
    client_stubber.add_client_error('get_metric_statistics', 'Invalid request')
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day_selected_month(workspace_id)
    assert result is False
    client_stubber.deactivate()


def test_get_workspaces_for_directory_returns_list_of_workspaces(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {
        'Workspaces': [
            {'WorkspaceId': '1234'},
            {'WorkspaceId': '1234'},
            {'WorkspaceId': '1234'}
        ]
    }
    expected_params = {
        'DirectoryId': directory_id
    }
    client_stubber.add_response('describe_workspaces', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.get_workspaces_for_directory(directory_id)
    assert result == [
        {'WorkspaceId': '1234'},
        {'WorkspaceId': '1234'},
        {'WorkspaceId': '1234'}
    ]
    client_stubber.deactivate()


def test_get_workspaces_for_directory_returns_empty_list_for_exception(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('describe_workspaces', 'Invalid Directory')
    client_stubber.activate()
    result = workspace_helper.get_workspaces_for_directory(directory_id)
    assert result == []
    client_stubber.deactivate()


def test_check_if_workspace_needs_to_be_terminated_returns_dry_run_is_dry_run_true(session):
    # 'terminateUnusedWorkspaces': 'Dry Run'
    # 'isDryRun': True

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == 'Yes - Dry Run'


def test_check_if_workspace_needs_to_be_terminated_returns_dry_run_is_dry_run_false(session):
    # 'terminateUnusedWorkspaces': 'Dry Run'
    # 'isDryRun': False

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == 'Yes - Dry Run'


def test_check_if_workspace_needs_to_be_terminated_returns_empty_string_is_dry_run_true(session):
    # 'terminateUnusedWorkspaces': 'Yes'
    # 'isDryRun': True

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == ''


def test_check_if_workspace_needs_to_be_terminated_returns_yes_is_dry_run_false(mocker, session):
    # 'terminateUnusedWorkspaces': 'Yes'
    # 'isDryRun': False

    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': False,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Yes'
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mocker.patch.object(workspace_helper, 'terminate_unused_workspace')
    workspace_helper.terminate_unused_workspace.return_value = 'Yes'
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(workspace_id)
    assert result == 'Yes'


def test_check_if_workspace_used_for_selected_period_returns_false_if_timestamp_is_none():
    last_known_user_connection_timestamp = None
    result = workspace_utils.check_if_workspace_used_for_selected_period(last_known_user_connection_timestamp)
    assert result is False


def test_check_if_workspace_used_for_selected_period_returns_false_if_timestamp_is_before_first_day():
    last_known_user_connection_timestamp = datetime.datetime.strptime('2021-01-10 19:35:15.524000+00:00',
                                                                      '%Y-%m-%d %H:%M:%S.%f+00:00')
    result = workspace_utils.check_if_workspace_used_for_selected_period(last_known_user_connection_timestamp)
    assert result is False


def test_check_if_workspace_used_for_selected_period_returns_true_if_timestamp_is_first_day_selected_month():
    last_known_user_connection_timestamp = datetime.datetime.utcnow().today().replace(day=1, hour=0, minute=0, second=0,
                                                                                      microsecond=0)
    result = workspace_utils.check_if_workspace_used_for_selected_period(last_known_user_connection_timestamp)
    assert result is True


def test_get_last_known_user_connection_timestamp_returns_last_connected_time_value(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    last_known_user_connection_timestamp = datetime.datetime.strptime('2021-08-10 19:35:15.524000+00:00',
                                                                      '%Y-%m-%d %H:%M:%S.%f+00:00')
    workspace_id = "123qwe123qwe"
    response = {
        'WorkspacesConnectionStatus': [{
            'LastKnownUserConnectionTimestamp': last_known_user_connection_timestamp
        }]
    }
    expected_params = {
        'WorkspaceIds': [workspace_id]
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_response('describe_workspaces_connection_status', response, expected_params)
    client_stubber.activate()
    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)
    assert result == last_known_user_connection_timestamp
    client_stubber.deactivate()


def test_get_last_known_user_connection_timestamp_returns_resource_unavailable_for_exception(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('get_last_known_user_connection_timestamp', 'Invalid workspace')
    client_stubber.activate()
    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)
    assert result == 'ResourceUnavailable'
    client_stubber.deactivate()


def test_get_termination_status_returns_empty_string_for_terminate_workspaces_no(session):
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = 'No'
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'No'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''


def test_get_termination_status_returns_yes_for_terminate_workspaces_yes(mocker, session):
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Yes',
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": False,
            "date_today": '',
            "date_for_s3_key": ''
        }

    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = 'Yes'

    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_utils, 'check_if_workspace_used_for_selected_period')
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day_selected_month')
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes'

    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == 'Yes'


def test_get_termination_status_returns_dry_run_for_terminate_workspaces_dry_run(mocker, session):
    start_time = time.strftime("%Y-%m") + '-01T00:00:00Z'
    end_time = time.strftime("%Y-%m") + '-02T00:00:00Z'
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run',
        'dateTimeValues': {
            "start_time_for_current_month": '',
            "end_time_for_current_month": '',
            "last_day_current_month": '',
            "first_day_selected_month": '',
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": False,
            "date_today": '',
            "date_for_s3_key": ''
        }
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')
    mocker.patch.object(workspace_utils, 'check_if_workspace_used_for_selected_period')
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = False
    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day_selected_month')
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = True
    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == 'Yes - Dry Run'


def test_get_termination_status_returns_empty_string_when_workspace_used(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_utils, 'check_if_workspace_used_for_selected_period')
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day_selected_month')
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = True

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''


def test_get_termination_status_returns_empty_string_when_workspace_not_available_first_day(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = 'Yes'
    mocker.patch.object(workspace_helper, 'get_last_known_user_connection_timestamp')

    mocker.patch.object(workspace_utils, 'check_if_workspace_used_for_selected_period')
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_available_on_first_day_selected_month')
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = False

    mocker.patch.object(workspace_helper, 'check_if_workspace_needs_to_be_terminated')
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = 'Yes - Dry Run'
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ''


def test_get_workspaces_for_directory_use_next_token(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'terminateUnusedWorkspaces': 'Dry Run'
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    expected_params_1 = {
        'DirectoryId': directory_id
    }

    response_1 = {
        'Workspaces': [{'WorkspaceId': 'id_1'}],
        'NextToken': 's223123jj32'
    }

    expected_params_2 = {
        'DirectoryId': directory_id,
        'NextToken': 's223123jj32'
    }

    response_2 = {
        'Workspaces': [{'WorkspaceId': 'id_2'}]
    }

    client_stubber.add_response('describe_workspaces', response_1, expected_params_1)
    client_stubber.add_response('describe_workspaces', response_2, expected_params_2)
    client_stubber.activate()
    response = workspace_helper.get_workspaces_for_directory(directory_id)
    client_stubber.activate()
    assert response == [{'WorkspaceId': 'id_1'}, {'WorkspaceId': 'id_2'}]


def test_get_workspaces_for_directory_no_next_token(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    expected_params_1 = {
        'DirectoryId': directory_id
    }

    response_1 = {
        'Workspaces': [{'WorkspaceId': 'id_1'}]
    }

    expected_params_2 = {
        'DirectoryId': directory_id,
        'NextToken': 's223123jj32'
    }

    response_2 = {
        'Workspaces': [{'WorkspaceId': 'id_2'}]
    }

    client_stubber.add_response('describe_workspaces', response_1, expected_params_1)
    client_stubber.add_response('describe_workspaces', response_2, expected_params_2)
    client_stubber.activate()
    response = workspace_helper.get_workspaces_for_directory(directory_id)
    client_stubber.activate()
    assert response == [{'WorkspaceId': 'id_1'}]


def test_get_workspaces_for_directory_return_empty_list_for_exception(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('describe_workspaces', "Invalid_request")
    client_stubber.activate()
    response = workspace_helper.get_workspaces_for_directory(directory_id)
    client_stubber.activate()
    assert response == []


def test_get_list_tags_for_workspace_returns_list_of_tags(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    tags = {'TagList': ['tags']}
    workspace_id = 1
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mocker.patch.object(workspace_helper.workspaces_client, 'describe_tags')
    workspace_helper.workspaces_client.describe_tags.return_value = tags
    assert workspace_helper.get_list_tags_for_workspace(workspace_id) == ['tags']


def test_compare_usage_metrics__returns_error_for_billable_time_none(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    new_mode = "ALWAYS_ON"
    expected = {
        'resultCode': '-E-',
        'newMode': new_mode
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    assert workspace_helper.compare_usage_metrics(1, None, None, new_mode) == expected


def test_compare_usage_metrics__returns_skipped_for_hourly_threshold_none(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    new_mode = "ALWAYS_ON"
    expected = {
        'resultCode': '-S-',
        'newMode': new_mode
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    assert workspace_helper.compare_usage_metrics(1, 1, None, new_mode) == expected


def test_get_hourly_threshold_for_bundle_type_returns_correct_value(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': {'value': 85},
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.get_hourly_threshold_for_bundle_type('value')

    assert result is 85


def test_get_hourly_threshold_for_bundle_type(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': {},
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.get_hourly_threshold_for_bundle_type('Value')

    assert result is None


def test_get_list_tags_for_workspace_returns_none_in_case_of_exception(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    workspace_id = 'ws-abd123'
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error('describe_tags', 'Invalid Tags')
    assert workspace_helper.get_list_tags_for_workspace(workspace_id) is None


def test_compare_usage_metrics__returns_new_mode_as_auto_stop(session, mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = {
        'resultCode': '-H-',
        'newMode': 'AUTO_STOP'
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'compare_usage_metrics_for_auto_stop')
    workspace_helper.compare_usage_metrics_for_auto_stop.return_value = ['-H-', 'AUTO_STOP']

    assert workspace_helper.compare_usage_metrics(1, 1, 85, "AUTO_STOP") == expected


def test_compare_usage_metrics__returns_new_mode_as_always_on(session, mocker):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = {
        'resultCode': '-M-',
        'newMode': 'ALWAYS_ON'
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'compare_usage_metrics_for_always_on')
    workspace_helper.compare_usage_metrics_for_always_on.return_value = ['-M-', 'ALWAYS_ON']

    assert workspace_helper.compare_usage_metrics(1, 100, 85, "ALWAYS_ON") == expected


def test_compare_usage_metrics__returns_new_mode_same_as_old_mode_for_error(session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = {
        'resultCode': '-S-',
        'newMode': 'ALWAYS_ON_Error'
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    assert workspace_helper.compare_usage_metrics(1, 100, 85, "ALWAYS_ON_Error") == expected


def test_compare_usage_metrics_for_auto_stop_returns_always_on_if_billable_time_exceeds_threshold(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-M-', 'ALWAYS_ON')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'modify_workspace_properties')
    workspace_helper.modify_workspace_properties.return_value = '-M-'

    assert workspace_helper.compare_usage_metrics_for_auto_stop('ws-112d', 100, 85, "AUTO_STOP") == expected


def test_compare_usage_metrics_for_auto_stop_returns_auto_stop_if_billable_time_less_than_threshold(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-N-', 'AUTO_STOP')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    assert workspace_helper.compare_usage_metrics_for_auto_stop('ws-112d', 10, 85, "AUTO_STOP") == expected


def test_compare_usage_metrics_for_auto_stop_returns_auto_stop_for_api_exception(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': 'yes',
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-E-', 'AUTO_STOP')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'modify_workspace_properties')
    workspace_helper.modify_workspace_properties.return_value = '-E-'

    assert workspace_helper.compare_usage_metrics_for_auto_stop('ws-112d', 100, 85, "AUTO_STOP") == expected


def test_compare_usage_metrics_for_always_on_returns_auto_stop_if_billable_time_less_than_threshold(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-H-', 'AUTO_STOP')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'modify_workspace_properties')
    workspace_helper.modify_workspace_properties.return_value = '-H-'

    assert workspace_helper.compare_usage_metrics_for_always_on('ws-112d', 10, 85, "ALWAYS_ON") == expected


def test_compare_usage_metrics_for_always_on_returns_always_on_if_billable_time_exceeds_threshold(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-N-', 'ALWAYS_ON')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    assert workspace_helper.compare_usage_metrics_for_always_on('ws-112d', 100, 85, "ALWAYS_ON") == expected


def test_compare_usage_metrics_for_always_on_returns_always_on_for_api_exception(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': True,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-E-', 'ALWAYS_ON')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'modify_workspace_properties')
    workspace_helper.modify_workspace_properties.return_value = '-E-'

    assert workspace_helper.compare_usage_metrics_for_always_on('ws-112d', 10, 85, "ALWAYS_ON") == expected


def test_compare_usage_metrics_for_always_on_returns_no_change_for_end_of_month_false(mocker, session):
    settings = {
        'region': 'us-east-1',
        'hourlyLimits': 10,
        'testEndOfMonth': False,
        'isDryRun': True,
        'startTime': 1,
        'endTime': 2,
        'TerminateUnusedWorkspaces': 'Dry Run'
    }
    expected = ('-N-', 'ALWAYS_ON')
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, 'modify_workspace_properties')
    workspace_helper.modify_workspace_properties.return_value = '-N-'

    assert workspace_helper.compare_usage_metrics_for_always_on('ws-112d', 10, 85, "ALWAYS_ON") == expected
