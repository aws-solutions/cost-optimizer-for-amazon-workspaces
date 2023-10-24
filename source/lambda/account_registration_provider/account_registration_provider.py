#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import cfnresponse
import boto3
import botocore
import logging
import json
import os
import sys

logger = logging.getLogger(__name__)
log_level = getattr(logging, str(os.getenv('LOG_LEVEL', 'INFO')))
logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', level=log_level)  # NOSONAR

boto_config = botocore.config.Config(
    retries={
        'total_max_attempts': 10,
        'mode': 'adaptive'
    },
    user_agent_extra=os.getenv('USER_AGENT_STRING', 'Unknown'))


def invoke_register_lambda(request_type: str):
    account_id = boto3.client('sts', config=boto_config).get_caller_identity().get('Account')
    payload = {
        'account_id': account_id,
        'request_type': request_type,
        'role_arn': os.environ.get('MANAGEMENT_ROLE_ARN')
    }
    return boto3.client('lambda', config=boto_config).invoke(
        FunctionName=os.environ.get('REGISTER_LAMBDA_ARN'),
        Payload=json.dumps(payload),
        InvocationType='RequestResponse'
    )


def event_handler(event, context):
    response_data = {}
    try:
        request_type = event['RequestType']
        if (request_type == 'Create' or request_type == 'Update'):
            register_request_type = 'Register'
        elif (request_type == 'Delete'):
            register_request_type = 'Unregister'
        else:
            raise ValueError(f'Unknown request type: {request_type}')

        response_data = invoke_register_lambda(register_request_type)
        logger.debug(f"Response from the hub account is {response_data}")
        if (response_data.get('Payload')):
            max_bytes = 3854
            try:
                response_data['Payload'] = json.loads(response_data['Payload'].read(amt=max_bytes).decode('utf-8'))
            except Exception as e:
                response_data['Payload'] = f"Unable to serialize response body: {e.__class__.__name__}: {str(e)}"
            # Under normal circumstances, we will get a 200 response even if registration failed. Check the payload.
            if (response_data['Payload'].get('status', {}).get('code', 'Failed') != 'Success'):
                raise RuntimeError('Registering spoke account failed')
        # Also check that the call succeeded
        if (response_data.get('StatusCode') != 200 or response_data.get('FunctionError')):
            raise RuntimeError('Error invoking register lambda')

        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
    except Exception as e:
        reason = f'An exception occurred:\n{e.__class__.__name__}: {str(e)}'
        logger.error(reason)
        max_reason_length = 3854  # response can't exceed 4 kiB
        truncated_reason = reason[:max_reason_length] if len(reason) > max_reason_length else reason
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data, reason=truncated_reason)
