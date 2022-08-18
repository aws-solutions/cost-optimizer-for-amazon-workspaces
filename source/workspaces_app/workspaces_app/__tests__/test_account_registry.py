#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

from unittest.mock import patch, MagicMock, ANY, call
from pytest import raises

from botocore.exceptions import ClientError

from ..account_registry import (
    AccountRegistry,
    DynamoDbAccountRegistry,
    NullAccountRegistry,
    get_account_registry,
    AccountInfo)

def test_account_registry_not_implemented():
    account_registry: AccountRegistry = AccountRegistry()
    with raises(NotImplementedError):
        account_registry.get_accounts()

def scan_response(items: list[dict[str, str]]) -> dict:
    return {
        'Items': items,
        'Count': len(items),
        'ScannedCount': len(items),
        'ConsumedCapacity': {
            'TableName': 'string',
            'CapacityUnits': 123.0,
            'ReadCapacityUnits': 123.0,
            'WriteCapacityUnits': 123.0,
            'Table': {
                'ReadCapacityUnits': 123.0,
                'WriteCapacityUnits': 123.0,
                'CapacityUnits': 123.0
            },
            'LocalSecondaryIndexes': {
                'string': {
                    'ReadCapacityUnits': 123.0,
                    'WriteCapacityUnits': 123.0,
                    'CapacityUnits': 123.0
                }
            },
            'GlobalSecondaryIndexes': {
                'string': {
                    'ReadCapacityUnits': 123.0,
                    'WriteCapacityUnits': 123.0,
                    'CapacityUnits': 123.0
                }
            }
        }
    }

def test_ddb_registry():
    mock_table: MagicMock = MagicMock()
    ddb_registry: DynamoDbAccountRegistry = DynamoDbAccountRegistry(mock_table)
    expected_items = [
        {'account_id': '111111111111', 'role_name': 'a-role-name'},
        {'account_id': '222222222222', 'role_name': 'another-role-name'}
    ]
    mock_table.scan.return_value = scan_response(expected_items)

    accounts: list[AccountInfo] = ddb_registry.get_accounts()

    assert accounts == [AccountInfo(**item) for item in expected_items]
    mock_table.scan.assert_called_once_with(ProjectionExpression='account_id, role_name')

def test_ddb_registry_empty():
    mock_table: MagicMock = MagicMock()
    ddb_registry: DynamoDbAccountRegistry = DynamoDbAccountRegistry(mock_table)
    mock_table.scan.return_value = scan_response([])

    accounts: list[AccountInfo] = ddb_registry.get_accounts()

    assert accounts == []
    mock_table.scan.assert_called_once_with(ProjectionExpression='account_id, role_name')

def test_ddb_registry_paginated():
    mock_table: MagicMock = MagicMock()
    ddb_registry: DynamoDbAccountRegistry = DynamoDbAccountRegistry(mock_table)
    expected_items_first = [
        {'account_id': '111111111111', 'role_name': 'a-role-name'},
        {'account_id': '222222222222', 'role_name': 'another-role-name'}
    ]
    response_first = scan_response(expected_items_first)
    response_first['LastEvaluatedKey'] = expected_items_first[-1]
    expected_items_second = [
        {'account_id': '333333333333', 'role_name': 'a-different-role-name'},
        {'account_id': '444444444444', 'role_name': 'yet-another-role-name'}
    ]
    response_second = scan_response(expected_items_second)
    mock_table.scan.side_effect = [response_first, response_second]

    accounts: list[AccountInfo] = ddb_registry.get_accounts()

    expected_items = expected_items_first
    expected_items.extend(expected_items_second)
    assert accounts == [AccountInfo(**item) for item in expected_items]
    mock_table.scan.assert_has_calls([
        call(ProjectionExpression='account_id, role_name'),
        call(ProjectionExpression='account_id, role_name',
            ExclusiveStartKey=response_first['LastEvaluatedKey'])
    ])

def test_ddb_registry_exception():
    mock_table: MagicMock = MagicMock()
    ddb_registry: DynamoDbAccountRegistry = DynamoDbAccountRegistry(mock_table)
    mock_table.scan.side_effect = ClientError(
        {
            'Error': {
                'Code': 'InternalServerError',
                'Message': 'message'
            }
        },
        'scan')
    with raises(ClientError):
        ddb_registry.get_accounts()

def test_null_registry():
    null_registry = NullAccountRegistry()
    assert [] == null_registry.get_accounts()

@patch.dict(os.environ, {'UserAgentString': 'user-agent', 'SpokeAccountDynamoDBTable': 'ddb-table'})
@patch(AccountRegistry.__module__ + '.DynamoDbAccountRegistry')
@patch(AccountRegistry.__module__ + '.Session')
def test_get_account_registry(mock_session, mock_ddb_registry):
    mock_ddb: MagicMock = MagicMock()
    mock_table: MagicMock = MagicMock()
    mock_ddb.Table.return_value = mock_table
    mock_session.return_value.resource.side_effect = lambda resource, **_: mock_ddb if resource == 'dynamodb' else Exception()

    account_registry: AccountRegistry = get_account_registry(mock_session())

    assert account_registry is mock_ddb_registry.return_value
    mock_session.return_value.resource.assert_called_once_with('dynamodb', config=ANY)
    mock_ddb.Table.assert_called_once_with(os.environ['SpokeAccountDynamoDBTable'])
    mock_ddb_registry.assert_called_once_with(mock_table)

@patch.dict(os.environ, {'UserAgentString': 'user-agent'})
@patch(AccountRegistry.__module__ + '.NullAccountRegistry')
@patch(AccountRegistry.__module__ + '.Session')
def test_get_account_registry_single_account(mock_session, mock_null_registry):
    account_registry: AccountRegistry = get_account_registry(mock_session())
    assert account_registry is mock_null_registry.return_value
