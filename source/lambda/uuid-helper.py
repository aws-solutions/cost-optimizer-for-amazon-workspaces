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

# uuid-helper.py
# This code generates a uuid using the uuid random tool
import json
import uuid
import requests
import logging
import os

log = logging.getLogger()
LOG_LEVEL = str(os.getenv('LogLevel', 'INFO'))
log.setLevel(LOG_LEVEL)


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False): 
    try: 
        responseUrl = event.get('ResponseURL') 
         
        responseBody = { 
            "Status":responseStatus, 
            "Reason": "See the details in CloudWatch Log Stream: " + context.log_stream_name, 
            "PhysicalResourceId": physicalResourceId or context.log_stream_name, 
            "StackId": event.get('StackId'), 
            "RequestId":event.get('RequestId'), 
            "LogicalResourceId": event.get('LogicalResourceId'), 
            "NoEcho": noEcho, 
            "Data": responseData 
        } 
         
        data = json.dumps(responseBody) 
         
        headers = { 
            'content-type' : '', 
            'content-length' : str(len(data)) 
        } 
 
        response = requests.put(responseUrl,data=data,headers=headers) 
        log.debug("CFN Status: " + str(response.status_code))
        response.raise_for_status() 
     
    except Exception as e: 
        raise(e) 


def lambda_handler(event, context): 
    try: 
        request = event.get('RequestType') 
        responseData = {} 
 
        if request == 'Create': 
            responseData = {'UUID': str(uuid.uuid4())}
            log.debug(" UUID: {}".format(responseData))

        send(event, context, 'SUCCESS', responseData) 
 
    except Exception as e: 
        log.error('Exception: {}'.format(e))
        send(event, context, 'FAILED', {}, context.log_stream_name) 
