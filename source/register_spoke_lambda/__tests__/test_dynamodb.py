# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re
import pytest
import botocore
from botocore.stub import Stubber
from register_spoke_lambda.dynamodb_table import DynamoDBTable


def test_put_item_success():
    dynamodb_table = DynamoDBTable("test")
    table_stubber = Stubber(dynamodb_table.dynamo_db_client.meta.client)
    response = {}
    expected_params = {'Item': {'account_id': '123456789', 'role_name': 'arn:aws:12345::role/test_arn'}, 'TableName': 'test'}
    table_stubber.add_response('put_item', response, expected_params)
    table_stubber.activate()
    resp = dynamodb_table.put_item("123456789", "arn:aws:12345::role/test_arn")
    assert resp is None


def test_put_item_error():
    with pytest.raises(botocore.exceptions.ClientError,
                       match=re.escape("An error occurred (InvalidRequest) when calling the PutItem operation: ")):
        dynamodb_table = DynamoDBTable("test")
        table_stubber = Stubber(dynamodb_table.dynamo_db_client.meta.client)
        table_stubber.add_client_error('put_item', 'InvalidRequest')
        table_stubber.activate()
        dynamodb_table.put_item("123456789", "arn:aws:12345::role/test_arn")


def test_delete_item_success():
    dynamodb_table = DynamoDBTable("test")
    table_stubber = Stubber(dynamodb_table.dynamo_db_client.meta.client)
    response = {}
    expected_params = {'Key': {'account_id': '123456789', 'role_name': 'arn:aws:12345::role/test_arn'}, 'TableName': 'test'}
    table_stubber.add_response('delete_item', response, expected_params)
    table_stubber.activate()
    resp = dynamodb_table.delete_item("123456789", "arn:aws:12345::role/test_arn")
    assert resp is None


def test_delete_item_error():
    with pytest.raises(botocore.exceptions.ClientError,
                       match=re.escape("An error occurred (InvalidRequest) when calling the DeleteItem operation: ")):
        dynamodb_table = DynamoDBTable("test")
        table_stubber = Stubber(dynamodb_table.dynamo_db_client.meta.client)
        table_stubber.add_client_error('delete_item', 'InvalidRequest')
        table_stubber.activate()
        dynamodb_table.delete_item("123456789", "arn:aws:12345::role/test_arn")
