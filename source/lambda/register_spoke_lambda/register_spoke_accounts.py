# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
from register_spoke_lambda.dynamodb_table import DynamoDBTable
from register_spoke_lambda.request_event import RequestEvent


# Initialize log level
LOG_LEVEL = str(os.getenv('LOG_LEVEL', 'INFO'))
log = logging.getLogger()
log.setLevel(LOG_LEVEL)

DYNAMO_DB_TABLE_NAME = os.environ['DDB_TABLE_NAME']
STATUS_CODE_SUCCESS = 'Success'
STATUS_CODE_FAILED = 'Failed'
SUCCESS_MESSAGE = 'Successfully processed the request'
FAILED_MESSAGE = 'Error while processing the request'


def lambda_handler(event, context):
    """
    This lambda function is invoked by the lambda function in the spoke account. Based on the event type, the account
    will be registered or unregistered from the hub account.

    :param: event: event from spoke lambda function
    :param: context: lambda context
    :return: response object: success response message.
    """
    log.info("Executing Lambda handler")
    log.debug(f'Received payload: {event}')
    log.debug(f'Context for handler {context}')
    response = {
        'status': {
            'code': STATUS_CODE_SUCCESS,
            'message': SUCCESS_MESSAGE
        }
    }
    try:
        request_event = RequestEvent.from_json(event)
        dynamodb_table = DynamoDBTable(DYNAMO_DB_TABLE_NAME)
        if request_event.request_type == RequestEvent.RequestType.REGISTER.value:
            dynamodb_table.put_item(request_event.account_id, request_event.role_arn)
        elif request_event.request_type == RequestEvent.RequestType.UNREGISTER.value:
            dynamodb_table.delete_item(request_event.account_id, request_event.role_arn)
    except Exception as e:
        log.error(f'Following error occurred when registering spoke account for the request {event}: {e}')
        response.update({
            'status': {
                'code': STATUS_CODE_FAILED,
                'message': FAILED_MESSAGE,
                'error': str(e)
            }
        })

    return response
