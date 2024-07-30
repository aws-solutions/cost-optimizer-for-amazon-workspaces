#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import datetime
import unittest
import uuid

# Third Party Libraries
from dateutil.tz import tzutc

# AWS Libraries
from botocore.stub import Stubber

# Cost Optimizer for Amazon Workspaces
import uuid_generator.uuid_generator as uuid_generator


class MockContext:
    def __init__(self):
        self.log_stream_name = "log_stream_name"


@unittest.mock.patch("cfnresponse.send")
def test_lambda_handler_create(mock_cfnresponse_send):
    event = {"RequestType": "Create"}
    context = MockContext()
    expected_uuid = uuid.uuid4()
    with unittest.mock.patch("uuid.uuid4") as mock_uuid4:
        mock_uuid4.return_value = expected_uuid
        uuid_generator.lambda_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(
        event, context, "SUCCESS", {"UUID": str(expected_uuid)}
    )


@unittest.mock.patch("cfnresponse.send")
def test_lambda_handler_update(mock_cfnresponse_send):
    event = {"RequestType": "Update", "StackId": "testid"}
    context = MockContext()
    cfn_client_stubber = Stubber(uuid_generator.cfn_client)
    response = {
        "Stacks": [
            {
                "StackName": "testStackName",
                "CreationTime": datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                "StackStatus": "",
                "Outputs": [{"OutputKey": "UUID", "OutputValue": "test-uuid"}],
            }
        ]
    }

    expected_params = {"StackName": "testid"}
    cfn_client_stubber.add_response("describe_stacks", response, expected_params)
    cfn_client_stubber.activate()
    uuid_generator.lambda_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(
        event, context, "SUCCESS", {"UUID": "test-uuid"}
    )


@unittest.mock.patch("cfnresponse.send")
def test_lambda_handler_delete(mock_cfnresponse_send):
    event = {"RequestType": "Delete"}
    context = MockContext()
    uuid_generator.lambda_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(
        event, context, "SUCCESS", {"UUID": ""}
    )


@unittest.mock.patch("uuid.uuid4")
@unittest.mock.patch("cfnresponse.send")
def test_lambda_handler_exception(mock_cfnresponse_send, mock_uuid4):
    event = {"RequestType": "Create"}
    context = MockContext()
    mock_uuid4.side_effect = Exception()
    uuid_generator.lambda_handler(event, context)
    mock_cfnresponse_send.assert_called_once_with(
        event, context, "FAILED", {}, context.log_stream_name
    )
