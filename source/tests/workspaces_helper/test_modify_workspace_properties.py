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

# modify_workspace_properties
def test_modify_workspace_properties_always_on():
    result = helper.modify_workspace_properties('ws-xxxxxxxxx', 'ALWAYS_ON', True)
    assert type(result) is str
    assert result == '-M-'

def test_modify_workspace_properties_auto_stop():
    result = helper.modify_workspace_properties('ws-xxxxxxxxx', 'AUTO_STOP', True)
    assert type(result) is str
    assert result == '-H-'
