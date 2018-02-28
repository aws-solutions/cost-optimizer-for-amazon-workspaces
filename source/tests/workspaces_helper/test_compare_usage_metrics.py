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

from lib.workspaces_helper import WorkspacesHelper

helper = WorkspacesHelper({
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

endOfMonthHelper = WorkspacesHelper({
    'region': 'us-west-2',
    'hourlyLimits': {
        'VALUE': 5,
        'STANDARD': 5,
        'PERFORMANCE': 5,
        'GRAPHICS': 5
    },
    'testEndOfMonth': True,
    'isDryRun': True,
    'startTime': '2018-02-01T00:00:00Z',
    'endTime': '2018-02-01T12:00:00Z'
})

# ALWAYS_ON (paid monthly)
def test_compare_usage_metrics_always_on_under_threshold():
    result = endOfMonthHelper.compare_usage_metrics('ws-xxxxxxxxx', 1, 5, 'ALWAYS_ON')
    assert result['resultCode'] == '-H-'

def test_compare_usage_metrics_always_on_over_threshold():
    result = endOfMonthHelper.compare_usage_metrics('ws-xxxxxxxxx', 10, 5, 'ALWAYS_ON')
    assert result['resultCode'] == '-N-'

# AUTO_STOP (paid hourly)
def test_compare_usage_metrics_auto_stop_under_threshold():
    result = helper.compare_usage_metrics('ws-xxxxxxxxx', 1, 5, 'AUTO_STOP')
    assert result['resultCode'] == '-N-'

def test_compare_usage_metrics_auto_stop_over_threshold():
    result = helper.compare_usage_metrics('ws-xxxxxxxxx', 10, 5, 'AUTO_STOP')
    assert result['resultCode'] == '-M-'

def test_compare_usage_metrics_no_threshold():
    result = helper.compare_usage_metrics('ws-xxxxxxxxx', 10, None, 'AUTO_STOP')
    assert result['resultCode'] == '-S-'