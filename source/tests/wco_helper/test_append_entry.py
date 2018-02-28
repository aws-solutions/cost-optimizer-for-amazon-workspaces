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

from lib.wco_helper import WCOHelper

helper = WCOHelper()

# append_entry
def test_append_entry():
    csv = helper.append_entry('foo,bar,baz,biz,', {
        'workspaceID': 'ws-xxxxxxxxx',
        'billableTime': 0,
        'hourlyThreshold': 1,
        'optimizationResult': 'N',
        'newMode': 'ALWAYS_ON',
        'bundleType': 'VALUE',
        'initialMode': 'ALWAYS_ON'
    })

    assert csv == 'foo,bar,baz,biz,ws-xxxxxxxxx,0,1,N,VALUE,ALWAYS_ON,ALWAYS_ON\n'