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
import time
from urllib2 import Request
from urllib2 import urlopen

botoConfig = botocore.config.Config(max_pool_connections=100)

# New client connections to AWS
workspacesClient = ''
cloudwatchClient = ''

def lambda_handler(event, context):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    botoConfig = botocore.config.Config(max_pool_connections=100)
    lastDay = calendar.monthrange(int(time.strftime('%Y')), int(time.strftime('%m')))[1]
   
    stackOutputs = {}
    testEndOfMonth = False
    sendAnonymousData = False

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
    isDryRun = stackOutputs['DryRun']

    # Determine if child function should run last-day-of-month routine.
    if (time.strftime('%d') == lastDay):
        testEndOfMonth = True
        log.debug('Last day of month, setting testEndOfMonth to %s', testEndOfMonth)

    # CloudFormation overrides the end of month testing
    if (stackOutputs['TestEndOfMonth'] == 'Yes'):
        testEndOfMonth = True
        log.debug('Setting testEndOfMonth to %s due to CloudFormation stack parameters', testEndOfMonth)

    if stackOutputs['SendAnonymousData'] == 'Yes':
        sendAnonymousData = True
    
    log.debug('sendAnonymousData: %s', sendAnonymousData)

    # Map conversion values
    hourlyLimits = {
        'VALUE': stackOutputs['ValueLimit'],
        'STANDARD': stackOutputs['StandardLimit'],
        'PERFORMANCE': stackOutputs['PerformanceLimit'],
        'GRAPHICS': stackOutputs['GraphicsLimit']
    }
    
    log.debug('ValueLimit: %s', hourlyLimits['VALUE'])
    log.debug('StandardLimit: %s', hourlyLimits['STANDARD'])
    log.debug('PerformanceLimit: %s', hourlyLimits['PERFORMANCE'])
    log.debug('GraphicsLimit: %s', hourlyLimits['GRAPHICS'])

    childFunctionArn = stackOutputs['ChildFunctionArn']
    awsS3Bucket = stackOutputs['BucketName']
    maxRetries = 20

    # Capture any payload information passed to the function
    if 'DirectoryId' in event:
        directoryID = event['DirectoryId']
    else:
        return 'Error: No DirectoryID specified'

    workspaceRegion = event['Region']
    endTime = event['EndTime']
    startTime = event['StartTime']
    lastDay = event['LastDay']
    runUUID = event['RunUUID']
    
    try: event['CSV']
    except: wsCsv = ''
    else: wsCsv = event['CSV']

    try: event['NextToken']
    except: nextToken = 'None'
    else: nextToken = event['NextToken']
    
    wsClient = boto3.client('workspaces', region_name=workspaceRegion, config=botoConfig)
    cwClient = boto3.client('cloudwatch', region_name=workspaceRegion, config=botoConfig)
    if nextToken == 'None':
        describeWorkspaces = wsClient.describe_workspaces(DirectoryId = directoryID)
    else:
        describeWorkspaces = wsClient.describe_workspaces(DirectoryId = directoryID, NextToken = nextToken)

    try: describeWorkspaces['NextToken']
    except: nextToken = 'None'
    else: nextToken = describeWorkspaces['NextToken']
    
    for workspace in describeWorkspaces['Workspaces']:
        workspaceID = workspace['WorkspaceId']
        log.debug('workspaceID: %s', workspaceID)

        workspaceBundleType = wsClient.describe_workspace_bundles(BundleIds = [workspace['BundleId']])['Bundles'][0]['ComputeType']['Name']
        log.debug('workspaceBundleType: %s', workspaceBundleType)

        workspaceRunningMode = workspace['WorkspaceProperties']['RunningMode']
        log.debug('workspaceRunningMode: %s', workspaceRunningMode)

        wsResult = ''
        wsBillable = ''

        for i in range(0, maxRetries):
            try:
                workspaceTags = wsClient.describe_tags(ResourceId=workspaceID)
                log.debug(workspaceTags)
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= maxRetries - 1: log.error('ExceededMaxRetries')
                else: time.sleep(i/10)

        # Check for Skip_Convert tag
        SkipConvert = False
        for tagPair in workspaceTags['TagList']:
            if tagPair['Key'] == 'Skip_Convert':
                SkipConvert = True
                log.info('Skipping WorkSpace %s due to Skip_Convert tag', workspaceID)
                wsResult = 'S'

        if SkipConvert == False:

            # If the Workspace is in Auto Stop
            if workspaceRunningMode == 'AUTO_STOP':
                billableTime = 0

                # Get metrics from CloudWatch
                for i in range(0, maxRetries):
                    log.debug('getMetricStatistics')
                    try:
                        metrics = cwClient.get_metric_statistics(
                            Dimensions = [ {
                                'Name': 'WorkspaceId',
                                'Value': workspaceID
                            } ],
                            Namespace = 'AWS/WorkSpaces',
                            MetricName = 'Stopped',
                            StartTime = startTime,
                            EndTime = endTime,
                            Period = 3600,
                            Statistics = ['Minimum']
                        )
                        break
                    except botocore.exceptions.ClientError as e:
                        log.error(e)
                        if i >= maxRetries - 1: log.error('getMetricStatisticsError: ExceededMaxRetries')
                        else: time.sleep(i/10)
            
                for metric in metrics['Datapoints']:
                    if metric['Minimum'] == 0:
                        billableTime += 1
            
                # If billable time is over the threshold for this bundle type
                if billableTime > hourlyLimits[workspaceBundleType]:
                    log.info('Attempting to change RunningMode to ALWAYS_ON')
                    
                    for i in range(0, maxRetries):
                        log.debug('modifyWorkspaceProperties')
                        try:
                            if isDryRun == False:
                                wsModWS = wsClient.modify_workspace_properties(
                                    WorkspaceId = workspaceID,
                                    WorkspaceProperties = { 'RunningMode': 'ALWAYS_ON' }
                                )
                            else:
                                log.info('Skipping modifyWorkspaceProperties for Workspace %s due to dry run', workspaceID)

                            wsResult = 'M'
                            wsBillable = str(billableTime)
                            break
                        except botocore.exeptions.ClientError as e:
                            if i >= maxRetries - 1:
                                wsResult = 'E'
                            else:
                                time.sleep(i/10)

                # Otherwise, report no change for the Workspace
                else:
                    wsResult = 'N'
                    wsBillable = str(billableTime)

            # Otherwise, the Workspace is Always On.
            else:

                # Only perform metrics gathering for ALWAYS_ON Workspaces at the end of the month.
                if testEndOfMonth == True:
                    billableArray = {}

                    # Get metrics from CloudWatch
                    for i in range(0, maxRetries):
                        log.debug('getMetricStatistics')
                        try:
                            metrics = cwClient.get_metric_statistics(
                                Dimensions = [
                                    {
                                        'Name': 'WorkspaceId',
                                        'Value': workspaceID
                                    }
                                ],
                                Namespace = 'AWS/WorkSpaces',
                                MetricName = 'UserConnected',
                                StartTime = startTime,
                                EndTime = endTime,
                                Period = 3600,
                                Statistics = ['Maximum']
                            )
                            break
                        except botocore.exceptions.ClientError as e:
                            log.error(e)
                            if i >= maxRetries - 1: log.error('ExceededMaxRetries')
                            else: time.sleep(i/10)
            
                    for metric in metrics['Datapoints']:
                        if metric['Maximum'] == 1:
                            metricTime = metric['Timestamp']
                            wsTime = str('{:0>2}'.format(metricTime.day)) + str('{:0>2}'.format(metricTime.hour))
                            billableArray[wsTime] = 1
                        
                            wsTimeNext = 0
                            if metricTime.hour == 23: wsTimeNext = str('{:0>2}'.format(metricTime.day+1)) + '00'
                            else: wsTimeNext = str(int(wsTime) + 1)

                            billableArray[wsTimeNext] = 1

                    if len(billableArray) < hourlyLimits[workspaceBundleType]:
                        log.info('Attempting to change RunningMode to AUTO_STOP')
                        
                        for i in range(0, maxRetries):
                            log.debug('modifyWorkspaceProperties')
                            try:
                                if isDryRun == False:
                                    wsModWS = wsClient.modify_workspace_properties(
                                        WorkspaceId = workspaceID,
                                        WorkspaceProperties = { 'RunningMode': 'AUTO_STOP' }
                                    )
                                else:
                                    log.info('Skipping modifyWorkspaceProperties for Workspace %s due to dry run', workspaceID)

                                wsResult = 'H'
                                wsBillable = str(len(billableArray))
                                break
                            except botocore.exceptions.ClientError as e:
                                log.error(e)
                                if i >= maxRetries - 1:
                                    wsResult = 'E'
                                else: time.sleep(i/10)

                    else:
                        log.info('Monthly usage is not below the threshold to switch to hourly, no changes will be made')
                        wsResult = 'N'
                        wsBillable = str(len(billableArray))

                else:
                    log.info('testEndOfMonth is False, skipping metrics gathering')
                    wsResult = 'N'

        wsCsv += workspaceID + ',' + wsBillable + ',' + wsResult

        if sendAnonymousData == True:
            postDict = {}
            postDict['Data'] = {
                'runUUID': runUUID,
                'result': wsResult,
                'bundleType': workspaceBundleType,
                'previousMode': workspaceRunningMode
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

        for i in range(0, maxRetries):
            log.debug('Try #%s to put files into S3', i)
            try:

                body = wsCsv.replace(',M', ',ToMonthly\n').replace(',H', ',ToHourly\n').replace(',E', ',Exceeded MaxRetries\n').replace(',N', ',No Change\n').replace(',S', ',Skipped\n')

                s3DailyPutResult = s3Client.put_object(
                    Bucket = awsS3Bucket,
                    Body = body,
                    Key = time.strftime('%Y/%m/%d/', pEndTime) + workspaceRegion + '_' + directoryID + '_' + time.strftime('%H%M%S.csv', pEndTime)
                )
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= maxRetries - 1: log.error('ExceededMaxRetries')
                else: time.sleep(i/10)
    else:
        laClient = boto3.client('lambda', config=botoConfig)
        payload = {
            'Region': workspaceRegion,
            'DirectoryId': directoryID,
            'EndTime': endTime,
            'NextToken': nextToken,
            'CSV': wsCsv,
            'StartTime': startTime,
            'LastDay': lastDay,
            'StackOutputs': stackOutputs,
            'RunUUID': runUUID,
            'AnonymousDataEndpoint': event['AnonymousDataEndpoint']
        }
        for i in range(0, maxRetries):
            try:
                laResponse = laClient.invoke(
                    FunctionName = childFunctionArn,
                    Payload = json.dumps(payload),
                    InvocationType = 'Event'
                )
                break
            except botocore.exceptions.ClientError as e:
                log.error(e)
                if i >= maxRetries - 1: log.error('ExceededMaxRetries')
                else: time.sleep(i/10)