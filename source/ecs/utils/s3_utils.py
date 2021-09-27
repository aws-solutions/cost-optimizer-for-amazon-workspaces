# !/usr/bin/python
# -*- coding: utf-8 -*-
######################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
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
import boto3
import logging
import botocore
import os
import sys
import time
from botocore.config import Config
from botocore.exceptions import ClientError


# Set default logging level
logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', level=logging.INFO)
log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)

# Setting the boto config
boto_config = Config(
    retries={
        'max_attempts': 20,
        'mode': 'standard'
    },
    user_agent_extra=os.getenv('UserAgentString')
)

# create s3 client
s3_client = boto3.client('s3', config=boto_config)

# set the end time
end_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def upload_report(stack_parameters, report_body, directory_id=None, directory_region=None):
    """
    :param directory_region: Region for the directory
    :param directory_id: ID for the directory
    :param report_body: body of the report
    :param stack_parameters: parameters for the stack
    This method uploads the workspace report to the cost optimizer bucket.
    """
    log.debug("Uploading the csv report to s3 bucket.")
    s3_key = create_s3_key(stack_parameters, directory_id, directory_region)
    bucket_name = stack_parameters['BucketName']
    s3_put_report(bucket_name, report_body, s3_key)
    log.debug('Successfully uploaded csv file to %s', s3_key)


def create_s3_key(stack_parameters, directory_id, directory_region):
    """
    :param: stack_parameters: parameters for the stack
    :param: directory_id: ID for the directory
    :param: Region for the directory
    This method creates the s3 key for the report.
    """
    log.debug("Creating s3 key for report")
    report_time = time.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ')
    if directory_id:
        s3_key = time.strftime('%Y/%m/%d/', report_time) + directory_region + '_' + directory_id
    else:
        s3_key = time.strftime('%Y/%m/%d/', report_time) + 'aggregated'
    if stack_parameters['DryRun'] == 'Yes':
        s3_key += '_dry-run'
    if stack_parameters['TestEndOfMonth'] == 'Yes':
        s3_key += '_end-of-month'
    else:
        s3_key += '_daily'
    s3_key += '.csv'
    log.debug("Returning s3 key as {}".format(s3_key))

    return s3_key


def s3_put_report(bucket_name, report_body, s3_key):
    """
    :param: bucket_name: Name of the bucket to upload report
    :param: report_body: body of the report
    :param: s3_key: key for the s3 report
    This method puts report to s3 bucket
    """
    log.debug("Putting report to s3 bucket {} with key: {}".format(bucket_name, s3_key))
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Body=report_body,
            Key=s3_key
        )
        log.debug("Successfully uploaded the report to s3 bucket {} with key: {}".format(bucket_name, s3_key))
    except botocore.exceptions.ClientError as e:
        log.error("Exception occurred while uploading the report to s3 bucket. Error {}".format(e))


