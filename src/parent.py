#  Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           
#
#  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://aws.amazon.com/asl/
#
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import boto3
import botocore
import calendar
import datetime
import json
import logging
import threading
import time
import uuid
from urllib2 import Request
from urllib2 import urlopen

def lambda_handler(event, context):

    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    endTime = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    startTime = time.strftime("%Y-%m") + '-01T00:00:00Z'
    lastDay = calendar.monthrange(int(time.strftime("%Y")), int(time.strftime("%m")))[1]
    stackOutputs = {}
    maxRetries = 20
    sendAnonymousData = False
        
    runUUID = str(uuid.uuid4())
    anonymousDataEndpoint = 'https://metrics.awssolutionsbuilder.com/generic'
    regionCount = 0;
    directoryCount = 0;

    # Get StackOutputs from CloudFormation
    stackName = context.invoked_function_arn.split(':')[6].rsplit('-', 2)[0]
    cfClient = boto3.client('cloudformation')
    response = cfClient.describe_stacks(StackName=stackName)
    for e in response['Stacks'][0]['Outputs']:
        stackOutputs[e['OutputKey']] = e['OutputValue']

    # Set log level
    log.setLevel(stackOutputs['LogLevel'])

    log.debug(stackOutputs)

    if (stackOutputs['SendAnonymousData'] == 'Yes'):
        sendAnonymousData = True
        log.debug('Setting sendAnonymousData to %s due to CloudFormation stack parameters', sendAnonymousData)

    childFunctionArn = stackOutputs['ChildFunctionArn']
    laClient = boto3.client('lambda')
    
    # Get all WorkSpaces regions
    for i in range(0, maxRetries):
        log.debug('Try #%s to get_regions for WorkSpaces', i)
        try:
            wsRegions = boto3.session.Session().get_available_regions('workspaces')
            break
        except botocore.exceptions.ClientError as e:
            log.error(e)
            if i >= maxRetries - 1: log.error('Error processing get_regions for WorkSpaces: ExceededMaxRetries')
            else: time.sleep(i/10)

    # For each region
    for wsRegion in wsRegions:

        regionCount += 1

        # Create a WS Client
        wsClient = boto3.client('workspaces', region_name=wsRegion)

        log.debug('Describing WorkSpace Directories')
        for i in range(0, maxRetries):
            log.debug('Try #%s to get list of directories', i)

            # Get each Directory within the region
            try:
                directories = wsClient.describe_workspace_directories()
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= maxRetries - 1: log.error('describe_workspace_directories ExceededMaxRetries')
                else: time.sleep(i/10)

        # For each directory
        for directory in directories["Directories"]:

            directoryCount += 1

            payload = {
                "DirectoryId": directory["DirectoryId"],
                "Region": wsRegion,
                "EndTime": endTime,
                "StartTime": startTime,
                "LastDay": str(lastDay),
                "StackOutputs": stackOutputs,
                "RunUUID": runUUID,
                "AnonymousDataEndpoint": anonymousDataEndpoint
            }

            for i in range(0, maxRetries):
                log.debug('Try #%s to call Lambda child function', i)
                
                # Invoke the child lambda for each directory in the region
                try:
                    laResponse = laClient.invoke(
                        FunctionName = childFunctionArn,
                        Payload = json.dumps(payload),
                        InvocationType = "Event"
                    )
                    break
                except botocore.exceptions.ClientError as e:
                    log.error(e)
                    if i >= maxRetries - 1: log.error('Error processing Lambda for Directory ID %s: ExceededMaxRetries', directory["DirectoryId"])
                    else: time.sleep(i/10)

    if sendAnonymousData == True:
        postDict = {}
        postDict['Data'] = {
            'runUUID': runUUID
        }
        postDict['TimeStamp'] = str(datetime.datetime.utcnow().isoformat())
        postDict['Solution'] = 'SO0018'
        postDict['UUID'] = stackOutputs['UUID']

        url = anonymousDataEndpoint
        data = json.dumps(postDict)
        headers = {'content-type': 'application/json'}
        req = Request(url, data, headers)
        rsp = urlopen(req)
        content = rsp.read()
        rspcode = rsp.getcode()
        log.debug('Response Code: {}'.format(rspcode))
        log.debug('Response Content: {}'.format(content))

    return 'Successfully invoked Child function for {!s} directories across {!s} regions.'.format(directoryCount, regionCount)