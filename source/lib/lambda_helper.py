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
import json
import logging
import time

botoConfig = botocore.config.Config(max_pool_connections=100)

log = logging.getLogger()
log.setLevel(logging.INFO)

class LambdaHelper(object):
    def __init__(self, childFunctionArn):
        self.maxRetries = 20
        self.childFunctionArn = childFunctionArn
        return

    def invokeChildFunction(self, region, directoryID, startTime, endTime, lastDay, stackOutputs, runUUID, anonymousDataEndpoint, csv, nextToken):
        laClient = boto3.client('lambda', config=botoConfig)
        payload = {
            'Region': region,
            'DirectoryId': directoryID,
            'StartTime': startTime,
            'EndTime': endTime,
            'LastDay': lastDay,
            'StackOutputs': stackOutputs,
            'RunUUID': runUUID,
            'AnonymousDataEndpoint': anonymousDataEndpoint,
            'CSV': csv,
            'NextToken': nextToken
        }
        for i in range(0, self.maxRetries):
            try:
                laResponse = laClient.invoke(
                    FunctionName = self.childFunctionArn,
                    Payload = json.dumps(payload),
                    InvocationType = 'Event'
                )
                return laResponse
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= self.maxRetries - 1: log.error('ExceededMaxRetries')
                else: time.sleep(i/10)


