import sys
sys.path.append('engine')
import datetime
from dateutil.tz import tzutc
from lib.metrics_helper import MetricsHelper
from botocore.stub import Stubber



def test_get_billable_time():
    settings = 'us-east-1'
    workspaceID = 'ws-abc1234XYZ'
    startTime = '2020-04-01T00:00:00Z'
    endTime = '2020-04-02T20:35:58Z'
    metrics_helper = MetricsHelper(settings)
    client_stubber = Stubber(metrics_helper.client)

    response = {
        'Label': 'UserConnected',
        'Datapoints': [
            {'Timestamp': datetime.datetime(2020, 4, 2, 11, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 1, 7, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 2, 6, 0, tzinfo=tzutc()), 'Maximum': 1.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 1, 2, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 2, 1, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'}
        ]
    }
    expected_params = {
        'Dimensions': [
            {
                'Name': 'WorkspaceId',
                'Value': workspaceID
            }
        ],
        'Namespace': 'AWS/WorkSpaces',
        'MetricName': 'UserConnected',
        'StartTime': startTime,
        'EndTime': endTime,
        'Period': 3600,
        'Statistics': ['Maximum']
    }

    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    billable_time = metrics_helper.get_billable_time(workspaceID, startTime, endTime)
    assert billable_time == 3


def test_get_billable_time_new_workspace():
    settings = 'us-east-1'
    workspaceID = 'ws-abc1234XYZ'
    startTime = '2020-04-01T00:00:00Z'
    endTime = '2020-04-02T20:35:58Z'
    metrics_helper = MetricsHelper(settings)
    client_stubber = Stubber(metrics_helper.client)

    response = {
        'Label': 'UserConnected',
        'Datapoints': [
            {'Timestamp': datetime.datetime(2020, 4, 2, 11, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 1, 7, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 2, 6, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 1, 2, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'},
            {'Timestamp': datetime.datetime(2020, 4, 2, 1, 0, tzinfo=tzutc()), 'Maximum': 0.0, 'Unit': 'Count'}
        ]
    }
    expected_params = {
        'Dimensions': [
            {
                'Name': 'WorkspaceId',
                'Value': workspaceID
            }
        ],
        'Namespace': 'AWS/WorkSpaces',
        'MetricName': 'UserConnected',
        'StartTime': startTime,
        'EndTime': endTime,
        'Period': 3600,
        'Statistics': ['Maximum']
    }

    client_stubber.add_response('get_metric_statistics', response, expected_params)
    client_stubber.activate()
    billable_time = metrics_helper.get_billable_time(workspaceID, startTime, endTime)
    assert billable_time == 0
