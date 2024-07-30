#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

# Third Party Libraries
import pytest

# AWS Libraries
import boto3
import boto3.session
from botocore import stub

# Cost Optimizer for Amazon Workspaces
from ...user_session import *
from ..user_session_dao import UserSessionDAO

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def user_session_timestamps_factory(length):
    time = datetime(2024, 1, 1, 12, 0, 0)
    timestamps = []
    for i in range(length):
        timestamps.append(time)
        time = time + datetime.timedelta(minutes=5)
    return timestamps


def user_session_timestamps_factory(length):
    time = datetime(2024, 1, 1, 12, 0, 0)
    timestamps = []
    for i in range(length):
        timestamps.append(time)
        time = time + timedelta(minutes=5)
    return timestamps


def convert_time_to_string(session_time):
    return session_time.strftime(TIME_FORMAT)


def get_session_time(session):
    start = session.active_sessions[0].strftime(TIME_FORMAT)
    end = session.active_sessions[-1].strftime(TIME_FORMAT)
    return start + " - " + end


@pytest.fixture()
def user_session():
    return UserSession(
        workspace_id="test-id",
        directory_id="test-id",
        region="test-region",
        account="test-account",
        username="test-user",
        active_sessions=user_session_timestamps_factory(5),
        duration_hours=1,
        in_session_latency=Decimal("93.42"),
        cpu_usage=Decimal("94.42"),
        memory_usage=Decimal("95.42"),
        root_volume_disk_usage=Decimal("96.42"),
        user_volume_disk_usage=Decimal("97.42"),
        udp_packet_loss_rate=Decimal("98.42"),
    )


@pytest.fixture()
def ddb_item(user_session):
    return {
        "WorkspaceId": {
            "S": user_session.workspace_id,
        },
        "SessionTime": {"S": get_session_time(user_session)},
        "DirectoryId": {
            "S": user_session.directory_id,
        },
        "Region": {"S": user_session.region},
        "Account": {
            "S": user_session.account,
        },
        "Username": {
            "S": user_session.username,
        },
        "ActiveSessions": {
            "L": list(
                map(
                    lambda x: {"S": convert_time_to_string(x)},
                    user_session.active_sessions,
                )
            ),
        },
        "DurationHours": {"N": str(user_session.duration_hours)},
        "InSessionLatency": {
            "N": str(user_session.in_session_latency),
        },
        "CPUUsage": {
            "N": str(
                user_session.cpu_usage,
            )
        },
        "MemoryUsage": {
            "N": str(user_session.memory_usage),
        },
        "RootVolumeDiskUsage": {
            "N": str(user_session.root_volume_disk_usage),
        },
        "UserVolumeDiskUsage": {
            "N": str(user_session.user_volume_disk_usage),
        },
        "UDPPacketLossRate": {"N": str(user_session.udp_packet_loss_rate)},
    }


def batch_write_item_response_factory(items_to_process=None):
    unprocessed_items = {"UnprocessedItems": {}}
    if items_to_process:
        unprocessed_items["UnprocessedItems"] = {"test-table": items_to_process}
    return {
        **unprocessed_items,
        "ConsumedCapacity": [
            {
                "TableName": "string",
                "CapacityUnits": 123.0,
                "ReadCapacityUnits": 123.0,
                "WriteCapacityUnits": 123.0,
                "Table": {
                    "ReadCapacityUnits": 123.0,
                    "WriteCapacityUnits": 123.0,
                    "CapacityUnits": 123.0,
                },
            }
        ],
        "ItemCollectionMetrics": {},
    }


@unittest.mock.patch("boto3.session.Session")
def test_batch_write_ddb_item(
    mock_session,
    ddb_item,
    user_session,
):
    list_ddb_items = [ddb_item, ddb_item]
    table_name = "test-table"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    mock_session.return_value.client.return_value = dynamo_client
    stub_dynamo.activate()
    stub_dynamo.add_response(
        "batch_write_item",
        batch_write_item_response_factory(),
        expected_params={
            "RequestItems": {
                table_name: [{"PutRequest": {"Item": item}} for item in list_ddb_items]
            }
        },
    )
    table_dao = UserSessionDAO(boto3.session.Session(), table_name, region)
    table_dao.update_ddb_items([user_session, user_session])
    stub_dynamo.assert_no_pending_responses()
    stub_dynamo.deactivate()


@unittest.mock.patch("time.sleep", return_value=None)
@unittest.mock.patch("boto3.session.Session")
def test_batch_write_ddb_item_with_retries_timeout(
    mock_session,
    mock_sleep,
    ddb_item,
    user_session,
):
    list_ddb_items = [ddb_item, ddb_item]
    table_name = "test-table"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    mock_session.return_value.client.return_value = dynamo_client
    stub_dynamo.activate()
    request_items = [{"PutRequest": {"Item": item}} for item in list_ddb_items]
    for _ in range(6):
        stub_dynamo.add_response(
            "batch_write_item",
            batch_write_item_response_factory(request_items),
            expected_params={"RequestItems": {table_name: request_items}},
        )
    table_dao = UserSessionDAO(boto3.session.Session(), table_name, region)
    table_dao.update_ddb_items([user_session, user_session])
    stub_dynamo.assert_no_pending_responses()


@unittest.mock.patch("time.sleep", return_value=None)
@unittest.mock.patch("boto3.session.Session")
def test_batch_write_ddb_item_retries_once(
    mock_session,
    mock_sleep,
    ddb_item,
    user_session,
):
    list_ddb_items = [ddb_item, ddb_item]
    table_name = "test-table"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    mock_session.return_value.client.return_value = dynamo_client
    stub_dynamo.activate()
    request_items = [{"PutRequest": {"Item": item}} for item in list_ddb_items]
    stub_dynamo.add_response(
        "batch_write_item",
        batch_write_item_response_factory(request_items),
        expected_params={"RequestItems": {table_name: request_items}},
    )
    stub_dynamo.add_response(
        "batch_write_item",
        batch_write_item_response_factory(),
        expected_params={"RequestItems": {table_name: request_items}},
    )
    table_dao = UserSessionDAO(boto3.session.Session(), table_name, region)
    table_dao.update_ddb_items([user_session, user_session])
    stub_dynamo.assert_no_pending_responses()
