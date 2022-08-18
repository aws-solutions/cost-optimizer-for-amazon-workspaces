#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import urllib3
import logging
import json

logger = logging.getLogger(__name__)

SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()


def send(event, context, response_status, response_data, physical_resource_id=None, no_echo=False, reason=None):
    response_url = event['ResponseURL']

    logger.info(response_url)

    response_body = {
        'Status': response_status,
        'Reason': reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId': physical_resource_id or context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'NoEcho': no_echo,
        'Data': response_data
    }

    json_response_body = json.dumps(response_body)

    logger.info("Response body:")
    logger.info(json_response_body)

    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    try:
        response = http.request('PUT', response_url, headers=headers, body=json_response_body)
        logger.info(f"Status code: {str(response.status)}")
    except Exception as e:
        logger.error(f"send(..) failed executing http.request(..): {str(e)}")
