#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import datetime
import time
from decimal import Decimal

# Third Party Libraries
import pytest
from dateutil.tz import tzutc
from freezegun import freeze_time

# AWS Libraries
import boto3
from botocore.stub import Stubber

# Cost Optimizer for Amazon Workspaces
from .. import workspaces_helper
from ..utils import date_utils, workspace_utils
from ..utils.dashboard_metrics import DashboardMetrics
from ..workspace_record import *


@pytest.fixture(scope="module")
def session():
    yield boto3.session.Session()


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
        last_reported_metric_period="2024-08-29T00:00:00Z",
        last_known_user_connection="test-last-connection",
        tags="[{'key1': 'tag1'}, {'key2': 'value2'}]",
        workspace_type="PRIMARY",
    )


def test_skip_tag_true_process_standard_workspace(mocker, session, ws_record):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": "",
            "end_time_selected_date": "",
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
        "usageTable": "test-table",
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mock_get_billable_hours = mocker.patch.object(
        workspace_helper.metrics_helper, "get_billable_hours_and_performance"
    )
    workspace_helper.metrics_helper.get_billable_hours_and_performance.return_value = {
        "billable_hours": 444,
        "performance_metrics": ws_record.performance_metrics,
    }
    mocker.patch.object(workspace_helper, "get_list_tags_for_workspace")
    mocker.patch.object(workspace_utils, "check_for_skip_tag")
    workspace_utils.check_for_skip_tag.return_value = True
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)
    assert result.description.bundle_type == "test-bundle"
    assert (
        result.billing_data.new_mode == "test-mode"
    )  # The old mode should not be changed as the skip tag is True
    # test that previous data was used
    assert mock_get_billable_hours.call_args.args == ("", "", ws_record, 60)


def test_bundle_type_returned_process_workspace(mocker, session, ws_record):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": "",
            "end_time_selected_date": "",
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mock_get_billable_hours = mocker.patch.object(
        workspace_helper.metrics_helper, "get_billable_hours_and_performance"
    )
    workspace_helper.metrics_helper.get_billable_hours_and_performance.return_value = {
        "billable_hours": 100,
        "performance_metrics": ws_record.performance_metrics,
    }
    mocker.patch.object(workspace_helper, "get_list_tags_for_workspace")
    mocker.patch.object(workspace_utils, "check_for_skip_tag")
    workspace_utils.check_for_skip_tag.return_value = False
    mocker.patch.object(workspace_helper, "get_hourly_threshold_for_bundle_type")
    workspace_helper.get_hourly_threshold_for_bundle_type.return_value = 5
    mocker.patch.object(workspace_helper, "compare_usage_metrics")
    workspace_helper.compare_usage_metrics.return_value = {
        "resultCode": "-N-",
        "newMode": "ALWAYS_ON",
    }
    mock_termination_status = mocker.patch.object(
        workspace_helper, "get_termination_status"
    )
    mock_termination_status.return_value = "", "last-known-time"
    dashboard_metrics = DashboardMetrics()
    # set ws_record last reported data to prior to v2.7.1 release
    ws_record.last_reported_metric_period = "2024-08-27T00:00:00Z"
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)
    assert result.description.bundle_type == "test-bundle"
    assert result.billing_data.billable_hours == 100
    assert result.last_known_user_connection == "last-known-time"
    assert result.billing_data.new_mode == "ALWAYS_ON"
    assert result.billing_data.change_reported == "-N-"
    assert result.performance_metrics == ws_record.performance_metrics
    # test that previous data was not used
    assert mock_get_billable_hours.call_args.args == ("", "", ws_record.description, 60)


def test_modify_workspace_properties_returns_always_on(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        "WorkspaceId": "123qwer",
        "WorkspaceProperties": {"RunningMode": "ALWAYS_ON"},
    }
    client_stubber.add_response(
        "modify_workspace_properties", response, expected_params
    )
    client_stubber.activate()
    workspace_id = "123qwer"
    new_running_mode = "ALWAYS_ON"
    result = workspace_helper.modify_workspace_properties(
        workspace_id, new_running_mode
    )
    assert result == "-M-"


