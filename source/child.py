#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#  Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
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
import calendar
import datetime
import json
import logging
import time
from urllib2 import Request
from urllib2 import urlopen
from lib.lambda_helper import LambdaHelper
from lib.wco_helper import WCOHelper
from lib.workspaces_helper import WorkspacesHelper

botoConfig = botocore.config.Config(max_pool_connections=100)

log = logging.getLogger()
log.setLevel(logging.INFO)

def lambda_handler(event, context):

    wcoHelper = WCOHelper()

    lastDay = calendar.monthrange(int(time.strftime('%Y')), int(time.strftime('%m')))[1]
    log.info("Current date = %s", time.strftime('%Y/%m/%d'))
    log.info("Last day of month = %s", lastDay)
    region = event['Region']

    stackOutputs = {}
    testEndOfMonth = False
    sendAnonymousData = False
    isDryRun = True

    # Get cached StackOutputs
    if 'StackOutputs' in event:
        stackOutputs = event['StackOutputs']

    # Get StackOutputs from CloudFormation
    else:
        stackName = context.invoked_function_arn.split(':')[6].rsplit('-', 2)[0]
        cfClient = boto3.client('cloudformation')
        response = cfClient.describe_stacks(StackName=stackName)
        for e in response['Stacks'][0]['Outputs']:
            stackOutputs[e['OutputKey']] = e['OutputValue']

    # Set log level
    log.setLevel(stackOutputs['LogLevel'])

    log.debug(stackOutputs)

    # Provide point to clean up parameter names in the future.

    if stackOutputs['DryRun'] == 'No':
        isDryRun = False

    # Determine if child function should run last-day-of-month routine.
    if (int(time.strftime('%d')) == lastDay):
        testEndOfMonth = True
        log.info('Last day of month, setting testEndOfMonth to %s', testEndOfMonth)

    # CloudFormation overrides the end of month testing
    if (stackOutputs['TestEndOfMonth'] == 'Yes'):
        testEndOfMonth = True
        log.info('Setting testEndOfMonth to %s due to CloudFormation stack parameters', testEndOfMonth)

    if stackOutputs['SendAnonymousData'] == 'true':
        log.debug('SendAnonymousData')
        sendAnonymousData = True

    log.debug('sendAnonymousData: %s', sendAnonymousData)

    childFunctionArn = stackOutputs['ChildFunctionArn']
    awsS3Bucket = stackOutputs['BucketName']
    maxRetries = 20

    # Capture any payload information passed to the function
    if 'DirectoryId' in event:
        directoryID = event['DirectoryId']
    else:
        return 'Error: No DirectoryID specified'

    endTime = event['EndTime']
    startTime = event['StartTime']
    lastDay = event['LastDay']
    runUUID = event['RunUUID']

    try: event['CSV']
    except: wsCsv = 'WorkspaceID,UserName,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode\n'
    else: wsCsv = event['CSV']

    try: event['NextToken']
    except: nextToken = 'None'
    else: nextToken = event['NextToken']

    workspacesHelper = WorkspacesHelper({
        'region': region,
        'hourlyLimits': {
            'VALUE': stackOutputs['ValueLimit'],
            'STANDARD': stackOutputs['StandardLimit'],
            'PERFORMANCE': stackOutputs['PerformanceLimit'],
            'GRAPHICS': stackOutputs['GraphicsLimit'],
            'POWER': stackOutputs['PowerLimit']
        },
        'testEndOfMonth': testEndOfMonth,
        'isDryRun': isDryRun,
        'startTime': startTime,
        'endTime': endTime
    })

    workspacesPage = workspacesHelper.get_workspaces_page(directoryID, nextToken)

    try: workspacesPage['NextToken']
    except: nextToken = 'None'
    else: nextToken = workspacesPage['NextToken']

    for workspace in workspacesPage['Workspaces']:
        result = workspacesHelper.process_workspace(workspace)

        # Append result data to the CSV
        wsCsv = wcoHelper.append_entry(wsCsv, result)

        if sendAnonymousData == True:
            postDict = {}
            postDict['Data'] = {
                'runUUID': runUUID,
                'result': result['optimizationResult'],
                'bundleType': result['bundleType'],
                'previousMode': result['initialMode']
            }
            postDict['TimeStamp'] = str(datetime.datetime.utcnow().isoformat())
            postDict['Solution'] = 'SO0018'
            postDict['UUID'] = stackOutputs['UUID']

            url = event['AnonymousDataEndpoint']
            data = json.dumps(postDict)

            log.debug('Sending anonymous data to endpoint %s', event['AnonymousDataEndpoint'])
            log.debug('%s', data)

            headers = {'content-type': 'application/json'}
            req = Request(url, data, headers)
            rsp = urlopen(req)
            content = rsp.read()
            rspcode = rsp.getcode()
            log.debug('Response Code: {}'.format(rspcode))
            log.debug('Response Content: {}'.format(content))

    if nextToken == 'None':
        log.debug('Last page, putting files in S3')
        pEndTime = time.strptime(endTime, '%Y-%m-%dT%H:%M:%SZ')
        s3Client = boto3.client('s3', config=botoConfig)

        logBody = wcoHelper.expand_csv(wsCsv)
        logKey = time.strftime('%Y/%m/%d/', pEndTime) + region + '_' + directoryID

        if testEndOfMonth:
            logKey += '_end-of-month'
        else:
            logKey += '_daily'

        if isDryRun:
            logKey += '_dry-run'

        logKey += '.csv'

        for i in range(0, maxRetries):
            log.debug('Try #%s to put files into S3', i)
            try:
                s3DailyPutResult = s3Client.put_object(
                    Bucket = awsS3Bucket,
                    Body = logBody,
                    Key = logKey
                )
                return 'Successfully uploaded log file to {!s}/{!s}'.format(awsS3Bucket, logKey)
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= maxRetries - 1: log.error('ExceededMaxRetries')
                else: time.sleep(i/10)
    else:
        # Invoke a child function to process paginated API results.
        lambdaHelper = LambdaHelper(childFunctionArn)
        lambdaHelper.invokeChildFunction(region, directoryID, startTime, endTime, lastDay, stackOutputs, runUUID, event['AnonymousDataEndpoint'], wsCsv, nextToken)
        return 'Another page of results was found, invoking the child function again.'
