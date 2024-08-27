#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
from decimal import Decimal

# Third Party Libraries
import pytest

# Cost Optimizer for Amazon Workspaces
from ..workspace_record import *

METRIC_LIST = [
    "InSessionLatency",
    "CPUUsage",
    "MemoryUsage",
    "RootVolumeDiskUsage",
    "UserVolumeDiskUsage",
    "UDPPacketLossRate",
]


@pytest.fixture()
def ws_description():
    return WorkspaceDescription(
        region="test-region",
        account="test-acct",
        workspace_id="test-ws-id",
        directory_id="test-dir-id",
        usage_threshold=Decimal(100),
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
        change_reported="-H-",
    )


@pytest.fixture()
def weighted_avg():
    return WeightedAverage(Decimal("93.42"), 67)


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
    )


@pytest.fixture()
def ddb_item(ws_record):
    return {
        "WorkspaceId": {
            "S": ws_record.description.workspace_id,
        },
        "Region": {"S": ws_record.description.region},
        "Account": {
            "S": ws_record.description.account,
        },
        "BillableHours": {
            "N": str(ws_record.billing_data.billable_hours),
        },
        "UsageThreshold": {
            "N": str(ws_record.description.usage_threshold),
        },
        "ChangeReported": {"S": ws_record.billing_data.change_reported},
        "BundleType": {
            "S": ws_record.description.bundle_type,
        },
        "InitialMode": {
            "S": ws_record.description.initial_mode,
        },
        "NewMode": {
            "S": ws_record.billing_data.new_mode,
        },
        "Username": {
            "S": ws_record.description.username,
        },
        "ComputerName": {
            "S": ws_record.description.computer_name,
        },
        "DirectoryId": {
            "S": ws_record.description.directory_id,
        },
        "WorkspaceTerminated": {
            "S": ws_record.billing_data.workspace_terminated,
        },
        "InSessionLatency": {
            "N": str(ws_record.performance_metrics.in_session_latency.avg),
        },
        "InSessionLatencyCount": {
            "N": str(ws_record.performance_metrics.in_session_latency.count),
        },
        "CPUUsage": {
            "N": str(
                ws_record.performance_metrics.cpu_usage.avg,
            )
        },
        "CPUUsageCount": {
            "N": str(ws_record.performance_metrics.cpu_usage.count),
        },
        "MemoryUsage": {
            "N": str(ws_record.performance_metrics.memory_usage.avg),
        },
        "MemoryUsageCount": {
            "N": str(ws_record.performance_metrics.memory_usage.count),
        },
        "RootVolumeDiskUsage": {
            "N": str(ws_record.performance_metrics.root_volume_disk_usage.avg),
        },
        "RootVolumeDiskUsageCount": {
            "N": str(ws_record.performance_metrics.root_volume_disk_usage.count),
        },
        "UserVolumeDiskUsage": {
            "N": str(ws_record.performance_metrics.user_volume_disk_usage.avg),
        },
        "UserVolumeDiskUsageCount": {
            "N": str(ws_record.performance_metrics.user_volume_disk_usage.count),
        },
        "UDPPacketLossRate": {
            "N": str(ws_record.performance_metrics.udp_packet_loss_rate.avg)
        },
        "UDPPacketLossRateCount": {
            "N": str(ws_record.performance_metrics.udp_packet_loss_rate.count)
        },
        "Tags": {
            "S": ws_record.tags,
        },
        "ReportDate": {"S": ws_record.report_date},
        "LastReportedMetricPeriod": {"S": ws_record.last_reported_metric_period},
        "LastKnownUserConnection": {"S": ws_record.last_known_user_connection},
    }


def test_ddb_item_to_workspace_record(ws_record, ddb_item, ws_description):
    result = WorkspaceRecord.from_ddb_obj(ddb_item, ws_description)

    assert result == ws_record


def test_workspace_record_to_ddb_item(ws_record, ddb_item):
    result = ws_record.to_ddb_obj()

    assert result == ddb_item


def test_serialize():
    test_fields = {
        "none_item": None,
        "string_item": "string",
        "decimal_item": Decimal("10.2"),
        "int": 10,
    }
    expected_result = {
        "NoneItem": {"NULL": True},
        "StringItem": {"S": "string"},
        "DecimalItem": {"N": "10.2"},
        "Int": {"N": "10"},
    }
    result = {}
    for key, value in test_fields.items():
        result |= WorkspaceRecord.serialize(key, value)
    assert result == expected_result


def test_deserialize():
    test_fields = {
        "none_item": None,
        "string_item": "string",
        "decimal_item": Decimal("10.2"),
        "int": 10,
    }
    test_ddb_item = {
        "NoneItem": {"NULL": True},
        "StringItem": {"S": "string"},
        "DecimalItem": {"N": "10.2"},
        "Int": {"N": "10"},
    }
    result = {}
    for key, value in test_ddb_item.items():
        result |= WorkspaceRecord.deserialize(key, value)
    assert result == test_fields


def test_class_field_to_ddb_attr_with_underscore():
    test_string = "test_string"

    result = WorkspaceRecord.class_field_to_ddb_attr(test_string)

    assert result == "TestString"


def test_class_field_to_ddb_attr_without_underscore():
    test_string = "teststring"

    result = WorkspaceRecord.class_field_to_ddb_attr(test_string)

    assert result == "Teststring"


def test_ddb_attr_to_class_field():
    test_string = "TestString"

    result = WorkspaceRecord.ddb_attr_to_class_field(test_string)

    assert result == "test_string"


def test_ddb_attr_to_class_field_with_caps():
    test_string = "TESTString"

    result = WorkspaceRecord.ddb_attr_to_class_field(test_string)

    assert result == "test_string"


def test_weighted_avg(ws_metrics):
    weighted_avg = ws_metrics.cpu_usage.weighted_avg()

    assert weighted_avg == ws_metrics.cpu_usage.avg * ws_metrics.cpu_usage.count


def test_weighted_average_merge(ws_metrics):
    wa_1 = ws_metrics.in_session_latency
    wa_2 = ws_metrics.udp_packet_loss_rate

    merged_wa = wa_1.merge(wa_2)
    expected_count = wa_1.count + wa_2.count
    expected_avg = Decimal((wa_1.weighted_avg() + wa_2.weighted_avg()) / expected_count)
    assert merged_wa.avg == expected_avg
    assert merged_wa.count == expected_count


def test_to_csv(ws_record):
    expected = "test-ws-id,20,100,ToHourly,test-bundle,test-mode,test-mode,test-user,test-computer,test-dir-id,,93.42,94.42,95.42,96.42,97.42,98.42,[{'key1': 'tag1'}, {'key2': 'tag2'}],test-report-date\n"
    assert ws_record.to_csv() == expected
