#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import unittest
from decimal import Decimal

# Third Party Libraries
import pytest

# AWS Libraries
import boto3
import boto3.session
from boto3.dynamodb.types import TypeDeserializer
from botocore import stub

# Cost Optimizer for Amazon Workspaces
from ...workspace_record import *
from ..usage_table_dao import UsageTableDAO


@pytest.fixture()
def ws_description():
    return WorkspaceDescription(
        region="test-region",
        account="test-acct",
        workspace_id="test-ws-id",
        directory_id="test-dir-id",
        usage_threshold=100,
        bundle_type="test-bundle",
        username="test-user",
        computer_name="test-computer",
        initial_mode="test-mode",
    )


@pytest.fixture()
def ws_billing_data():
    return WorkspaceBillingData(
        billable_hours=20,
        new_mode="test-mode",
        workspace_terminated="",
        change_reported="No change",
    )


@pytest.fixture()
def ws_metrics():
    return WorkspacePerformanceMetrics(
        in_session_latency=WeightedAverage(Decimal("93.42"), 67),
        cpu_usage=WeightedAverage(Decimal("94.42"), 68),
        memory_usage=WeightedAverage(Decimal("95.42"), 69),
        root_volume_disk_usage=WeightedAverage(Decimal("96.42"), 70),
        user_volume_disk_usage=WeightedAverage(Decimal("97.42"), 71),
        udp_packet_loss_rate=WeightedAverage(Decimal("98.42"), 72),
    )


@pytest.fixture()
def ws_record(ws_description, ws_billing_data, ws_metrics):
    return WorkspaceRecord(
        description=ws_description,
        billing_data=ws_billing_data,
        performance_metrics=ws_metrics,
        report_date="test-report-date",
        last_reported_metric_period="test-last-period",
        last_known_user_connection="test-last-connection",
        tags="[{'key1': 'tag1'}, {'key2': 'tag2'}]",
        workspace_type="PRIMARY",
    )


@pytest.fixture()
def workspace_ddb_item(ws_record):
    description = ws_record.description
    perf_metrics = ws_record.performance_metrics
    billing_data = ws_record.billing_data
    return {
        "WorkspaceId": {
            "S": description.workspace_id,
        },
        "Region": {"S": description.region},
        "Account": {
            "S": description.account,
        },
        "BillableHours": {
            "N": str(billing_data.billable_hours),
        },
        "UsageThreshold": {
            "N": str(description.usage_threshold),
        },
        "ChangeReported": {
            "S": billing_data.change_reported,
        },
        "BundleType": {
            "S": description.bundle_type,
        },
        "InitialMode": {
            "S": description.initial_mode,
        },
        "NewMode": {
            "S": billing_data.new_mode,
        },
        "Username": {
            "S": description.username,
        },
        "ComputerName": {
            "S": description.computer_name,
        },
        "DirectoryId": {
            "S": description.directory_id,
        },
        "WorkspaceTerminated": {
            "S": billing_data.workspace_terminated,
        },
        "InSessionLatency": {
            "N": str(perf_metrics.in_session_latency.avg),
        },
        "InSessionLatencyCount": {
            "N": str(perf_metrics.in_session_latency.count),
        },
        "CPUUsage": {
            "N": str(perf_metrics.cpu_usage.avg),
        },
        "CPUUsageCount": {
            "N": str(perf_metrics.cpu_usage.count),
        },
        "MemoryUsage": {
            "N": str(perf_metrics.memory_usage.avg),
        },
        "MemoryUsageCount": {
            "N": str(perf_metrics.memory_usage.count),
        },
        "RootVolumeDiskUsage": {
            "N": str(perf_metrics.root_volume_disk_usage.avg),
        },
        "RootVolumeDiskUsageCount": {
            "N": str(perf_metrics.root_volume_disk_usage.count),
        },
        "UserVolumeDiskUsage": {
            "N": str(perf_metrics.user_volume_disk_usage.avg),
        },
        "UserVolumeDiskUsageCount": {
            "N": str(perf_metrics.user_volume_disk_usage.count),
        },
        "UDPPacketLossRate": {
            "N": str(perf_metrics.udp_packet_loss_rate.avg),
        },
        "UDPPacketLossRateCount": {
            "N": str(perf_metrics.udp_packet_loss_rate.count),
        },
        "Tags": {
            "S": ws_record.tags,
        },
        "WorkspaceType": {
            "S": ws_record.workspace_type,
        },
        "ReportDate": {"S": ws_record.report_date},
        "LastReportedMetricPeriod": {"S": ws_record.last_reported_metric_period},
        "LastKnownUserConnection": {"S": ws_record.last_known_user_connection},
    }


