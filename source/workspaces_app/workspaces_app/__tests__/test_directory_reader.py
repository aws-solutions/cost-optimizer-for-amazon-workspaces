#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import copy
import datetime
import unittest
from decimal import Decimal

# Third Party Libraries
import pytest

# AWS Libraries
import boto3
from botocore import stub

# Cost Optimizer for Amazon Workspaces
from ..directory_reader import DirectoryReader
from ..utils import usage_table_dao
from ..workspace_record import *
from workspaces_app.utils.dashboard_metrics import DashboardMetrics

dashboard_metrics = DashboardMetrics()


@pytest.fixture()
def sts_client():
    sts_client = boto3.client("sts")
    yield stub.Stubber(sts_client)


@pytest.fixture(scope="module")
def session():
    yield boto3.session.Session()


@pytest.fixture()
def stack_parameters():
    yield {
        "DryRun": "No",
        "TestEndOfMonth": "No",
        "ValueLimit": 0,
        "StandardLimit": 0,
        "PerformanceLimit": 0,
        "PowerLimit": 0,
        "PowerProLimit": 0,
        "GraphicsG4dnLimit": 0,
        "GraphicsProG4dnLimit": 0,
        "TerminateUnusedWorkspaces": "No",
    }


@pytest.fixture()
def directory_parameters():
    yield {
        "StartTime": datetime.datetime.now(),
        "EndTime": datetime.datetime.now(),
        "DirectoryId": "foobarbazqux",
        "DateTimeValues": {},
    }


def ws_description(**kwargs):
    default_args = {
        "region": "us-east-1",
        "account": "111111111111",
        "workspace_id": "test-ws-id",
        "directory_id": "test-dir-id",
        "usage_threshold": Decimal(100),
        "bundle_type": "test-bundle",
        "username": "test-user",
        "computer_name": "test-computer",
        "initial_mode": "test-mode",
        "tags": ["tag1", "tag2"],
    }
    filtered_args = {
        key: value for key, value in kwargs.items() if key in default_args.keys()
    }
    filtered_args = {**default_args, **filtered_args}
    return WorkspaceDescription(**filtered_args)


