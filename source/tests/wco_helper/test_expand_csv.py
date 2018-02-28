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

# expand_csv
def test_expand_csv_expand_to_monthly():
    body = helper.expand_csv('ws-xxxxxxxxx,0,-M-')
    assert body == 'ws-xxxxxxxxx,0,ToMonthly'

def test_expand_csv_expand_to_hourly():
    body = helper.expand_csv('ws-xxxxxxxxx,0,-H-')
    assert body == 'ws-xxxxxxxxx,0,ToHourly'

def test_expand_csv_expand_exceeded_max_retries():
    body = helper.expand_csv('ws-xxxxxxxxx,0,-E-')
    assert body == 'ws-xxxxxxxxx,0,Exceeded MaxRetries'

def test_expand_csv_expand_no_change():
    body = helper.expand_csv('ws-xxxxxxxxx,0,-N-')
    assert body == 'ws-xxxxxxxxx,0,No Change'

def test_expand_csv_expand_skipped():
    body = helper.expand_csv('ws-xxxxxxxxx,0,-S-')
    assert body == 'ws-xxxxxxxxx,0,Skipped'