def test_modify_workspace_properties_returns_auto_stop(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {
        "WorkspaceId": "123qwer",
        "WorkspaceProperties": {"RunningMode": "AUTO_STOP"},
    }
    client_stubber.add_response(
        "modify_workspace_properties", response, expected_params
    )
    client_stubber.activate()
    workspace_id = "123qwer"
    new_running_mode = "AUTO_STOP"
    result = workspace_helper.modify_workspace_properties(
        workspace_id, new_running_mode
    )
    assert result == "-H-"
    client_stubber.deactivate()


def test_modify_workspace_properties_returns_exception_error_code(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {"WorkspaceProperties": {"RunningMode": "AUTO_STOP"}}

    client_stubber.add_response(
        "modify_workspace_properties", response, expected_params
    )
    client_stubber.activate()
    workspace_id = "123qwer"
    new_running_mode = "AUTO_STOP"
    result = workspace_helper.modify_workspace_properties(
        workspace_id, new_running_mode
    )
    assert result == "-E-"


def test_modify_workspace_api_is_not_called_for_dry_run_true_auto_stop(session):
    # validate that the stubber call is not made when Dry Run is set to True
    # send an invalid request using stubber and validate that the does not method throws exception

    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {"WorkspaceProperties": {"RunningMode": "AUTO_STOP"}}
    client_stubber.add_response(
        "modify_workspace_properties", response, expected_params
    )
    client_stubber.activate()
    workspace_id = "123qwer"
    new_running_mode = "AUTO_STOP"
    # check if the method throws exception and validate that the stubber was not called
    result = workspace_helper.modify_workspace_properties(
        workspace_id, new_running_mode
    )
    assert result == "-H-"
    client_stubber.deactivate()


def test_modify_workspace_api_is_not_called_for_dry_run_true_always_on(session):
    # validate that the stubber call is not made when Dry Run is set to True
    # send an invalid request using stubber and validate that the does not method throws exception

    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {"WorkspaceProperties": {"RunningMode": "ALWAYS_ON"}}
    client_stubber.add_response(
        "modify_workspace_properties", response, expected_params
    )
    client_stubber.activate()
    workspace_id = "123qwer"
    new_running_mode = "ALWAYS_ON"
    # check if the method throws exception and validate that the stubber was not called
    result = workspace_helper.modify_workspace_properties(
        workspace_id, new_running_mode
    )
    assert result == "-M-"
    client_stubber.deactivate()


def test_check_for_skip_tag_returns_true_for_skip_convert_tag():
    tags = [{"Key": "skip_convert", "Value": "True"}]
    result = workspace_utils.check_for_skip_tag(tags)
    assert result is True


def test_check_for_skip_tag_returns_false_if_skip_convert_tag_absent():
    tags = [{"Key": "nothing", "Value": "True"}]
    result = workspace_utils.check_for_skip_tag(tags)
    assert result is False


def test_check_for_skip_tag_returns_false_if_tag_list_is_empty():
    tags = []
    result = workspace_utils.check_for_skip_tag(tags)
    assert result is False


def test_terminate_unused_workspace_returns_yes_when_workspace_terminated_successfully(
    session,
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {}
    expected_params = {"TerminateWorkspaceRequests": [{"WorkspaceId": "123qwer"}]}
    client_stubber.add_response("terminate_workspaces", response, expected_params)
    client_stubber.activate()
    workspace_id = "123qwer"
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == "Yes"
    client_stubber.deactivate()


def test_terminate_unused_workspace_returns_empty_string_when_workspace_not_terminated(
    session,
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error("TerminateWorkspaceRequests", "Invalid_request")
    client_stubber.activate()
    workspace_id = "123qwer"
    result = workspace_helper.terminate_unused_workspace(workspace_id)
    assert result == ""
    client_stubber.deactivate()


def test_check_if_workspace_available_on_first_day_selected_month_returns_true(session):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = "123qwer"
    response = {
        "Datapoints": [
            {
                "Timestamp": datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                "Maximum": 1.0,
                "Unit": "Count",
            },
            {
                "Timestamp": datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                "Maximum": 1.0,
                "Unit": "Count",
            },
            {
                "Timestamp": datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                "Maximum": 1.0,
                "Unit": "Count",
            },
            {
                "Timestamp": datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                "Maximum": 0.0,
                "Unit": "Count",
            },
            {
                "Timestamp": datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                "Maximum": 0.0,
                "Unit": "Count",
            },
        ]
    }
    expected_params = {
        "Dimensions": [{"Name": "WorkspaceId", "Value": workspace_id}],
        "Namespace": "AWS/WorkSpaces",
        "MetricName": "Available",
        "StartTime": start_time,
        "EndTime": end_time,
        "Period": 3600,
        "Statistics": ["Maximum"],
    }
    client_stubber.add_response("get_metric_statistics", response, expected_params)
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day_selected_month(
        workspace_id
    )
    assert result is True
    client_stubber.deactivate()


def test_check_if_workspace_available_on_first_day_selected_month_returns_false(
    session,
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"

    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = "123qwer"
    response = {"Datapoints": []}
    expected_params = {
        "Dimensions": [{"Name": "WorkspaceId", "Value": workspace_id}],
        "Namespace": "AWS/WorkSpaces",
        "MetricName": "Available",
        "StartTime": start_time,
        "EndTime": end_time,
        "Period": 3600,
        "Statistics": ["Maximum"],
    }
    client_stubber.add_response("get_metric_statistics", response, expected_params)
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day_selected_month(
        workspace_id
    )
    assert result is False
    client_stubber.deactivate()


def test_check_if_workspace_available_on_first_day_selected_month_returns_false_for_exception(
    session,
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.cloudwatch_client)
    workspace_id = "123qwer"
    client_stubber.add_client_error("get_metric_statistics", "Invalid request")
    client_stubber.activate()
    result = workspace_helper.check_if_workspace_available_on_first_day_selected_month(
        workspace_id
    )
    assert result is False
    client_stubber.deactivate()


def test_get_workspaces_for_directory_returns_list_of_workspaces(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    response = {
        "Workspaces": [
            {"WorkspaceId": "1234"},
            {"WorkspaceId": "1234"},
            {"WorkspaceId": "1234"},
        ]
    }
    expected_params = {"DirectoryId": directory_id}
    client_stubber.add_response("describe_workspaces", response, expected_params)
    client_stubber.activate()
    result = workspace_helper.get_workspaces_for_directory(directory_id)
    assert result == [
        {"WorkspaceId": "1234"},
        {"WorkspaceId": "1234"},
        {"WorkspaceId": "1234"},
    ]
    client_stubber.deactivate()


def test_get_workspaces_for_directory_returns_empty_list_for_exception(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error("describe_workspaces", "Invalid Directory")
    client_stubber.activate()
    result = workspace_helper.get_workspaces_for_directory(directory_id)
    assert result == []
    client_stubber.deactivate()


def test_check_if_workspace_needs_to_be_terminated_returns_dry_run_is_dry_run_true(
    session,
):
    # 'terminateUnusedWorkspaces': 'Dry Run'
    # 'isDryRun': True

    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Dry Run",
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(
        workspace_id, billable_time
    )
    assert result == "Yes - Dry Run"


def test_check_if_workspace_needs_to_be_terminated_returns_dry_run_is_dry_run_false(
    session,
):
    # 'terminateUnusedWorkspaces': 'Dry Run'
    # 'isDryRun': False

    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Dry Run",
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(
        workspace_id, billable_time
    )
    assert result == "Yes - Dry Run"


def test_check_if_workspace_needs_to_be_terminated_returns_empty_string_is_dry_run_true(
    session,
):
    # 'terminateUnusedWorkspaces': 'Yes'
    # 'isDryRun': True

    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Yes",
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(
        workspace_id, billable_time
    )
    assert result == ""


def test_check_if_workspace_needs_to_be_terminated_returns_yes_is_dry_run_false(
    mocker, session
):
    # 'terminateUnusedWorkspaces': 'Yes'
    # 'isDryRun': False

    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Yes",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": True,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mocker.patch.object(workspace_helper, "terminate_unused_workspace")
    workspace_helper.terminate_unused_workspace.return_value = "Yes"
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(
        workspace_id, billable_time
    )
    assert result == "Yes"


@freeze_time("2020-11-29 03:21:34")
def test_check_if_workspace_used_for_selected_period_returns_false_if_timestamp_is_none():
    last_known_user_connection_timestamp = None
    first_day_selected_month = date_utils.get_first_day_selected_month()
    result = workspace_utils.check_if_workspace_used_for_selected_period(
        last_known_user_connection_timestamp, first_day_selected_month
    )
    assert result is False


@freeze_time("2022-11-29 03:21:34")
def test_check_if_workspace_used_for_selected_period_returns_false_if_timestamp_is_before_first_day():
    last_known_user_connection_timestamp = datetime.datetime.strptime(
        "2021-01-10 19:35:15.524000+00:00", "%Y-%m-%d %H:%M:%S.%f+00:00"
    )
    first_day_selected_month = date_utils.get_first_day_selected_month()
    result = workspace_utils.check_if_workspace_used_for_selected_period(
        last_known_user_connection_timestamp, first_day_selected_month
    )
    assert result is False


@freeze_time("2020-11-29 03:21:34")
def test_check_if_workspace_used_for_selected_period_returns_true_if_timestamp_is_first_day_selected_month():
    last_known_user_connection_timestamp = datetime.datetime.now(
        datetime.timezone.utc
    ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_day_selected_month = date_utils.get_first_day_selected_month()
    result = workspace_utils.check_if_workspace_used_for_selected_period(
        last_known_user_connection_timestamp, first_day_selected_month
    )
    assert result is True


@freeze_time("2025-01-15 12:00:00")
def test_check_if_workspace_needs_to_be_terminated_returns_empty_string_with_billable_time(
    session,
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Dry Run",
        "dateTimeValues": {
            "current_month_last_day": True,
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 5
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(
        workspace_id, billable_time
    )
    assert result == ""


def test_get_last_known_user_connection_timestamp_returns_last_connected_time_value(
    session,
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    last_known_user_connection_timestamp = datetime.datetime.strptime(
        "2021-08-10 19:35:15.524000+00:00", "%Y-%m-%d %H:%M:%S.%f+00:00"
    )
    workspace_id = "123qwe123qwe"
    response = {
        "WorkspacesConnectionStatus": [
            {"LastKnownUserConnectionTimestamp": last_known_user_connection_timestamp}
        ]
    }
    expected_params = {"WorkspaceIds": [workspace_id]}
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_response(
        "describe_workspaces_connection_status", response, expected_params
    )
    client_stubber.activate()
    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)
    assert (
        result == last_known_user_connection_timestamp
    ), last_known_user_connection_timestamp
    client_stubber.deactivate()


def test_get_last_known_user_connection_timestamp_handles_pagination(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "ws-12345678"
    last_known_timestamp = datetime.datetime(
        2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
    )

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    response1 = {"WorkspacesConnectionStatus": [], "NextToken": "next-token"}
    expected_params1 = {"WorkspaceIds": [workspace_id]}

    response2 = {
        "WorkspacesConnectionStatus": [
            {
                "WorkspaceId": workspace_id,
                "LastKnownUserConnectionTimestamp": last_known_timestamp,
            }
        ]
    }
    expected_params2 = {"WorkspaceIds": [workspace_id], "NextToken": "next-token"}

    client_stubber.add_response(
        "describe_workspaces_connection_status", response1, expected_params1
    )
    client_stubber.add_response(
        "describe_workspaces_connection_status", response2, expected_params2
    )
    client_stubber.activate()

    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)

    assert result == last_known_timestamp
    client_stubber.deactivate()


def test_get_last_known_user_connection_timestamp_returns_resource_unavailable_for_exception(
    session,
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error(
        "get_last_known_user_connection_timestamp", "Invalid workspace"
    )
    client_stubber.activate()
    result = workspace_helper.get_last_known_user_connection_timestamp(workspace_id)
    assert result == "ResourceUnavailable"
    client_stubber.deactivate()


def test_get_termination_status_returns_empty_string_for_terminate_workspaces_no(
    mocker,
    session,
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = "No"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "No",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": True,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    test_timestamp = datetime.datetime.now()
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mock_get_last_connect = mocker.patch.object(
        workspaces_helper.WorkspacesHelper, "get_last_known_user_connection_timestamp"
    )
    mock_get_last_connect.return_value = test_timestamp
    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ("", time.strftime("%Y-%m-%d", test_timestamp.timetuple()))


def test_get_termination_status_returns_yes_for_terminate_workspaces_yes(
    mocker, session
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Yes",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": False,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = "Yes"

    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    mock_last_connect = mocker.patch.object(
        workspace_helper, "get_last_known_user_connection_timestamp"
    )
    mock_last_connect.return_value = None
    mocker.patch.object(workspace_utils, "check_if_workspace_used_for_selected_period")
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = False

    mocker.patch.object(
        workspace_helper, "check_if_workspace_available_on_first_day_selected_month"
    )
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = (
        True
    )

    mocker.patch.object(workspace_helper, "check_if_workspace_needs_to_be_terminated")
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = "Yes"

    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ("Yes", None)


def test_get_termination_status_returns_dry_run_for_terminate_workspaces_dry_run(
    mocker, session
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": False,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = "Yes"

    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    mock_last_connect = mocker.patch.object(
        workspace_helper, "get_last_known_user_connection_timestamp"
    )
    test_time = datetime.datetime.now()
    mock_last_connect.return_value = test_time
    mocker.patch.object(workspace_utils, "check_if_workspace_used_for_selected_period")
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = False
    mocker.patch.object(
        workspace_helper, "check_if_workspace_available_on_first_day_selected_month"
    )
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = (
        True
    )
    mocker.patch.object(workspace_helper, "check_if_workspace_needs_to_be_terminated")
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = (
        "Yes - Dry Run"
    )
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ("Yes - Dry Run", time.strftime("%Y-%m-%d", test_time.timetuple()))


def test_get_termination_status_returns_empty_string_when_workspace_used(
    mocker, session
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": True,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = "Yes"

    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    mock_last_connect = mocker.patch.object(
        workspace_helper, "get_last_known_user_connection_timestamp"
    )
    mock_last_connect.return_value = None
    mocker.patch.object(workspace_utils, "check_if_workspace_used_for_selected_period")
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = True

    mocker.patch.object(
        workspace_helper, "check_if_workspace_available_on_first_day_selected_month"
    )
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = (
        True
    )

    mocker.patch.object(workspace_helper, "check_if_workspace_needs_to_be_terminated")
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = (
        "Yes - Dry Run"
    )
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ("", None)


def test_get_termination_status_returns_empty_string_when_workspace_not_available_first_day(
    mocker, session
):
    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Dry Run",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": True,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    workspace_utils.TERMINATE_UNUSED_WORKSPACES = "Yes"

    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    mock_last_connect = mocker.patch.object(
        workspace_helper, "get_last_known_user_connection_timestamp"
    )
    test_time = datetime.datetime.now()
    mock_last_connect.return_value = test_time
    mocker.patch.object(workspace_utils, "check_if_workspace_used_for_selected_period")
    workspace_utils.check_if_workspace_used_for_selected_period.return_value = False

    mocker.patch.object(
        workspace_helper, "check_if_workspace_available_on_first_day_selected_month"
    )
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.return_value = (
        False
    )

    mocker.patch.object(workspace_helper, "check_if_workspace_needs_to_be_terminated")
    workspace_helper.check_if_workspace_needs_to_be_terminated.return_value = (
        "Yes - Dry Run"
    )
    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)
    assert result == ("", time.strftime("%Y-%m-%d", test_time.timetuple()))


def test_get_termination_status_with_billable_hours(mocker, session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "2025-01-01",
            "start_time_selected_date": "2025-01-01T00:00:00Z",
            "end_time_selected_date": "2025-01-02T00:00:00Z",
            "current_month_last_day": True,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    workspace_id = "ws-12345678"
    billable_time = 10
    tags = [{"Key": "TestTag", "Value": "TestValue"}]

    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    mock_timestamp = datetime.datetime(2025, 1, 15, 12, 0, 0)
    mocker.patch.object(
        workspace_helper,
        "get_last_known_user_connection_timestamp",
        return_value=mock_timestamp,
    )
    mocker.patch.object(
        workspace_utils, "is_terminate_workspace_enabled", return_value=True
    )
    mocker.patch.object(
        workspace_helper, "check_if_workspace_available_on_first_day_selected_month"
    )
    mocker.patch.object(workspace_utils, "check_if_workspace_used_for_selected_period")
    mocker.patch.object(workspace_helper, "check_if_workspace_needs_to_be_terminated")

    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)

    assert result == ("", "2025-01-15")
    workspace_helper.is_standby_workspace.assert_called_once_with(workspace_id)
    workspace_helper.get_last_known_user_connection_timestamp.assert_called_once_with(
        workspace_id
    )
    workspace_utils.is_terminate_workspace_enabled.assert_called_once()
    workspace_helper.check_if_workspace_available_on_first_day_selected_month.assert_called_once()
    workspace_utils.check_if_workspace_used_for_selected_period.assert_called_once()
    workspace_helper.check_if_workspace_needs_to_be_terminated.assert_not_called()


def test_get_termination_status_skips_standby_workspace(mocker, session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Yes",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": "",
            "end_time_selected_date": "",
            "current_month_last_day": True,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "ws-standby123"
    billable_time = 0
    tags = []
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    # Mock is_standby_workspace to return True
    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=True)

    # These methods should not be called for standby workspaces
    mock_get_last_connect = mocker.patch.object(
        workspace_helper, "get_last_known_user_connection_timestamp"
    )
    mock_check_workspace_used = mocker.patch.object(
        workspace_utils, "check_if_workspace_used_for_selected_period"
    )
    mock_check_available = mocker.patch.object(
        workspace_helper, "check_if_workspace_available_on_first_day_selected_month"
    )
    mock_check_terminate = mocker.patch.object(
        workspace_helper, "check_if_workspace_needs_to_be_terminated"
    )

    result = workspace_helper.get_termination_status(workspace_id, billable_time, tags)

    assert result == ("", None)
    workspace_helper.is_standby_workspace.assert_called_once_with(workspace_id)
    mock_get_last_connect.assert_not_called()
    mock_check_workspace_used.assert_not_called()
    mock_check_available.assert_not_called()
    mock_check_terminate.assert_not_called()


def test_get_workspaces_for_directory_use_next_token(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Dry Run",
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    expected_params_1 = {"DirectoryId": directory_id}

    response_1 = {"Workspaces": [{"WorkspaceId": "id_1"}], "NextToken": "s223123jj32"}

    expected_params_2 = {"DirectoryId": directory_id, "NextToken": "s223123jj32"}

    response_2 = {"Workspaces": [{"WorkspaceId": "id_2"}]}

    client_stubber.add_response("describe_workspaces", response_1, expected_params_1)
    client_stubber.add_response("describe_workspaces", response_2, expected_params_2)
    client_stubber.activate()
    response = workspace_helper.get_workspaces_for_directory(directory_id)
    client_stubber.activate()
    assert response == [{"WorkspaceId": "id_1"}, {"WorkspaceId": "id_2"}]


def test_get_workspaces_for_directory_no_next_token(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    expected_params_1 = {"DirectoryId": directory_id}

    response_1 = {"Workspaces": [{"WorkspaceId": "id_1"}]}

    expected_params_2 = {"DirectoryId": directory_id, "NextToken": "s223123jj32"}

    response_2 = {"Workspaces": [{"WorkspaceId": "id_2"}]}

    client_stubber.add_response("describe_workspaces", response_1, expected_params_1)
    client_stubber.add_response("describe_workspaces", response_2, expected_params_2)
    client_stubber.activate()
    response = workspace_helper.get_workspaces_for_directory(directory_id)
    client_stubber.activate()
    assert response == [{"WorkspaceId": "id_1"}]


def test_get_workspaces_for_directory_return_empty_list_for_exception(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    directory_id = "123qwe123qwe"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error("describe_workspaces", "Invalid_request")
    client_stubber.activate()
    response = workspace_helper.get_workspaces_for_directory(directory_id)
    client_stubber.activate()
    assert response == []


def test_get_list_tags_for_workspace_returns_list_of_tags(mocker, session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    tags = {"TagList": ["tags"]}
    workspace_id = 1
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    mocker.patch.object(workspace_helper.workspaces_client, "describe_tags")
    workspace_helper.workspaces_client.describe_tags.return_value = tags
    assert workspace_helper.get_list_tags_for_workspace(workspace_id) == ["tags"]


def test_compare_usage_metrics__returns_error_for_billable_time_none(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    new_mode = "ALWAYS_ON"
    expected = {"resultCode": "-E-", "newMode": new_mode}
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    assert workspace_helper.compare_usage_metrics(1, None, None, new_mode) == expected


def test_compare_usage_metrics__returns_skipped_for_hourly_threshold_none(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    new_mode = "ALWAYS_ON"
    expected = {"resultCode": "-S-", "newMode": new_mode}
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    assert workspace_helper.compare_usage_metrics(1, 1, None, new_mode) == expected


def test_get_hourly_threshold_for_bundle_type_returns_correct_value(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": {"value": 85},
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.get_hourly_threshold_for_bundle_type("value")

    assert result is 85


def test_get_hourly_threshold_for_bundle_type(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": {},
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.get_hourly_threshold_for_bundle_type("Value")

    assert result is None


def test_get_list_tags_for_workspace_returns_none_in_case_of_exception(mocker, session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    workspace_id = "ws-abd123"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)
    client_stubber.add_client_error("describe_tags", "Invalid Tags")
    assert workspace_helper.get_list_tags_for_workspace(workspace_id) is None


def test_is_standby_workspace_returns_true_for_standby_workspace(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "ws-standby123"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    response = {
        "Workspaces": [
            {
                "WorkspaceId": workspace_id,
                "RelatedWorkspaces": [
                    {"WorkspaceId": "ws-primary123", "Type": "PRIMARY"}
                ],
            }
        ]
    }
    expected_params = {"WorkspaceIds": [workspace_id]}

    client_stubber.add_response("describe_workspaces", response, expected_params)
    client_stubber.activate()

    result = workspace_helper.is_standby_workspace(workspace_id)

    assert result is True
    client_stubber.deactivate()


def test_is_standby_workspace_returns_false_for_primary_workspace(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "ws-primary123"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    # Response for a primary workspace (no RelatedWorkspaces with PRIMARY type)
    response = {
        "Workspaces": [
            {
                "WorkspaceId": workspace_id,
                "RelatedWorkspaces": [
                    {"WorkspaceId": "ws-standby123", "Type": "STANDBY"}
                ],
            }
        ]
    }
    expected_params = {"WorkspaceIds": [workspace_id]}

    client_stubber.add_response("describe_workspaces", response, expected_params)
    client_stubber.activate()

    result = workspace_helper.is_standby_workspace(workspace_id)

    assert result is False
    client_stubber.deactivate()


def test_is_standby_workspace_returns_false_for_workspace_with_no_related_workspaces(
    session,
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "ws-regular123"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    # Response for a workspace with no RelatedWorkspaces field
    response = {
        "Workspaces": [
            {
                "WorkspaceId": workspace_id
                # No RelatedWorkspaces field
            }
        ]
    }
    expected_params = {"WorkspaceIds": [workspace_id]}

    client_stubber.add_response("describe_workspaces", response, expected_params)
    client_stubber.activate()

    result = workspace_helper.is_standby_workspace(workspace_id)

    assert result is False
    client_stubber.deactivate()


def test_is_standby_workspace_returns_false_for_empty_workspaces_response(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "ws-nonexistent123"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    # Empty response (no workspaces found)
    response = {"Workspaces": []}
    expected_params = {"WorkspaceIds": [workspace_id]}

    client_stubber.add_response("describe_workspaces", response, expected_params)
    client_stubber.activate()

    result = workspace_helper.is_standby_workspace(workspace_id)

    assert result is False
    client_stubber.deactivate()


def test_is_standby_workspace_returns_false_on_exception(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
    }
    workspace_id = "ws-error123"
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    client_stubber = Stubber(workspace_helper.workspaces_client)

    # Adding client error to simulate an exception
    client_stubber.add_client_error("describe_workspaces", "ResourceNotFoundException")
    client_stubber.activate()

    result = workspace_helper.is_standby_workspace(workspace_id)

    assert result is False
    client_stubber.deactivate()


def test_compare_usage_metrics__returns_new_mode_as_auto_stop(session, mocker):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = {"resultCode": "-H-", "newMode": "AUTO_STOP"}
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "compare_usage_metrics_for_auto_stop")
    workspace_helper.compare_usage_metrics_for_auto_stop.return_value = [
        "-H-",
        "AUTO_STOP",
    ]

    assert workspace_helper.compare_usage_metrics(1, 1, 85, "AUTO_STOP") == expected


def test_compare_usage_metrics__returns_new_mode_as_always_on(session, mocker):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = {"resultCode": "-M-", "newMode": "ALWAYS_ON"}
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "compare_usage_metrics_for_always_on")
    workspace_helper.compare_usage_metrics_for_always_on.return_value = [
        "-M-",
        "ALWAYS_ON",
    ]

    assert workspace_helper.compare_usage_metrics(1, 100, 85, "ALWAYS_ON") == expected


def test_compare_usage_metrics__returns_new_mode_same_as_old_mode_for_error(session):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = {"resultCode": "-S-", "newMode": "ALWAYS_ON_Error"}
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    assert (
        workspace_helper.compare_usage_metrics(1, 100, 85, "ALWAYS_ON_Error")
        == expected
    )


def test_compare_usage_metrics_for_auto_stop_returns_always_on_if_billable_time_exceeds_threshold(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-M-", "ALWAYS_ON")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "modify_workspace_properties")
    workspace_helper.modify_workspace_properties.return_value = "-M-"

    assert (
        workspace_helper.compare_usage_metrics_for_auto_stop(
            "ws-112d", 100, 85, "AUTO_STOP"
        )
        == expected
    )


def test_compare_usage_metrics_for_auto_stop_returns_auto_stop_if_billable_time_less_than_threshold(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-N-", "AUTO_STOP")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    assert (
        workspace_helper.compare_usage_metrics_for_auto_stop(
            "ws-112d", 10, 85, "AUTO_STOP"
        )
        == expected
    )


def test_compare_usage_metrics_for_auto_stop_returns_auto_stop_for_api_exception(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-E-", "AUTO_STOP")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "modify_workspace_properties")
    workspace_helper.modify_workspace_properties.return_value = "-E-"

    assert (
        workspace_helper.compare_usage_metrics_for_auto_stop(
            "ws-112d", 100, 85, "AUTO_STOP"
        )
        == expected
    )


def test_compare_usage_metrics_for_always_on_returns_auto_stop_if_billable_time_less_than_threshold(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-H-", "AUTO_STOP")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "modify_workspace_properties")
    workspace_helper.modify_workspace_properties.return_value = "-H-"

    assert (
        workspace_helper.compare_usage_metrics_for_always_on(
            "ws-112d", 10, 85, "ALWAYS_ON"
        )
        == expected
    )


def test_compare_usage_metrics_for_always_on_returns_always_on_if_billable_time_exceeds_threshold(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-N-", "ALWAYS_ON")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    assert (
        workspace_helper.compare_usage_metrics_for_always_on(
            "ws-112d", 100, 85, "ALWAYS_ON"
        )
        == expected
    )


def test_compare_usage_metrics_for_always_on_returns_always_on_for_api_exception(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": True,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-E-", "ALWAYS_ON")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "modify_workspace_properties")
    workspace_helper.modify_workspace_properties.return_value = "-E-"

    assert (
        workspace_helper.compare_usage_metrics_for_always_on(
            "ws-112d", 10, 85, "ALWAYS_ON"
        )
        == expected
    )


def test_compare_usage_metrics_for_always_on_returns_no_change_for_end_of_month_false(
    mocker, session
):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": False,
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "TerminateUnusedWorkspaces": "Dry Run",
    }
    expected = ("-N-", "ALWAYS_ON")
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(workspace_helper, "modify_workspace_properties")
    workspace_helper.modify_workspace_properties.return_value = "-N-"

    assert (
        workspace_helper.compare_usage_metrics_for_always_on(
            "ws-112d", 10, 85, "ALWAYS_ON"
        )
        == expected
    )


def test_check_if_workspace_needs_to_be_terminated_returns_empty_string_for_last_day_month_false(
    session,
):
    # 'terminateUnusedWorkspaces': 'Dry Run'
    # 'isDryRun': True

    start_time = time.strftime("%Y-%m") + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m") + "-02T00:00:00Z"
    settings = {
        "region": "us-east-1",
        "hourlyLimits": 10,
        "testEndOfMonth": "yes",
        "isDryRun": False,
        "startTime": 1,
        "endTime": 2,
        "terminateUnusedWorkspaces": "Yes",
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": start_time,
            "end_time_selected_date": end_time,
            "current_month_last_day": False,
            "date_today": "",
            "date_for_s3_key": "",
        },
    }
    workspace_id = "123qwe123qwe"
    billable_time = 0
    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)
    result = workspace_helper.check_if_workspace_needs_to_be_terminated(
        workspace_id, billable_time
    )
    assert result == ""


@freeze_time("2023-03-31", auto_tick_seconds=86400)
def test_check_if_workspace_used_for_selected_period_returns_true_for_multi_day_processing():
    first_day_selected_month = datetime.datetime(year=2023, month=3, day=1).date()
    last_known_user_connection_timestamp = datetime.datetime.strptime(
        "2023-03-20 19:35:15.524000+00:00", "%Y-%m-%d %H:%M:%S.%f+00:00"
    )
    result = workspace_utils.check_if_workspace_used_for_selected_period(
        last_known_user_connection_timestamp, first_day_selected_month
    )
    assert result is True

    result1 = date_utils.get_first_day_selected_month()
    result2 = date_utils.get_first_day_selected_month()
    assert result2 == datetime.date(2023, 4, 1)

    result = workspace_utils.check_if_workspace_used_for_selected_period(
        last_known_user_connection_timestamp, first_day_selected_month
    )
    assert result is True


def test_process_workspace_sets_workspace_type_correctly(mocker, session, ws_record):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": {"STANDARD": 80},
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": "",
            "end_time_selected_date": "",
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(
        workspace_helper.metrics_helper, "get_billable_hours_and_performance"
    )
    workspace_helper.metrics_helper.get_billable_hours_and_performance.return_value = {
        "billable_hours": 100,
        "performance_metrics": ws_record.performance_metrics,
    }
    mocker.patch.object(
        workspace_helper, "get_list_tags_for_workspace", return_value=[]
    )
    mocker.patch.object(
        workspace_helper, "get_termination_status", return_value=("", "last-known-time")
    )
    mocker.patch.object(
        workspace_helper,
        "compare_usage_metrics",
        return_value={"resultCode": "-N-", "newMode": "AUTO_STOP"},
    )

    # Test case 1: Primary workspace
    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=False)
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)
    assert result.workspace_type == "PRIMARY"

    # Test case 2: Standby workspace
    mocker.patch.object(workspace_helper, "is_standby_workspace", return_value=True)
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)
    assert result.workspace_type == "STANDBY"


def test_process_workspace_with_metrics(mocker, session, ws_record):
    settings = {
        "region": "us-east-1",
        "hourlyLimits": {"STANDARD": 80},
        "testEndOfMonth": "yes",
        "isDryRun": True,
        "startTime": 1,
        "endTime": 2,
        "dateTimeValues": {
            "start_time_for_current_month": "",
            "end_time_for_current_month": "",
            "last_day_current_month": "",
            "first_day_selected_month": "",
            "start_time_selected_date": "",
            "end_time_selected_date": "",
            "current_month_last_day": "",
            "date_today": "",
            "date_for_s3_key": "",
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    mocker.patch.object(
        workspace_helper.metrics_helper, "get_billable_hours_and_performance"
    )
    workspace_helper.metrics_helper.get_billable_hours_and_performance.return_value = {
        "billable_hours": 100,
        "performance_metrics": ws_record.performance_metrics,
    }

    mocker.patch.object(
        workspace_helper, "get_list_tags_for_workspace", return_value=[]
    )
    mocker.patch.object(
        workspace_helper, "get_termination_status", return_value=("", "last-known-time")
    )

    # Test case 1: Hourly to Monthly conversion
    mocker.patch.object(
        workspace_helper,
        "compare_usage_metrics",
        return_value={
            "resultCode": "-M-",
            "newMode": "ALWAYS_ON",
        },
    )

    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)

    assert result.description.bundle_type == "test-bundle"
    assert result.billing_data.billable_hours == 100
    assert result.last_known_user_connection == "last-known-time"
    assert result.billing_data.new_mode == "ALWAYS_ON"
    assert result.billing_data.change_reported == "-M-"
    assert result.performance_metrics == ws_record.performance_metrics

    assert dashboard_metrics.conversion_metrics.hourly_to_monthly == 1
    assert dashboard_metrics.conversion_metrics.monthly_to_hourly == 0
    assert dashboard_metrics.conversion_metrics.conversion_errors == 0
    assert dashboard_metrics.conversion_metrics.conversion_skips == 0
    assert dashboard_metrics.termination_metrics == 0
    assert dashboard_metrics.billing_metrics.monthly_billed == 1
    assert dashboard_metrics.billing_metrics.hourly_billed == 0

    # Test case 2: Monthly to Hourly conversion
    mocker.patch.object(
        workspace_helper,
        "compare_usage_metrics",
        return_value={
            "resultCode": "-H-",
            "newMode": "AUTO_STOP",
        },
    )

    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)

    assert result.billing_data.new_mode == "AUTO_STOP"
    assert result.billing_data.change_reported == "-H-"
    assert dashboard_metrics.conversion_metrics.monthly_to_hourly == 1
    assert dashboard_metrics.billing_metrics.hourly_billed == 1
    assert dashboard_metrics.billing_metrics.monthly_billed == 0

    # Test case 3: Skip convert tag
    tags = [{"Key": "skip_convert", "Value": "True"}]
    mocker.patch.object(
        workspace_helper,
        "get_list_tags_for_workspace",
        return_value=tags,
    )
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)

    assert result.billing_data.change_reported == "-S-"
    assert dashboard_metrics.conversion_metrics.conversion_skips == 1
    assert result.tags == "".join(('"', str(tags), '"'))

    # Test case 4: Error case
    mocker.patch.object(
        workspace_helper, "get_list_tags_for_workspace", return_value=[]
    )
    mocker.patch.object(
        workspace_helper,
        "compare_usage_metrics",
        return_value={
            "resultCode": "-E-",
            "newMode": "AUTO_STOP",
        },
    )
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)

    assert result.billing_data.change_reported == "-E-"
    assert dashboard_metrics.conversion_metrics.conversion_errors == 1

    # Test case 5: Termination case
    mocker.patch.object(
        workspace_helper,
        "get_termination_status",
        return_value=("Yes", "last-known-time"),
    )
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)

    assert result.billing_data.workspace_terminated == "Yes"
    assert dashboard_metrics.termination_metrics == 1

    # Test case 6: No change case
    mocker.patch.object(
        workspace_helper,
        "compare_usage_metrics",
        return_value={
            "resultCode": "-N-",
            "newMode": "AUTO_STOP",
        },
    )
    dashboard_metrics = DashboardMetrics()
    result = workspace_helper.process_workspace(ws_record, 60, dashboard_metrics)

    assert result.billing_data.change_reported == "-N-"
    assert dashboard_metrics.conversion_metrics.hourly_to_monthly == 0
    assert dashboard_metrics.conversion_metrics.monthly_to_hourly == 0


def test_add_maintenance_time_when_conditions_met(session):
    """Test that maintenance time is added when all conditions are met"""
    settings = {
        "region": "us-east-1",
        "dateTimeValues": {
            "current_month_last_day": True,
        },
        "testEndOfMonth": False,
        "directoryInfo": {
            "WorkspaceCreationProperties": {"EnableMaintenanceMode": True}
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    # Test with non-zero billable hours
    result = workspace_helper.add_maintenance_time(
        billable_hours=50, workspace_id="ws-12345", workspace_running_mode="AUTO_STOP"
    )

    assert result == 51  # 50 + 1 hour maintenance time


def test_add_maintenance_time_when_test_end_of_month_true_but_always_on(
    session,
):
    """Test that maintenance time is added when TestEndOfMonth is true"""
    settings = {
        "region": "us-east-1",
        "dateTimeValues": {
            "current_month_last_day": False,
        },
        "testEndOfMonth": True,
        "directoryInfo": {
            "WorkspaceCreationProperties": {"EnableMaintenanceMode": True}
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    result = workspace_helper.add_maintenance_time(
        billable_hours=25, workspace_id="ws-12345", workspace_running_mode="ALWAYS_ON"
    )

    assert result == 25  # No maintenance time added


def test_add_maintenance_time_skips_zero_billable_hours(session):
    """Test that maintenance time is not added to workspaces with zero billable hours"""
    settings = {
        "region": "us-east-1",
        "dateTimeValues": {
            "current_month_last_day": True,
        },
        "testEndOfMonth": False,
        "directoryInfo": {
            "WorkspaceCreationProperties": {"EnableMaintenanceMode": True}
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    result = workspace_helper.add_maintenance_time(
        billable_hours=0, workspace_id="ws-12345", workspace_running_mode="AUTO_STOP"
    )

    assert result == 0  # No maintenance time added to zero billable hours


def test_add_maintenance_time_skips_when_not_last_day_and_not_test_mode(
    session,
):
    """Test that maintenance time is not added when it's not last day and not test mode"""
    settings = {
        "region": "us-east-1",
        "dateTimeValues": {
            "current_month_last_day": False,
        },
        "testEndOfMonth": False,
        "directoryInfo": {
            "WorkspaceCreationProperties": {"EnableMaintenanceMode": True}
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    result = workspace_helper.add_maintenance_time(
        billable_hours=30, workspace_id="ws-12345", workspace_running_mode="AUTO_STOP"
    )

    assert result == 30  # No maintenance time added


def test_add_maintenance_time_skips_when_maintenance_mode_disabled(
    session,
):
    """Test that maintenance time is not added when maintenance mode is disabled"""
    settings = {
        "region": "us-east-1",
        "dateTimeValues": {
            "current_month_last_day": True,
        },
        "testEndOfMonth": False,
        "directoryInfo": {
            "WorkspaceCreationProperties": {"EnableMaintenanceMode": False}
        },
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    result = workspace_helper.add_maintenance_time(
        billable_hours=40, workspace_id="ws-12345", workspace_running_mode="ALWAYS_ON"
    )

    assert result == 40  # No maintenance time added


def test_add_maintenance_time_skips_when_no_directory_info(session):
    """Test that maintenance time is not added when directoryInfo is missing"""
    settings = {
        "region": "us-east-1",
        "dateTimeValues": {
            "current_month_last_day": True,
        },
        "testEndOfMonth": False,
        # No directoryInfo
    }

    workspace_helper = workspaces_helper.WorkspacesHelper(session, settings)

    result = workspace_helper.add_maintenance_time(
        billable_hours=20, workspace_id="ws-12345", workspace_running_mode="ALWAYS_ON"
    )

    assert result == 20  # No maintenance time added
