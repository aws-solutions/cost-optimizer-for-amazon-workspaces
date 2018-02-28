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

import logging

log = logging.getLogger()
log.setLevel(logging.INFO)

class WCOHelper(object):
    def __init__(self):
        return

    '''
    returns str
    '''
    def append_entry(self, oldCsv, result):
        s = ','
        csv = oldCsv + s.join((
            result['workspaceID'],
            str(result['billableTime']),
            str(result['hourlyThreshold']),
            result['optimizationResult'],
            result['bundleType'],
            result['initialMode'],
            result['newMode'] + '\n'
        ))

        return csv

    '''
    returns str
    '''
    def expand_csv(self, rawCSV):
        csv = rawCSV.replace(',-M-', ',ToMonthly').replace(',-H-', ',ToHourly').replace(',-E-', ',Exceeded MaxRetries').replace(',-N-', ',No Change').replace(',-S-', ',Skipped')
        return csv