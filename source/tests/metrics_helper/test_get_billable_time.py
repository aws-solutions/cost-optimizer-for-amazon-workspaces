#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
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

import datetime

from lib.metrics_helper import MetricsHelper

startTime = '2018-02-01T00:00:00Z'
endTime = '2018-02-01T12:00:00Z'
timeStamp = datetime.datetime(2018, 2, 2, 16, 0)

def test_auto_stop(monkeypatch):
    metricsHelper = MetricsHelper('us-west-2')
    def mock_get_metric_statistics(
        Dimensions = [{
            'Name': 'WorkspaceId',
            'Value': 'ws-xxxxxxxxx'
        }],
        Namespace = 'AWS/WorkSpaces',
        MetricName = 'Stopped',
        StartTime = startTime,
        EndTime = endTime,
        Period = 3600,
        Statistics = ['Minimum', 'Maximum']
    ):
        return {
            'Datapoints': [
                {
                    'Timestamp': timeStamp, 
                    'Minimum': 0.0, 
                    'Unit': 'Count'
                },
                {
                    'Timestamp': timeStamp, 
                    'Minimum': 0.0, 
                    'Unit': 'Count'
                }
            ],
                'ResponseMetadata': {
                    'HTTPStatusCode': 200
                }
            }

    monkeypatch.setattr(metricsHelper.client, 'get_metric_statistics', mock_get_metric_statistics)

    billableTime = metricsHelper.get_billable_time('ws-xxxxxxxxx', 'AUTO_STOP', startTime, endTime)
    assert type(billableTime) is int
    assert billableTime == 2

def test_auto_stop_nonzero(monkeypatch):
    metricsHelper = MetricsHelper('us-west-2')
    def mock_get_metric_statistics(
        Dimensions = [{
            'Name': 'WorkspaceId',
            'Value': 'ws-xxxxxxxxx'
        }],
        Namespace = 'AWS/WorkSpaces',
        MetricName = 'Stopped',
        StartTime = startTime,
        EndTime = endTime,
        Period = 3600,
        Statistics = ['Minimum', 'Maximum']
    ):
        return {
            'Datapoints': [
                {
                    'Timestamp': timeStamp, 
                    'Minimum': 0.0, 
                    'Unit': 'Count'
                },
                {
                    'Timestamp': timeStamp, 
                    'Minimum': 1.0, 
                    'Unit': 'Count'
                }
            ],
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }

    monkeypatch.setattr(metricsHelper.client, 'get_metric_statistics', mock_get_metric_statistics)

    billableTime = metricsHelper.get_billable_time('ws-xxxxxxxxx', 'AUTO_STOP', startTime, endTime)
    assert type(billableTime) is int
    assert billableTime != 2

def test_always_on(monkeypatch):
    metricsHelper = MetricsHelper('us-west-2')
    def mock_get_metric_statistics(
        Dimensions = [{
            'Name': 'WorkspaceId',
            'Value': 'ws-xxxxxxxxx'
        }],
        Namespace = 'AWS/WorkSpaces',
        MetricName = 'Stopped',
        StartTime = startTime,
        EndTime = endTime,
        Period = 3600,
        Statistics = ['Minimum', 'Maximum']
    ):
        return {
            'Datapoints': [
                {
                    'Timestamp': timeStamp, 
                    'Maximum': 1.0, 
                    'Unit': 'Count'
                },
                {
                    'Timestamp': timeStamp, 
                    'Maximum': 1.0, 
                    'Unit': 'Count'
                }
            ],
            'ResponseMetadata': {
                'HTTPStatusCode': 200
            }
        }

    monkeypatch.setattr(metricsHelper.client, 'get_metric_statistics', mock_get_metric_statistics)

    billableTime = metricsHelper.get_billable_time('ws-xxxxxxxxx', 'ALWAYS_ON', startTime, endTime)
    assert type(billableTime) is int
    assert billableTime == 2
