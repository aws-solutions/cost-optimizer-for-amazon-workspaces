#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import account_registration_provider.account_registration_provider as account_registration_provider
import cfnresponse
import boto3
import botocore
import pytest
import unittest
import json
import io
import os


class MockContext:
    def __init__(self):
        self.log_stream_name = 'log_stream_name'


@pytest.fixture(autouse=True)
def mock_env():
    patch = unittest.mock.patch.dict(os.environ, {
        'REGISTER_LAMBDA_ARN': 'some-arn',
        'MANAGEMENT_ROLE_ARN': 'some-other-arn'
    })
    patch.start()
    yield
    patch.stop()


@pytest.fixture()
def mock_clients():
    clients = {
        'sts': boto3.client('sts'),
        'lambda': boto3.client('lambda')
    }
    patch = unittest.mock.patch('boto3.client')
    patch.start()
    boto3.client.side_effect = lambda client, **_: clients[client]
    yield clients
    patch.stop()


@pytest.fixture()
def stub_clients(mock_clients):
    stubs = {service: botocore.stub.Stubber(client) for (service, client) in mock_clients.items()}
    for _, stub in stubs.items():
        stub.activate()
    yield stubs
    for _, stub in stubs.items():
        stub.deactivate()


@pytest.fixture()
def stub_get_caller_identity(stub_clients):
    stub_clients['sts'].add_response(
        'get_caller_identity',
        {
            'UserId': 'string',
            'Account': '111111111111',
            'Arn': 'arn:aws:iam::111111111111:user/root'
        })


def response_body(body):
    body_bytes = json.dumps(body).encode('utf-8')
    return botocore.response.StreamingBody(io.BytesIO(body_bytes), len(body_bytes))


def successful_payload():
    return {
        'status': {
            'code': 'Success',
            'message': 'reason'
        }
    }


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_create(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Create'}
    context = MockContext()
    response = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': response_body(successful_payload()),
        'ExecutedVersion': 'string'
    }
    stub_clients['lambda'].add_response('invoke', response, {
        'FunctionName': 'some-arn',
        'Payload': json.dumps({
            'account_id': '111111111111',
            'request_type': 'Register',
            'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
        }),
        'InvocationType': 'RequestResponse'
    })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.SUCCESS, response)


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_update(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Update'}
    context = MockContext()
    response = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': response_body(successful_payload()),
        'ExecutedVersion': 'string'
    }
    stub_clients['lambda'].add_response('invoke', response, {
        'FunctionName': 'some-arn',
        'Payload': json.dumps({
            'account_id': '111111111111',
            'request_type': 'Register',
            'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
        }),
        'InvocationType': 'RequestResponse'
    })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.SUCCESS, response)


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_delete(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Delete'}
    context = MockContext()
    response = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': response_body(successful_payload()),
        'ExecutedVersion': 'string'
    }
    stub_clients['lambda'].add_response('invoke', response, {
        'FunctionName': 'some-arn',
        'Payload': json.dumps({
            'account_id': '111111111111',
            'request_type': 'Unregister',
            'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
        }),
        'InvocationType': 'RequestResponse'
    })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.SUCCESS, response)


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_fatal_status(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Create'}
    context = MockContext()
    response = {
        'StatusCode': 500,
        'FunctionError': 'string',
        'LogResult': 'string',
        'Payload': response_body(successful_payload()),
        'ExecutedVersion': 'string'
    }
    stub_clients['lambda'].add_response('invoke', response, {
        'FunctionName': 'some-arn',
        'Payload': json.dumps({
            'account_id': '111111111111',
            'request_type': 'Register',
            'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
        }),
        'InvocationType': 'RequestResponse'
    })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.FAILED, response,
                                                  reason=unittest.mock.ANY)


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_exception(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Delete'}
    context = MockContext()
    stub_clients['lambda'].add_client_error('invoke', 'ServiceException', expected_params={
        'FunctionName': 'some-arn',
        'Payload': json.dumps({
            'account_id': '111111111111',
            'request_type': 'Unregister',
            'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
        }),
        'InvocationType': 'RequestResponse'
    })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.FAILED, {}, reason=unittest.mock.ANY)


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_registration_failed(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Delete'}
    context = MockContext()
    response = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': response_body({
            'status': {
                'code': 'Failed',
                'message': 'reason',
                'error': 'error'
            }
        }),
        'ExecutedVersion': 'string'
    }
    stub_clients['lambda'].add_response('invoke',
        response,
        {
            'FunctionName': 'some-arn',
            'Payload': json.dumps({
                'account_id': '111111111111',
                'request_type': 'Unregister',
                'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
            }),
            'InvocationType': 'RequestResponse'
        })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.FAILED, response, reason=unittest.mock.ANY)


@unittest.mock.patch('cfnresponse.send')
def test_event_handler_response_serializable(mock_cfnresponse_send, stub_clients, stub_get_caller_identity):
    event = {'RequestType': 'Create'}
    context = MockContext()
    body = successful_payload()
    response = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': response_body(body),
        'ExecutedVersion': 'string'
    }
    stub_clients['lambda'].add_response('invoke', response, {
        'FunctionName': 'some-arn',
        'Payload': json.dumps({
            'account_id': '111111111111',
            'request_type': 'Register',
            'role_arn': os.environ['MANAGEMENT_ROLE_ARN']
        }),
        'InvocationType': 'RequestResponse'
    })
    account_registration_provider.event_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(event, context, cfnresponse.SUCCESS, unittest.mock.ANY)
    sent_response = mock_cfnresponse_send.call_args[0][3]
    assert json.dumps(sent_response['Payload']) == json.dumps(body)