@pytest.fixture()
def ws_billing_data():
    return WorkspaceBillingData(
        billable_hours=20,
        new_mode="test-mode",
        workspace_terminated="",
        change_reported="No change",
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
def ws_record(ws_billing_data, ws_metrics):
    return WorkspaceRecord(
        description=ws_description(),
        billing_data=ws_billing_data,
        performance_metrics=ws_metrics,
        report_date="test-report-date",
        last_reported_metric_period="test-last-period",
        last_known_user_connection="test-last-connection",
    )


@unittest.mock.patch(DirectoryReader.__module__ + ".WorkspacesHelper")
def test_process_directory_no_workspaces(
    MockWorkspacesHelper, session, stack_parameters, directory_parameters
):
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = []
    region = "us-east-1"
    directory_reader = DirectoryReader(session, region)
    result = directory_reader.process_directory(
        stack_parameters, directory_parameters, dashboard_metrics
    )
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.assert_called_once()
    assert result[0] == 0
    assert result[1] == []
    assert result[2] == ""
    MockWorkspacesHelper.return_value.process_workspace.assert_not_called()


@unittest.mock.patch("boto3.session.Session")
@unittest.mock.patch(DirectoryReader.__module__ + ".upload_report")
@unittest.mock.patch(DirectoryReader.__module__ + ".WorkspacesHelper")
def test_process_directory_without_ddb_item(
    MockWorkspacesHelper,
    mock_upload_report,
    mock_session,
    stack_parameters,
    directory_parameters,
    ws_record,
):
    previous_mode = "AUTO_STOP"
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = [
        {
            "WorkspaceId": "ws-wert1234",
            "DirectoryId": "foobarbazqux",
            "UserName": "test",
            "IpAddress": "test",
            "State": "AVAILABLE",
            "BundleId": "testid123",
            "SubnetId": "subnetid123",
            "ErrorMessage": "string",
            "ErrorCode": "string",
            "ComputerName": "string",
            "VolumeEncryptionKey": "string",
            "UserVolumeEncryptionEnabled": False,
            "RootVolumeEncryptionEnabled": False,
            "WorkspaceProperties": {
                "RunningMode": previous_mode,
                "RunningModeAutoStopTimeoutInMinutes": 123,
                "RootVolumeSizeGib": 123,
                "UserVolumeSizeGib": 123,
                "ComputeTypeName": "STANDARD",
            },
            "ModificationStates": [],
        }
    ]
    mock_session.client.return_value.get_item.return_value = {}
    MockWorkspacesHelper.return_value.process_workspace.return_value = ws_record
    MockWorkspacesHelper.return_value.append_entry.return_value = ""
    MockWorkspacesHelper.return_value.expand_csv.return_value = ""
    account = "111111111111"
    mock_session.client.return_value.get_caller_identity.return_value = {
        "Account": account
    }
    region = "us-east-1"
    directory_reader = DirectoryReader(mock_session, region)
    result = directory_reader.process_directory(
        stack_parameters, directory_parameters, dashboard_metrics
    )
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.assert_called_once()
    assert result[0] == 1
    assert result[1] == [
        {
            "previousMode": ws_record.description.initial_mode,
            "newMode": ws_record.billing_data.new_mode,
            "bundleType": ws_record.description.bundle_type,
            "hourlyThreshold": ws_record.description.usage_threshold,
            "billableTime": ws_record.billing_data.billable_hours,
        }
    ]
    MockWorkspacesHelper.return_value.process_workspace.assert_called_with(
        unittest.mock.ANY, unittest.mock.ANY, dashboard_metrics
    )
    report_header = "WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode,Username,Computer Name,DirectoryId,WorkspaceTerminated,insessionlatency,cpuusage,memoryusage,rootvolumediskusage,uservolumediskusage,udppacketlossrate,Tags,ReportDate,\n"
    list_processed_workspaces = "test-ws-id,20,100,No change,test-bundle,test-mode,test-mode,test-user,test-computer,test-dir-id,,93.42,94.42,95.42,96.42,97.42,98.42,\"['tag1', 'tag2']\",test-report-date\n"
    header_field_count = len(str.split(report_header, ","))
    data_field_count = len(str.split(list_processed_workspaces, ","))
    assert header_field_count == data_field_count
    assert result[2] == list_processed_workspaces
    log_body = report_header + list_processed_workspaces
    mock_upload_report.assert_called_once_with(
        mock_session.return_value,
        directory_parameters.get("DateTimeValues"),
        stack_parameters,
        log_body,
        directory_parameters["DirectoryId"],
        ws_record.description.region,
        ws_record.description.account,
    )


def test_get_dry_run(session):
    directory_reader = DirectoryReader(session, "us-east-1")
    assert directory_reader.get_dry_run({"DryRun": "Yes"})
    assert not directory_reader.get_dry_run({"DryRun": "No"})


def test_get_end_of_month(session):
    directory_reader = DirectoryReader(session, "us-east-1")
    assert directory_reader.get_end_of_month({"TestEndOfMonth": "Yes"})
    assert not directory_reader.get_end_of_month({"TestEndOfMonth": "No"})


@unittest.mock.patch("boto3.session.Session")
@unittest.mock.patch(DirectoryReader.__module__ + ".upload_report")
@unittest.mock.patch(DirectoryReader.__module__ + ".WorkspacesHelper")
def test_process_directory_with_multiple_graphics_workspaces(
    MockWorkspacesHelper,
    mock_session,
    stack_parameters,
    directory_parameters,
    ws_record,
):
    # Setup two workspaces, one with GRAPHICS_G4DN and another with GRAPHICSPRO_G4DN
    graphics_workspaces = [
        {
            "WorkspaceId": "ws-graphics1",
            "DirectoryId": "foobarbazqux",
            "UserName": "graphics_user",
            "State": "AVAILABLE",
            "WorkspaceProperties": {
                "RunningMode": "AUTO_STOP",
                "ComputeTypeName": "GRAPHICS_G4DN",
            },
        },
        {
            "WorkspaceId": "ws-graphicsPro1",
            "DirectoryId": "foobarbazqux",
            "UserName": "graphicsPro_user",
            "State": "AVAILABLE",
            "WorkspaceProperties": {
                "RunningMode": "AUTO_STOP",
                "ComputeTypeName": "GRAPHICSPRO_G4DN",
            },
        },
    ]
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = (
        graphics_workspaces
    )
    ws_records = [copy.deepcopy(ws_record), copy.deepcopy(ws_record)]
    for idx, record in enumerate(ws_records):
        record.description = ws_description(
            **{
                "bundle_type": graphics_workspaces[idx]["WorkspaceProperties"][
                    "ComputeTypeName"
                ],
                "workspace_id": graphics_workspaces[idx]["WorkspaceId"],
            }
        )

    mock_session.client.return_value.get_item.return_value = {}
    mock_process_workspace = MockWorkspacesHelper.return_value.process_workspace
    mock_process_workspace.side_effect = ws_records
    region = "us-east-1"
    directory_reader = DirectoryReader(mock_session, region)
    result = directory_reader.process_directory(
        stack_parameters, directory_parameters, dashboard_metrics
    )
    mock_process_workspace.has_calls([(ws_records[0], None), (ws_records[1], None)])
    assert len(mock_process_workspace.call_args_list) == 2
    assert result[0] == 2
    assert result[1][0]["bundleType"] == "GRAPHICS_G4DN"
    assert result[1][1]["bundleType"] == "GRAPHICSPRO_G4DN"
    assert "GRAPHICS_G4DN" in result[2]
    assert "GRAPHICSPRO_G4DN" in result[2]
    mock_process_workspace.assert_called_with(
        unittest.mock.ANY, unittest.mock.ANY, dashboard_metrics
    )


@unittest.mock.patch("boto3.session.Session")
@unittest.mock.patch(DirectoryReader.__module__ + ".upload_report")
@unittest.mock.patch(DirectoryReader.__module__ + ".WorkspacesHelper")
@unittest.mock.patch(DirectoryReader.__module__ + ".logger.exception")
@unittest.mock.patch(DirectoryReader.__module__ + ".WorkspaceRecord.to_csv")
def test_process_directory_continues_after_error(
    mock_to_csv,
    mock_log_exception,
    MockWorkspacesHelper,
    mock_upload_report,
    mock_session,
    stack_parameters,
    directory_parameters,
    ws_record,
):
    workspaces = [
        {"WorkspaceId": "ws-error", "WorkspaceProperties": {}},
        {"WorkspaceId": "ws-success", "WorkspaceProperties": {}},
    ]
    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = (
        workspaces
    )
    MockWorkspacesHelper.return_value.process_workspace.side_effect = [
        Exception("Error processing workspace ws-error"),
        ws_record,
    ]
    mock_session.client.return_value.get_item.return_value = {}
    region = "us-east-1"
    directory_reader = DirectoryReader(mock_session, region)
    result = directory_reader.process_directory(
        stack_parameters, directory_parameters, dashboard_metrics
    )
    MockWorkspacesHelper.return_value.process_workspace.assert_called_with(
        unittest.mock.ANY, unittest.mock.ANY, dashboard_metrics
    )
    mock_log_exception.assert_called_once_with(
        f"Error processing the workspace ws-error: Error processing workspace ws-error"
    )
    upload_args = mock_upload_report.call_args_list[0]
    assert (
        len(result[1]) == 1
        and result[1][0]["newMode"] == "test-mode"
        and result[1][0]["bundleType"] == "test-bundle"
    )
    assert mock_upload_report.call_count == len(workspaces)
    assert mock_to_csv.call_count == len(result[1]) * 2
    assert (
        "WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,New Mode,Username,Computer Name,DirectoryId,WorkspaceTerminated,insessionlatency,cpuusage,memoryusage,rootvolumediskusage,uservolumediskusage,udppacketlossrate,Tags,ReportDate,\n"
        in upload_args[0][3]
    )


@unittest.mock.patch("boto3.session.Session")
@unittest.mock.patch(DirectoryReader.__module__ + ".upload_report")
@unittest.mock.patch(DirectoryReader.__module__ + ".WorkspacesHelper")
@unittest.mock.patch(DirectoryReader.__module__ + ".time")
def test_process_directory_new_month(
    mock_time,
    MockWorkspacesHelper,
    mock_upload_report,
    mock_session,
    stack_parameters,
    directory_parameters,
    ws_record,
    ws_billing_data,
):
    workspace_id = "test-ws-id"
    directory_id = "foobarbazqux"
    bundle_type = "VALUE"
    usage_threshold = 20
    initial_mode = "test-mode"
    last_reported_month = 4  # April
    current_month = 5  # May

    mock_workspace = {
        "WorkspaceId": workspace_id,
        "WorkspaceProperties": {
            "ComputeTypeName": bundle_type,
            "RunningMode": initial_mode,
            "RunningModeAutoStopTimeoutInMinutes": 60,
        },
        "UserName": "user1",
        "ComputerName": "computer1",
    }

    # Modify the ws_record fixture to simulate a different month
    ws_record.last_reported_metric_period = (
        f"2023-{last_reported_month:02d}-30T23:59:59Z"
    )

    mock_usage_table_dao = unittest.mock.Mock()
    mock_usage_table_dao.get_workspace_ddb_item.return_value = ws_record

    MockWorkspacesHelper.return_value.get_workspaces_for_directory.return_value = [
        mock_workspace
    ]
    MockWorkspacesHelper.return_value.get_hourly_threshold_for_bundle_type.return_value = (
        usage_threshold
    )
    MockWorkspacesHelper.return_value.process_workspace.return_value = ws_record

    account = "111111111111"
    mock_session.client.return_value.get_caller_identity.return_value = {
        "Account": account
    }

    region = "us-east-1"
    directory_reader = DirectoryReader(mock_session, region)
    directory_reader.usage_table_dao = mock_usage_table_dao

    # Mock the current month
    mock_time.gmtime.return_value = unittest.mock.Mock(tm_mon=current_month)

    result = directory_reader.process_directory(
        stack_parameters, directory_parameters, unittest.mock.Mock()
    )
    assert result[0] == 1
    assert result[1] == [
        {
            "previousMode": ws_record.description.initial_mode,
            "newMode": ws_record.billing_data.new_mode,
            "bundleType": ws_record.description.bundle_type,
            "hourlyThreshold": ws_record.description.usage_threshold,
            "billableTime": ws_record.billing_data.billable_hours,
        }
    ]
    MockWorkspacesHelper.return_value.process_workspace.assert_called_with(
        unittest.mock.ANY, unittest.mock.ANY, unittest.mock.ANY
    )
    mock_usage_table_dao.get_workspace_ddb_item.assert_called_once_with(
        ws_description(
            tags=[],
            workspace_id=workspace_id,
            bundle_type=bundle_type,
            initial_mode=initial_mode,
            username="user1",
            computer_name="computer1",
            usage_threshold=usage_threshold,
            directory_id=directory_id,
        )
    )
    mock_upload_report.assert_called_once()

    assert (
        ws_record.last_reported_metric_period
        == f"2023-{last_reported_month:02d}-30T23:59:59Z"
    )
    assert directory_reader.usage_table_dao.update_ddb_item.call_count == 1
    updated_ws_record = directory_reader.usage_table_dao.update_ddb_item.call_args[0][0]
    assert updated_ws_record.description.workspace_id == workspace_id
    assert updated_ws_record.description.initial_mode == initial_mode
    assert (
        updated_ws_record.description.usage_threshold
        == ws_record.description.usage_threshold
    )
    assert updated_ws_record.billing_data.new_mode == ws_billing_data.new_mode
    assert (
        updated_ws_record.billing_data.billable_hours == ws_billing_data.billable_hours
    )

    # Assertions for creating a new WorkspaceDescription when ws_record is None
    assert isinstance(
        MockWorkspacesHelper.return_value.process_workspace.call_args[0][0],
        WorkspaceDescription,
    )
    new_ws_description = MockWorkspacesHelper.return_value.process_workspace.call_args[
        0
    ][0]
    expected_ws_description = WorkspaceDescription(
        account=ws_record.description.account,
        region=ws_record.description.region,
        directory_id=directory_id,
        workspace_id=workspace_id,
        initial_mode=initial_mode,
        usage_threshold=usage_threshold,
        bundle_type=bundle_type,
        username=mock_workspace["UserName"],
        computer_name=mock_workspace["ComputerName"],
    )

    assert new_ws_description == expected_ws_description
