#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
from unittest.mock import patch

patch.dict(os.environ, {"DDB_TABLE_NAME": "test"}).start()
patch.dict(os.environ, {"AWS_DEFAULT_REGION": "us-east-1"}).start()
# Cost Optimizer for Amazon Workspaces
import register_spoke_lambda.register_spoke_accounts as register_spoke_accounts
from register_spoke_lambda.dynamodb_table import DynamoDBTable


def test_lambda_handler_put_item(mocker):
    context = {}
    event = {
        "account_id": "111111111111",
        "request_type": "Register",
        "role_arn": "arn:aws:iam::111111111111:role/Admin",
    }
    mocker.patch.object(DynamoDBTable, "put_item")
    spy_put_item = mocker.spy(DynamoDBTable, "put_item")
    response = register_spoke_accounts.lambda_handler(event, context)
    spy_put_item.assert_called_once()
    assert response == {
        "status": {"code": "Success", "message": "Successfully processed the request"}
    }


def test_lambda_handler_delete_item(mocker):
    context = {}
    event = {
        "account_id": "111111111111",
        "request_type": "Unregister",
        "role_arn": "arn:aws:iam::111111111111:role/Admin",
    }
    mocker.patch.object(DynamoDBTable, "delete_item")
    spy_delete_item = mocker.spy(DynamoDBTable, "delete_item")
    response = register_spoke_accounts.lambda_handler(event, context)
    spy_delete_item.assert_called_once()
    assert response == {
        "status": {"code": "Success", "message": "Successfully processed the request"}
    }


def test_lambda_handler_error_response(mocker):
    context = {}
    event = {
        "account_id": "test",
        "request_type": "Unregister",
        "role_arn": "arn:aws:iam::111111111111:role/Admin",
    }
    mocker.patch.object(DynamoDBTable, "delete_item")
    response = register_spoke_accounts.lambda_handler(event, context)
    assert response == {
        "status": {
            "code": "Failed",
            "message": "Error while processing the request",
            "error": "Invalid value provided for Account ID.",
        }
    }