@pytest.fixture()
def ddb_put_item_response():
    return {
        "Attributes": {},
        "ConsumedCapacity": {
            "TableName": "string",
            "CapacityUnits": 123.0,
            "ReadCapacityUnits": 123.0,
            "WriteCapacityUnits": 123.0,
            "Table": {
                "ReadCapacityUnits": 123.0,
                "WriteCapacityUnits": 123.0,
                "CapacityUnits": 123.0,
            },
        },
        "ItemCollectionMetrics": {},
    }


@unittest.mock.patch("boto3.session.Session")
def test_put_ddb_item(
    mock_session, workspace_ddb_item, ddb_put_item_response, ws_record
):
    table_name = "test-table"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    mock_session.return_value.client.return_value = dynamo_client
    stub_dynamo.activate()
    stub_dynamo.add_response(
        "put_item",
        ddb_put_item_response,
        expected_params={"TableName": table_name, "Item": workspace_ddb_item},
    )
    table_dao = UsageTableDAO(boto3.session.Session(), table_name, region)
    table_dao.update_ddb_item(ws_record)
    stub_dynamo.deactivate()


@unittest.mock.patch("boto3.session.Session")
def test_put_ddb_item_raises_error(mock_session, ws_record):
    table_name = "test-table"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    mock_session.return_value.client.return_value = dynamo_client
    stub_dynamo.activate()
    stub_dynamo.add_client_error("put_item", "InvalidParameter")
    table_dao = UsageTableDAO(boto3.session.Session(), table_name, region)
    try:
        table_dao.update_ddb_item(ws_record)
    except Exception as e:
        assert e.response["Error"]["Code"] == "InvalidParameter"

    stub_dynamo.deactivate()


@unittest.mock.patch("boto3.session.Session")
def test_get_workspace_ddb_item(
    mock_session, workspace_ddb_item, ws_record, ws_description
):
    table_name = "test-table"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    stub_dynamo.activate()
    mock_session.return_value.client.return_value = dynamo_client
    response = {"ConsumedCapacity": {}, "Item": workspace_ddb_item}
    stub_dynamo.add_response(
        "get_item",
        response,
        expected_params={
            "TableName": table_name,
            "Key": {
                "Region": {
                    "S": region,
                },
                "WorkspaceId": {
                    "S": ws_description.workspace_id,
                },
            },
        },
    )
    table_dao = UsageTableDAO(boto3.session.Session(), table_name, region)
    results = table_dao.get_workspace_ddb_item(ws_description)
    assert results == ws_record
    stub_dynamo.deactivate()


@unittest.mock.patch("boto3.session.Session")
def test_get_workspace_ddb_item_no_record(mock_session, ws_description):
    table_name = "test-table"
    workspace_id = "test-id"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    stub_dynamo.activate()
    mock_session.return_value.client.return_value = dynamo_client
    response = {
        "ConsumedCapacity": {},
    }
    stub_dynamo.add_response(
        "get_item",
        response,
        expected_params={
            "TableName": table_name,
            "Key": {
                "Region": {
                    "S": region,
                },
                "WorkspaceID": {
                    "S": workspace_id,
                },
            },
        },
    )
    table_dao = UsageTableDAO(boto3.session.Session(), table_name, region)
    results = table_dao.get_workspace_ddb_item(ws_description)
    assert results == ws_description
    stub_dynamo.deactivate()


@unittest.mock.patch("boto3.session.Session")
def test_get_workspace_ddb_item_client_error(mock_session, ws_description):
    table_name = "test_table"
    workspace_id = "test-id"
    region = "us-east-1"
    dynamo_client = boto3.client("dynamodb")
    stub_dynamo = stub.Stubber(dynamo_client)
    stub_dynamo.activate()
    mock_session.return_value.client.return_value = dynamo_client
    stub_dynamo.add_client_error("get_item", "InvalidParameter")
    table_dao = UsageTableDAO(boto3.session.Session(), table_name, region)
    results = table_dao.get_workspace_ddb_item(ws_description)
    assert results is ws_description
    stub_dynamo.deactivate()
