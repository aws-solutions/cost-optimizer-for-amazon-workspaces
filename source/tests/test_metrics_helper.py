import sys
from unittest import mock
import os
mock.patch.dict(os.environ, {'AutoStopTimeoutHours': '1'}).start()
sys.path.append('engine')
import datetime
from dateutil.tz import tzutc, tzlocal
from ecs.metrics_helper import MetricsHelper
from botocore.stub import Stubber



def test_get_user_connected_hours():
    region = 'us-east-1'
    list_user_sessions = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ]
    workspace = {
        'WorkspaceProperties': {
            'RunningModeAutoStopTimeoutInMinutes': 60,
            'RunningMode': 'AUTO_STOP'
        }
    }
    metrics_helper = MetricsHelper(region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 5


def test_get_user_connected_hours_7():
    region = 'us-east-1'
    list_user_sessions = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ]
    workspace = {
        'WorkspaceProperties': {
            'RunningModeAutoStopTimeoutInMinutes': 120,
            'RunningMode': 'AUTO_STOP'
        }
    }
    metrics_helper = MetricsHelper(region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 7


def test_get_user_connected_hours_0_hours():
    region = 'us-east-1'
    list_user_sessions = []
    workspace = {
        'WorkspaceProperties': {
            'RunningModeAutoStopTimeoutInMinutes': 120,
            'RunningMode': 'AUTO_STOP'
        }
    }
    metrics_helper = MetricsHelper(region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 0


def test_get_user_connected_hours_0_hours_always_on():
    region = 'us-east-1'
    list_user_sessions = [
        [1.0, 1.0, 1.0]
    ]
    workspace = {
        'WorkspaceProperties': {
            'RunningMode': 'ALWAYS_ON'
        }
    }
    metrics_helper = MetricsHelper(region)
    result = metrics_helper.get_user_connected_hours(list_user_sessions, workspace)
    assert result == 2


def test_get_list_user_session_data_points():
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
    metrics_helper = MetricsHelper(region)
    result = metrics_helper.get_list_user_session_data_points(list_metric_data_points)
    assert result == [[1.0], [1.0], [1.0, 1.0], [1.0]]


def test_get_list_time_ranges():
    region = 'us-east-1'
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-20T13:16:11Z'
    metrics_helper = MetricsHelper(region)
    result = metrics_helper.get_list_time_ranges(start_time, end_time)
    assert result == [
        {'end_time': '2021-05-06T00:00:00Z', 'start_time': '2021-05-01T00:00:00Z'},
        {'end_time': '2021-05-11T00:00:00Z', 'start_time': '2021-05-06T00:00:00Z'},
        {'end_time': '2021-05-16T00:00:00Z', 'start_time': '2021-05-11T00:00:00Z'},
        {'end_time': '2021-05-21T00:00:00Z', 'start_time': '2021-05-16T00:00:00Z'}
    ]


def test_get_cloudwatch_metric_data_points():
    region = 'us-east-1'
    metrics_helper = MetricsHelper(region)
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


def test_get_billable_hours(mocker):
    region = 'us-east-1'
    metrics_helper = MetricsHelper(region)
    workspace = {
        'WorkspaceId': '123qwer'
    }
    start_time = '2021-05-01T00:00:00Z'
    end_time = '2021-05-06T00:00:00Z'

    mocker.patch.object(metrics_helper, 'get_list_time_ranges')
    mocker.patch.object(metrics_helper, 'get_cloudwatch_metric_data_points')
    mocker.patch.object(metrics_helper, 'get_list_user_session_data_points')
    mocker.patch.object(metrics_helper, 'get_user_connected_hours')

    spy_get_list_time_ranges = mocker.spy(metrics_helper, 'get_list_time_ranges')
    spy_get_cloudwatch_metric_data_points = mocker.spy(metrics_helper, 'get_cloudwatch_metric_data_points')
    spy_get_list_user_session_data_points = mocker.spy(metrics_helper, 'get_list_user_session_data_points')
    spy_get_user_connected_hours = mocker.spy(metrics_helper, 'get_user_connected_hours')

    metrics_helper.get_billable_hours(start_time, end_time, workspace)

    #spy_get_list_time_ranges.assert_called_once()
    #spy_get_cloudwatch_metric_data_points.assert_called_twice()
    #spy_get_list_user_session_data_points.assert_called_once()
    #spy_get_user_connected_hours.assert_called_once()
