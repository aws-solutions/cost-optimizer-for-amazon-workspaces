#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from ..metrics_helper import MetricsHelper, get_autostop_timeout_hours
import boto3
import pytest
from unittest import mock
from botocore.stub import Stubber
from dateutil.tz import tzutc, tzlocal
import datetime
import os

@mock.patch.dict(os.environ, {'AutoStopTimeoutHours': str(12)})
def test_get_autostop_timeout_hours():
    assert get_autostop_timeout_hours() == 12

@mock.patch.dict(os.environ, {}, clear = True)
def test_get_autostop_timeout_hours_not_set():
    with pytest.raises(TypeError):
        get_autostop_timeout_hours()

@mock.patch.dict(os.environ, {'AutoStopTimeoutHours': 'garbage'})
def test_get_autostop_timeout_hours_invalid():
    with pytest.raises(ValueError):
        get_autostop_timeout_hours()

@pytest.fixture(scope="module")
def session():
    yield boto3.session.Session()

def test_get_user_connected_hours(session):
    region = 'us-east-1'
    list_user_sessions = [1]
    workspace = {
        'WorkspaceProperties': {
            'RunningModeAutoStopTimeoutInMinutes': 60,
            'RunningMode': 'AUTO_STOP'
        }
    }
    metrics_helper = MetricsHelper(session, region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 2


def test_get_user_connected_hours_7(session):
    region = 'us-east-1'
    list_user_sessions = [1, 2]
    workspace = {
        'WorkspaceProperties': {
            'RunningModeAutoStopTimeoutInMinutes': 120,
            'RunningMode': 'AUTO_STOP'
        }
    }
    metrics_helper = MetricsHelper(session, region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 7


def test_get_user_connected_hours_0_hours(session):
    region = 'us-east-1'
    list_user_sessions = []
    workspace = {
        'WorkspaceProperties': {
            'RunningModeAutoStopTimeoutInMinutes': 120,
            'RunningMode': 'AUTO_STOP'
        }
    }
    metrics_helper = MetricsHelper(session, region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 0

@mock.patch(get_autostop_timeout_hours.__module__ + '.get_autostop_timeout_hours', return_value=1)
def test_get_user_connected_hours_0_hours_always_on(mock_get_autostop_timeout_hours, session):
    region = 'us-east-1'
    list_user_sessions = [1.0, 1.0, 1.0]
    workspace = {
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON'
        }
    }
    metrics_helper = MetricsHelper(session, region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 6


def test_get_list_user_session_data_points(session):
    region = 'us-east-1'
    list_metric_data_points = [
        {'Timestamp': datetime.datetime(2021, 5, 2, 1, 5, tzinfo=tzlocal()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 1, 10, tzinfo=tzlocal()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 20, 40, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 11, 50, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 12, 15, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 3, 25, tzinfo=tzlocal()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 23, 0, tzinfo=tzlocal()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 14, 10, tzinfo=tzlocal()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 9, 55, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 18, 5, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 13, 40, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 4, 50, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 0, 35, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 15, 45, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 11, 20, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 2, 55, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 17, 35, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 8, 45, tzinfo=tzlocal()), 'Maximum': 0.0, 'Unit': 'Count'}
    ]
    metrics_helper = MetricsHelper(session, region)
    result = metrics_helper.get_list_user_session_data_points(list_metric_data_points)
    assert result == [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0]


def test_get_list_time_ranges(session):
    region = 'us-east-1'
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-20T13:16:11Z'
    metrics_helper = MetricsHelper(session, region)
    result = metrics_helper.get_list_time_ranges(start_time, end_time)
    assert result == [
        {'end_time': '2021-05-06T00:00:00Z', 'start_time': '2021-05-01T00:00:00Z'},
        {'end_time': '2021-05-11T00:00:00Z', 'start_time': '2021-05-06T00:00:00Z'},
        {'end_time': '2021-05-16T00:00:00Z', 'start_time': '2021-05-11T00:00:00Z'},
        {'end_time': '2021-05-21T00:00:00Z', 'start_time': '2021-05-16T00:00:00Z'}
    ]


def test_get_cloudwatch_metric_data_points(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    client_stubber = Stubber(metrics_helper.client)
    workspace_id = '123qwer'
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-06T00:00:00Z'
    list_time_ranges = [
        {'end_time': '2021-05-06T00:00:00Z', 'start_time': '2021-05-01T00:00:00Z'}
    ]

    response = {
        'Label': 'UserConnected',
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
        'MetricName': 'UserConnected',
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 300,
        'Statistics': ['Maximum']
    }

    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    result = metrics_helper.get_cloudwatch_metric_data_points(workspace_id, list_time_ranges, "UserConnected")
    assert result == [
        {'Timestamp': datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
        {'Timestamp': datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'}
    ]


def test_get_cloudwatch_metric_data_points_empty_list(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    client_stubber = Stubber(metrics_helper.client)
    workspace_id = '123qwer'
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-06T00:00:00Z'
    list_time_ranges = [
        {'end_time': '2021-05-06T00:00:00Z', 'start_time': '2021-05-01T00:00:00Z'}
    ]

    response = {
        'Label': 'UserConnected',
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
        'MetricName': 'UserConnected',
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 300,
        'Statistics': ['Maximum']
    }

    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    result = metrics_helper.get_cloudwatch_metric_data_points(workspace_id, list_time_ranges, "UserConnected")
    assert result == []


def test_get_cloudwatch_metric_data_points_none(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    client_stubber = Stubber(metrics_helper.client)
    workspace_id = '123qwer'
    list_time_ranges = [
        {'end_time': '2021-05-06T00:00:00Z', 'start_time': '2021-05-01T00:00:00Z'}
    ]
    client_stubber.add_client_error('get_metric_statistics', 'InvalidRequest')
    client_stubber.activate()
    result = metrics_helper.get_cloudwatch_metric_data_points(workspace_id, list_time_ranges, "UserConnected")
    assert result is None


def test_get_billable_hours(mocker, session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-06T00:00:00Z'

    mocker.patch.object(metrics_helper, 'get_list_time_ranges')
    mocker.patch.object(metrics_helper, 'get_cloudwatch_metric_data_points')
    mocker.patch.object(metrics_helper, 'get_list_user_session_data_points')
    mocker.patch.object(metrics_helper, 'get_user_connected_hours')
    mocker.patch.object(metrics_helper, 'get_user_sessions')

    spy_get_list_time_ranges = mocker.spy(metrics_helper, 'get_list_time_ranges')
    spy_get_cloudwatch_metric_data_points = mocker.spy(metrics_helper, 'get_cloudwatch_metric_data_points')
    spy_get_list_user_session_data_points = mocker.spy(metrics_helper, 'get_list_user_session_data_points')
    spy_get_user_connected_hours = mocker.spy(metrics_helper, 'get_user_connected_hours')
    spy_get_user_sessions = mocker.spy(metrics_helper, 'get_user_sessions')

    metrics_helper.get_billable_hours(start_time, end_time, workspace)

    spy_get_list_time_ranges.assert_called_once()
    spy_get_cloudwatch_metric_data_points.assert_called_once()
    spy_get_list_user_session_data_points.assert_called_once()
    spy_get_user_connected_hours.assert_called_once()
    spy_get_user_sessions.assert_called_once()


def test_get_billable_hours_none(mocker, session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-06T00:00:00Z'

    mocker.patch.object(metrics_helper, 'get_list_time_ranges')
    mocker.patch.object(metrics_helper, 'get_cloudwatch_metric_data_points')
    metrics_helper.get_cloudwatch_metric_data_points.return_value = None
    mocker.patch.object(metrics_helper, 'get_list_user_session_data_points')
    mocker.patch.object(metrics_helper, 'get_user_connected_hours')
    mocker.patch.object(metrics_helper, 'get_user_sessions')

    spy_get_list_time_ranges = mocker.spy(metrics_helper, 'get_list_time_ranges')
    spy_get_cloudwatch_metric_data_points = mocker.spy(metrics_helper, 'get_cloudwatch_metric_data_points')
    spy_get_list_user_session_data_points = mocker.spy(metrics_helper, 'get_list_user_session_data_points')
    spy_get_user_connected_hours = mocker.spy(metrics_helper, 'get_user_connected_hours')
    spy_get_user_sessions = mocker.spy(metrics_helper, 'get_user_sessions')

    result = metrics_helper.get_billable_hours(start_time, end_time, workspace)

    spy_get_list_time_ranges.assert_called_once()
    spy_get_cloudwatch_metric_data_points.assert_called_once()
    spy_get_list_user_session_data_points.not_called()
    spy_get_user_connected_hours.not_called()
    spy_get_user_sessions.not_called()

    assert result is None


def test_get_user_sessions(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_1(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1, 1]


def test_get_user_sessions_2(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_3(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == []


def test_get_user_sessions_4(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1, 1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_5(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0, 0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == []


def test_get_user_sessions_6(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1, 0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_7(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0, 1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_8(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0, 1,0,0,0,0,0,0,0,0,0,0,0,0,1,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1,1]


def test_get_user_sessions_9(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0, 1,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1,1]


def test_get_user_sessions_10(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0, 1,0,0,0,0,0,0,0,0,0,0,0,1,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2]


def test_get_user_sessions_11(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_12(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == []


def test_get_user_sessions_13(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1,0,1,0,1,0,1,0,1,0,0,0,0,0,0,0,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_14(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [4]


def test_get_user_sessions_15(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2,1]


def test_get_user_sessions_16(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,1,1,1,1,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2,1,1]


def test_get_user_sessions_17(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2,1,3]


def test_get_user_sessions_18(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 60
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2,1,1,1]


def test_get_user_sessions_19(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 120
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [7]


def test_get_user_sessions_20(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 120
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2]


def test_get_user_sessions_21(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 120
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1,1]


def test_get_user_sessions_22(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 120
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [3]


def test_get_user_sessions_23(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 120
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [3,1]


def test_get_user_sessions_24(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 120
        }
    }

    list_user_session_data_points = [0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2,1]


def test_get_user_sessions_25(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 300
        }
    }

    list_user_session_data_points = [0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1,0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [4]


def test_get_user_sessions_26(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 300
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1]


def test_get_user_sessions_27(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 300
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [5]


def test_get_user_sessions_28(session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'Auto_Stop',
            'RunningModeAutoStopTimeoutInMinutes': 300
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1,1]

@mock.patch(get_autostop_timeout_hours.__module__ + '.get_autostop_timeout_hours', return_value=1)
def test_get_user_sessions_29(mock_get_autostop_timeout_hours, session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON'
        }
    }

    list_user_session_data_points = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1,1]

@mock.patch(get_autostop_timeout_hours.__module__ + '.get_autostop_timeout_hours', return_value=1)
def test_get_user_sessions_30(mock_get_autostop_timeout_hours, session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON'
        }
    }

    list_user_session_data_points = [1,0,0,1,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [1,1]

@mock.patch(get_autostop_timeout_hours.__module__ + '.get_autostop_timeout_hours', return_value=1)
def test_get_user_sessions_31(mock_get_autostop_timeout_hours, session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON'
        }
    }

    list_user_session_data_points = [1,0,0,1,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,
                                     0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [4]

@mock.patch(get_autostop_timeout_hours.__module__ + '.get_autostop_timeout_hours', return_value=1)
def test_get_user_sessions_32(mock_get_autostop_timeout_hours, session):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(session, region)
    workspace = {
        'WorkspaceId': '123qwer',
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON'
        }
    }

    list_user_session_data_points = [1,0,0,1,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,
                                     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
    result = metrics_helper.get_user_sessions(list_user_session_data_points, workspace)
    assert result == [2,1]
