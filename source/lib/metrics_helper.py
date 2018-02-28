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

import boto3
import botocore
import logging
import time

botoConfig = botocore.config.Config(max_pool_connections=100)
wsClient = boto3.client('workspaces', config=botoConfig)

log = logging.getLogger()
log.setLevel(logging.INFO)

class MetricsHelper(object):

    def __init__(self, region):
        self.maxRetries = 20
        self.region = region
        self.client = boto3.client('cloudwatch', region_name=self.region, config=botoConfig)
        return

    '''
    returns int
    '''
    def get_billable_time(self, workspaceID, runningMode, startTime, endTime):
        for i in range(0, self.maxRetries):
            log.debug('getMetricStatistics')
            try:
                metrics = self.client.get_metric_statistics(
                    Dimensions = [{
                        'Name': 'WorkspaceId',
                        'Value': workspaceID
                    }],
                    Namespace = 'AWS/WorkSpaces',
                    MetricName = 'Stopped',
                    StartTime = startTime,
                    EndTime = endTime,
                    Period = 3600,
                    Statistics = ['Minimum', 'Maximum']
                )
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= self.maxRetries - 1: log.error('getMetricStatisticsError: ExceededMaxRetries')
                else: time.sleep(i/10)

        if runningMode == 'AUTO_STOP':
            billableTime = 0
            for metric in metrics['Datapoints']:
                if metric['Minimum'] == 0:
                    billableTime += 1
            return int(billableTime)
        elif runningMode == 'ALWAYS_ON':
            billableArray = {}
            for metric in metrics['Datapoints']:
                if metric['Maximum'] == 1:
                    metricTime = metric['Timestamp']
                    wsTime = str('{:0>2}'.format(metricTime.day)) + str('{:0>2}'.format(metricTime.hour))
                    billableArray[wsTime] = 1
                
                    wsTimeNext = 0
                    if metricTime.hour == 23: wsTimeNext = str('{:0>2}'.format(metricTime.day+1)) + '00'
                    else: wsTimeNext = str(int(wsTime) + 1)

                    billableArray[wsTimeNext] = 1
            return len(billableArray)       
