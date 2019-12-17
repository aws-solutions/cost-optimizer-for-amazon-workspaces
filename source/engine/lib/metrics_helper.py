#!/usr/bin/python 
# -*- coding: utf-8 -*- 
######################################################################################################################
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# This file reads the AWS cloudwatch metrics for a given workspace
# This is where we will change the algorithm to determine billing preference

import boto3
import botocore
import logging
import time

botoConfig = botocore.config.Config(max_pool_connections=100)
wsClient = boto3.client('workspaces', config=botoConfig)

log = logging.getLogger()

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
                if runningMode == 'AUTO_STOP':
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
                        Statistics = ['Minimum']
                    )
                elif runningMode == 'ALWAYS_ON':
                    metrics = self.client.get_metric_statistics(
                        Dimensions = [{
                            'Name': 'WorkspaceId',
                            'Value': workspaceID
                        }],
                        Namespace = 'AWS/WorkSpaces',
                        MetricName = 'InSessionLatency',
                        StartTime = startTime,
                        EndTime = endTime,
                        Period = 3600,
                        Statistics = ['Maximum']
                    )
                log.debug(metrics)
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= self.maxRetries - 1: log.error('getMetricStatisticsError: ExceededMaxRetries')
                else: time.sleep(i/10)

        billableTime = 0
        log.info('METRICS for WS:%s:', workspaceID)
        if runningMode == 'AUTO_STOP':
            for metric in metrics['Datapoints']:
                if metric['Minimum'] == 0:
                    billableTime += 1
                    log.info('METRIC %d -> %s', billableTime, metric)
        else:
            for metric in metrics['Datapoints']:
                billableTime += 1
                log.info('METRIC %d -> %s', billableTime, metric)

        return int(billableTime)
