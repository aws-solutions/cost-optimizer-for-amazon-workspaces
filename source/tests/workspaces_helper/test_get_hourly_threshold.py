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
        'STANDARD': '10',
        'PERFORMANCE': 5,
        'GRAPHICS': 5
    },
    'testEndOfMonth': False,
    'isDryRun': True,
    'startTime': '2018-02-01T00:00:00Z',
    'endTime': '2018-02-01T12:00:00Z'
})

# AUTO_STOP (paid hourly)
def test_get_hourly_threshold_int():
    result = helper.get_hourly_threshold('VALUE')
    assert type(result) is int
    assert result == 5

def test_get_hourly_threshold_str():
    result = helper.get_hourly_threshold('STANDARD')
    assert type(result) is int
    assert result == 10

def test_get_hourly_threshold_int():
    result = helper.get_hourly_threshold('DOES_NOT_EXIST')
    assert result == None