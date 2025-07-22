#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import datetime
import math
import os
from decimal import Decimal
from statistics import mean
from unittest import mock

# Third Party Libraries
import pytest
from dateutil.tz import tzlocal, tzutc

# AWS Libraries
import boto3
from botocore.stub import Stubber

# Cost Optimizer for Amazon Workspaces
from ..metrics_helper import MetricsHelper, get_autostop_timeout_hours
from ..user_session import UserSession
from ..workspace_record import *

METRIC_LIST = [
    "UserConnected",
    "InSessionLatency",
    "CPUUsage",
    "MemoryUsage",
    "RootVolumeDiskUsage",
    "UserVolumeDiskUsage",
    "UDPPacketLossRate",
]


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
def weighted_avg():
    return WeightedAverage(Decimal("93.42"), 67)


@pytest.fixture()
def ws_metrics():
    return WorkspacePerformanceMetrics(
        in_session_latency=WeightedAverage(Decimal("93.42"), 67),
        cpu_usage=WeightedAverage(Decimal("94.42"), 68),
        memory_usage=WeightedAverage(Decimal("0"), 69),
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
        tags="[{'key1': 'tag1'}, {'key2': 'tag2'}]",
        workspace_type="PRIMARY",
    )


@pytest.fixture()
def metric_data():
    return {
        "userconnected": {"timestamps": [], "values": [1, 0, 0, 0, 1, 0, 0]},
        "cpuusage": {"timestamps": [], "values": [1, 2, 3]},
        "memoryusage": {"timestamps": [], "values": [1, 4, 10]},
        "insessionlatency": {"timestamps": [], "values": [2, 5, 11]},
        "rootvolumediskusage": {"timestamps": [], "values": [5, 8, 14]},
        "uservolumediskusage": {"timestamps": [], "values": [4, 7, 13]},
        "udppacketlossrate": {"timestamps": [], "values": []},
    }


def user_session_factory(
    active_sessions=[
        datetime.datetime(2024, 1, 1, 12, 0, 0),
        datetime.datetime(2024, 1, 1, 12, 5, 0),
    ],
    duration_hours=1,
    in_session_latency=Decimal("93.42"),
    cpu_usage=Decimal("94.42"),
    memory_usage=Decimal("0"),
    root_volume_disk_usage=Decimal("96.42"),
    user_volume_disk_usage=Decimal("97.42"),
    udp_packet_loss_rate=Decimal("98.42"),
):
    return UserSession(
        workspace_id="test-id",
        directory_id="test-id",
        region="test-region",
        account="test-account",
        username="test-username",
        active_sessions=active_sessions,
        duration_hours=duration_hours,
        in_session_latency=in_session_latency,
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        root_volume_disk_usage=root_volume_disk_usage,
        user_volume_disk_usage=user_volume_disk_usage,
        udp_packet_loss_rate=udp_packet_loss_rate,
    )


@mock.patch.dict(os.environ, {"AutoStopTimeoutHours": str(12)})
def test_get_autostop_timeout_hours():
    assert get_autostop_timeout_hours() == 12


@mock.patch.dict(os.environ, {}, clear=True)
def test_get_autostop_timeout_hours_not_set():
    with pytest.raises(TypeError):
        get_autostop_timeout_hours()


@mock.patch.dict(os.environ, {"AutoStopTimeoutHours": "garbage"})
def test_get_autostop_timeout_hours_invalid():
    with pytest.raises(ValueError):
        get_autostop_timeout_hours()


@pytest.fixture(scope="module")
def session():
    yield boto3.session.Session()


def user_connected_data_factory(indices, length):
    user_connected_data = []
    for i in range(length):
        if i in indices:
            user_connected_data.append(1)
        else:
            user_connected_data.append(0)
    return user_connected_data


def performance_metric_factory(length, start):
    metric_data = []
    value = start
    for i in range(length):
        metric_data.append(value)
        value += 1
    return metric_data


def metric_data_factory(indices, length, start):
    metrics = {}
    user_connected_timestamps = user_session_timestamps_factory(length)
    timestamps = user_session_timestamps_factory(length)
    for metric in METRIC_LIST:
        if metric == "UserConnected":
            data = user_connected_data_factory(indices, length)
            metrics[metric.lower()] = {
                "timestamps": user_connected_timestamps,
                "values": data,
            }
        else:
            data = performance_metric_factory(length, start)
            metrics[metric.lower()] = {"timestamps": timestamps, "values": data}
    return metrics


def user_session_timestamps_factory(length):
    time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    timestamps = []
    for i in range(length):
        timestamps.append(time)
        time = time + datetime.timedelta(minutes=5)
    return timestamps


def expected_sessions_factory(user_session_data, active_indices, zero_limit):
    expected_sessions = []
    duration_hours = 0
    expected_avg = None
    description = ws_description()
    session_description = {
        "workspace_id": description.workspace_id,
        "directory_id": description.directory_id,
        "region": description.region,
        "account": description.account,
        "username": description.username,
    }
    session = {**session_description}
    for i, active_index in enumerate(active_indices):
        if i > 0 and active_index - active_indices[i - 1] > zero_limit:
            duration_hours = math.ceil(
                (session["active_sessions"][-1] - session["active_sessions"][0]).seconds
                / 3600
            )
            session |= {
                "duration_hours": duration_hours or 1,
                **{
                    UserSession.ddb_attr_to_class_field(metric): Decimal(
                        round(expected_avg.avg, 2)
                    )
                    for metric in METRIC_LIST
                    if metric != "UserConnected"
                    and user_session_data[metric.lower()]["values"]
                },
            }
            expected_sessions.append(UserSession.from_json(session))
            session = {**session_description}
            session["active_sessions"] = [
                user_session_data["cpuusage"]["timestamps"][active_index]
            ]
            expected_avg = WeightedAverage(
                user_session_data["cpuusage"]["values"][active_index], 1
            )
        else:
            session.setdefault("active_sessions", []).append(
                user_session_data["cpuusage"]["timestamps"][active_index]
            )
            current_avg = WeightedAverage(
                user_session_data["cpuusage"]["values"][active_index], 1
            )
            expected_avg = (
                current_avg.merge(expected_avg)
                if expected_avg is not None
                else current_avg
            )
    if session:
        duration_hours = math.ceil(
            (session["active_sessions"][-1] - session["active_sessions"][0]).seconds
            / 3600
        )
        session |= {
            "duration_hours": duration_hours or 1,
            **{
                UserSession.ddb_attr_to_class_field(metric): Decimal(
                    round(expected_avg.avg, 2)
                )
                for metric in METRIC_LIST
                if metric != "UserConnected"
                and user_session_data[metric.lower()]["values"]
            },
        }
        expected_sessions.append(UserSession.from_json(session))

    return expected_sessions


def test_get_user_connected_hours(session, ws_record):
    region = "us-east-1"
    list_user_sessions = [user_session_factory()]
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_user_connected_hours(
        list_user_sessions,
        ws_record.description.workspace_id,
        ws_record.description.initial_mode,
        60,
        None,
    )
    assert result == 2  # add in timeout hours


def test_get_user_connected_hours_with_last_report(session, ws_record):
    region = "us-east-1"
    list_user_sessions = [user_session_factory()]
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_user_connected_hours(
        list_user_sessions,
        ws_record.description.workspace_id,
        ws_record.description.initial_mode,
        60,
        ws_record.billing_data.billable_hours,
    )
    assert result == 2 + ws_record.billing_data.billable_hours


def test_get_user_connected_hours_adds_autostop_hours(session, ws_record):
    region = "us-east-1"
    list_user_sessions = [
        user_session_factory(duration_hours=1),
        user_session_factory(duration_hours=2),
    ]
    autostop_minutes = 120  # 2 hours
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_user_connected_hours(
        list_user_sessions,
        ws_record.description.workspace_id,
        ws_record.description.initial_mode,
        autostop_minutes,
        ws_record.billing_data.billable_hours,
    )
    assert result == 7 + ws_record.billing_data.billable_hours


def test_get_user_connected_hours_0_hours(session, ws_record):
    region = "us-east-1"
    list_user_sessions = []
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_user_connected_hours(
        list_user_sessions,
        ws_record.description.workspace_id,
        ws_record.description.initial_mode,
        60,
        ws_record.billing_data.billable_hours,
    )
    assert result == 0 + ws_record.billing_data.billable_hours


@mock.patch(
    get_autostop_timeout_hours.__module__ + ".get_autostop_timeout_hours",
    return_value=1,
)
def test_get_user_connected_hours_0_hours_always_on(session, ws_record):
    region = "us-east-1"
    list_user_sessions = [
        user_session_factory(),
        user_session_factory(),
        user_session_factory(),
    ]
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_user_connected_hours(
        list_user_sessions,
        ws_record.description.workspace_id,
        ws_record.description.initial_mode,
        60,
        ws_record.billing_data.billable_hours,
    )
    assert result == 6 + ws_record.billing_data.billable_hours


def test_get_list_data_points(session):
    region = "us-east-1"
    list_metric_data_points = [
        {
            "Id": "userconnected",
            "Timestamps": [
                datetime.datetime(2021, 5, 2, 1, 5, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 1, 10, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 20, 40, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 11, 50, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 12, 15, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 3, 25, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 23, 0, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 14, 10, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 9, 55, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 18, 5, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 13, 40, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 4, 50, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 0, 35, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 15, 45, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 11, 20, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 2, 55, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 17, 35, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 8, 45, tzinfo=tzlocal()),
            ],
            "Values": [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
                1.0,
                0.0,
                1.0,
                0.0,
                0.0,
            ],
        },
        {
            "Id": "cpuusage",
            "Timestamps": [
                datetime.datetime(2021, 5, 2, 1, 5, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 1, 10, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 20, 40, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 11, 50, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 12, 15, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 3, 25, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 23, 0, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 14, 10, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 9, 55, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 18, 5, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 13, 40, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 4, 50, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 0, 35, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 15, 45, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 11, 20, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 2, 2, 55, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 17, 35, tzinfo=tzlocal()),
                datetime.datetime(2021, 5, 1, 8, 45, tzinfo=tzlocal()),
            ],
            "Values": [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
                1.0,
                0.0,
                1.0,
                0.0,
                0.0,
            ],
        },
    ]
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_list_data_points(list_metric_data_points)
    assert result == {
        "userconnected": {
            "timestamps": list_metric_data_points[0].get("Timestamps"),
            "values": list_metric_data_points[0].get("Values"),
        },
        "cpuusage": {
            "timestamps": list_metric_data_points[1].get("Timestamps"),
            "values": list_metric_data_points[1].get("Values"),
        },
    }


def test_get_time_range_when_no_last_reported_time(session):
    region = "us-east-1"
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-20T13:16:11Z"
    last_reported_time = None
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_time_range(start_time, end_time, last_reported_time)
    assert result == {
        "end_time": "2021-05-20T13:16:11Z",
        "start_time": "2021-05-01T00:00:00Z",
    }


def test_get_time_range_with_last_reported_time(session):
    region = "us-east-1"
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-20T13:16:11Z"
    last_reported_time = "2021-05-19T13:16:11Z"
    metrics_helper = MetricsHelper(session, region, "test-table")
    result = metrics_helper.get_time_range(start_time, end_time, last_reported_time)
    assert result == {
        "end_time": "2021-05-20T13:16:11Z",
        "start_time": "2021-05-19T13:16:11Z",
    }


def test_get_cloudwatch_metric_data_points(session):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    client_stubber = Stubber(metrics_helper.client)
    client_stubber2 = Stubber(metrics_helper.client)
    workspace_id = "123qwer"
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-06T00:00:00Z"
    time_range = {
        "end_time": end_time,
        "start_time": start_time,
    }

    response = {
        "MetricDataResults": [
            {
                "Id": "userconnected",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "Id": "insessionlatency",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "Id": "cpuusage",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "Id": "memoryusage",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "Id": "rootvolumediskusage",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "Id": "uservolumediskusage",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
            {
                "Id": "udppacketlossrate",
                "Timestamps": [
                    datetime.datetime(2021, 5, 2, 11, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 7, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 6, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 1, 2, 0, tzinfo=tzutc()),
                    datetime.datetime(2021, 5, 2, 1, 0, tzinfo=tzutc()),
                ],
                "Values": [
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                    0.0,
                ],
            },
        ],
        "NextToken": "next-token",
    }
    metric_queries = [
        metrics_helper.build_query(metric, workspace_id) for metric in METRIC_LIST
    ]
    expected_params = {
        "MetricDataQueries": metric_queries,
        "StartTime": start_time,
        "EndTime": end_time,
        "ScanBy": "TimestampAscending",
        "MaxDatapoints": 100800,
    }
    expected_result = response.get("MetricDataResults")
    client_stubber.add_response("get_metric_data", response, expected_params)
    del response["NextToken"]
    expected_result.extend(response.get("MetricDataResults"))
    client_stubber2.add_response("get_metric_data", response, expected_params)
    client_stubber.activate()
    client_stubber2.activate()
    result = metrics_helper.get_cloudwatch_metric_data_points(workspace_id, time_range)
    assert result == expected_result


def test_get_cloudwatch_metric_data_points_empty_list(session):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    client_stubber = Stubber(metrics_helper.client)
    workspace_id = "123qwer"
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-06T00:00:00Z"
    time_range = {
        "end_time": end_time,
        "start_time": start_time,
    }
    response = {"MetricDataResults": []}
    metric_queries = [
        metrics_helper.build_query(metric, workspace_id) for metric in METRIC_LIST
    ]
    expected_params = {
        "MetricDataQueries": metric_queries,
        "StartTime": start_time,
        "EndTime": end_time,
        "ScanBy": "TimestampAscending",
        "MaxDatapoints": 100800,
    }
    client_stubber.add_response("get_metric_data", response, expected_params)
    client_stubber.activate()
    result = metrics_helper.get_cloudwatch_metric_data_points(workspace_id, time_range)
    assert result == []


def test_get_cloudwatch_metric_data_points_none(session):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    client_stubber = Stubber(metrics_helper.client)
    workspace_id = "123qwer"
    time_range = {
        "end_time": "2021-05-06T00:00:00Z",
        "start_time": "2021-05-01T00:00:00Z",
    }

    client_stubber.add_client_error("get_metric_data", "InvalidRequest")
    client_stubber.activate()
    result = metrics_helper.get_cloudwatch_metric_data_points(workspace_id, time_range)
    assert result is None


def test_get_billable_hours_and_performance(mocker, session, ws_record, metric_data):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-06T00:00:00Z"

    mocker.patch.object(
        metrics_helper,
        "get_time_range",
        return_value={"start_time": start_time, "end_time": end_time},
    )
    mocker.patch.object(metrics_helper, "get_cloudwatch_metric_data_points")
    mocker.patch.object(
        metrics_helper, "get_list_data_points", return_value=metric_data
    )
    mocker.patch.object(metrics_helper, "get_user_connected_hours", return_value=100)
    mock_user_session = mocker.patch.object(metrics_helper, "get_user_sessions")
    mocker.patch.object(metrics_helper.session_table, "update_ddb_items"),
    spy_get_time_range = mocker.spy(metrics_helper, "get_time_range")
    spy_get_cloudwatch_metric_data_points = mocker.spy(
        metrics_helper, "get_cloudwatch_metric_data_points"
    )
    spy_get_list_data_points = mocker.spy(metrics_helper, "get_list_data_points")
    spy_get_user_connected_hours = mocker.spy(
        metrics_helper, "get_user_connected_hours"
    )
    spy_get_user_sessions = mocker.spy(metrics_helper, "get_user_sessions")

    metrics_helper.get_billable_hours_and_performance(
        start_time, end_time, ws_record, 60
    )

    spy_get_time_range.assert_called_once_with(
        start_time, end_time, ws_record.last_reported_metric_period
    )
    spy_get_cloudwatch_metric_data_points.assert_called_once()
    spy_get_list_data_points.assert_called_once()
    spy_get_user_connected_hours.assert_called_once_with(
        mock_user_session(),
        ws_record.description.workspace_id,
        ws_record.description.initial_mode,
        60,
        ws_record.billing_data.billable_hours,
    )
    spy_get_user_sessions.assert_called_once()


def test_get_billable_hours_and_performance_when_no_previous_report(
    mocker, session, ws_record, metric_data
):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-06T00:00:00Z"

    mocker.patch.object(
        metrics_helper,
        "get_time_range",
        return_value={"start_time": start_time, "end_time": end_time},
    )
    mocker.patch.object(metrics_helper, "get_cloudwatch_metric_data_points")
    mocker.patch.object(
        metrics_helper, "get_list_data_points", return_value=metric_data
    )
    mocker.patch.object(metrics_helper, "get_user_connected_hours", return_value=100)
    mocker.patch.object(metrics_helper, "get_user_sessions")
    mocker.patch.object(
        metrics_helper,
        "process_performance_metrics",
        return_value=ws_record.performance_metrics,
    )
    mocker.patch.object(metrics_helper.session_table, "update_ddb_items"),
    spy_get_time_range = mocker.spy(metrics_helper, "get_time_range")
    spy_get_cloudwatch_metric_data_points = mocker.spy(
        metrics_helper, "get_cloudwatch_metric_data_points"
    )
    spy_get_list_data_points = mocker.spy(metrics_helper, "get_list_data_points")
    spy_get_user_connected_hours = mocker.spy(
        metrics_helper, "get_user_connected_hours"
    )
    spy_get_user_sessions = mocker.spy(metrics_helper, "get_user_sessions")

    result = metrics_helper.get_billable_hours_and_performance(
        start_time, end_time, ws_record.description, 60
    )

    spy_get_time_range.assert_called_with(start_time, end_time, None)
    spy_get_cloudwatch_metric_data_points.assert_called_once()
    spy_get_list_data_points.assert_called_once()
    spy_get_user_connected_hours.assert_called_once()
    spy_get_user_sessions.assert_called_once()

    assert result == {
        "billable_hours": 100,
        "performance_metrics": ws_record.performance_metrics,
    }


def test_get_billable_hours_and_performance_none(mocker, session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    start_time = "2021-05-01T00:00:00Z"
    end_time = "2021-05-06T00:00:00Z"
    last_workspace_report = {}

    mocker.patch.object(
        metrics_helper,
        "get_time_range",
        return_value={"start_time": start_time, "end_time": end_time},
    )
    mocker.patch.object(metrics_helper, "get_cloudwatch_metric_data_points")
    metrics_helper.get_cloudwatch_metric_data_points.return_value = None
    mocker.patch.object(metrics_helper, "get_list_data_points")
    mocker.patch.object(metrics_helper, "get_user_connected_hours")
    mocker.patch.object(metrics_helper, "get_user_sessions")

    spy_get_time_range = mocker.spy(metrics_helper, "get_time_range")
    spy_get_cloudwatch_metric_data_points = mocker.spy(
        metrics_helper, "get_cloudwatch_metric_data_points"
    )
    spy_get_list_data_points = mocker.spy(metrics_helper, "get_list_data_points")
    spy_get_user_connected_hours = mocker.spy(
        metrics_helper, "get_user_connected_hours"
    )
    spy_get_user_sessions = mocker.spy(metrics_helper, "get_user_sessions")

    result = metrics_helper.get_billable_hours_and_performance(
        start_time, end_time, ws_record, last_workspace_report
    )

    spy_get_time_range.assert_called_once()
    spy_get_cloudwatch_metric_data_points.assert_called_once()
    spy_get_list_data_points.assert_not_called()
    spy_get_user_connected_hours.assert_not_called()
    spy_get_user_sessions.assert_not_called()

    assert result == None


def test_get_user_sessions(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 1, 4]
    total_values = 26
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    user_session_data["userconnected"]["timestamps"][-1] += datetime.timedelta(
        minutes=5
    )
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )

    expected_user_sessions = expected_sessions_factory(
        user_session_data, active_indices, 12
    )
    assert result == expected_user_sessions


def test_get_user_sessions_1(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 1, 4, 25]
    total_values = 26
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_sessions = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_sessions


def test_get_user_sessions_2(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0]
    total_values = 1
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_3(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = []
    total_values = 1
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    assert result == []


def test_get_user_sessions_4(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 1]
    total_values = 2
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)

    assert result == expected_result


def test_get_user_sessions_5(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = []
    total_values = 2
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    assert result == []


def test_get_user_sessions_6(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0]
    total_values = 2
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_7(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [1]
    total_values = 2
    start_value = 1
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_8(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [1, 14]
    total_values = 16
    start_value = 5
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    list_user_session_data_points = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_9(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [1, 15]
    total_values = 16
    start_value = 5
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_10(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [1, 13, 15]
    total_values = 16
    start_value = 5
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_11(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [15]
    total_values = 16
    start_value = 5
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_12(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = []
    total_values = 17
    start_value = 5
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    assert result == []


def test_get_user_sessions_13(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [1, 3, 4, 5, 7, 9]
    total_values = 17
    start_value = 523
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_14(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [i for i in range(40)]
    total_values = 40
    start_value = 523
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_15(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 11, 14, 28]
    total_values = 29
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_16(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 11, 14, 28, 51, 52, 53, 54, 55, 56]
    total_values = 57
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    assert result == expected_result


def test_get_user_sessions_17(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [
        0,
        11,
        14,
        28,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        59,
        60,
        61,
        62,
        63,
        74,
        75,
        76,
        77,
        78,
        79,
    ]
    total_values = 81
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    assert result == expected_result


def test_get_user_sessions_18(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 11, 14, 28, 47, 48, 49, 50, 51, 65, 75]
    total_values = 76
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    assert result == expected_result


def test_get_user_sessions_19(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 11, 14, 28, 47, 48, 49, 50, 51, 65, 75]
    total_values = 76
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    user_session_data["memoryusage"]["timestamps"] = []  # test with missing data
    user_session_data["memoryusage"]["values"] = []
    expected_result = expected_sessions_factory(user_session_data, active_indices, 24)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        120,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [7]


def test_get_user_sessions_20(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 17]
    total_values = 18
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 24)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        120,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [2]


def test_get_user_sessions_21(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 28]
    total_values = 29
    start_value = 10
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 24)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        120,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [1, 1]


def test_get_user_sessions_22(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 13, 28]
    total_values = 29
    start_value = 8
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 24)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        120,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [3]


def test_get_user_sessions_23(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 13, 28, 58]
    total_values = 60
    start_value = 8
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 24)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        120,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [3, 1]


def test_get_user_sessions_24(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [13, 28, 58]
    total_values = 60
    start_value = 8
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 24)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        120,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [2, 1]


def test_get_user_sessions_25(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [13, 28, 58]
    total_values = 60
    start_value = 8
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 60)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        300,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [4]


def test_get_user_sessions_26(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0]
    total_values = 57
    start_value = 8
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 60)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        300,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [1]


def test_get_user_sessions_27(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 56]
    total_values = 57
    start_value = 12
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 60)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        300,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [5]


def test_get_user_sessions_28(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 72]
    total_values = 73
    start_value = 12
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 60)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        300,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [1, 1]


@mock.patch(
    get_autostop_timeout_hours.__module__ + ".get_autostop_timeout_hours",
    return_value=1,
)
def test_get_user_sessions_29(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 43]
    total_values = 44
    start_value = 12
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [1, 1]


@mock.patch(
    get_autostop_timeout_hours.__module__ + ".get_autostop_timeout_hours",
    return_value=1,
)
def test_get_user_sessions_30(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 3, 5, 7, 9, 43]
    total_values = 44
    start_value = 12
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [1, 1]


@mock.patch(
    get_autostop_timeout_hours.__module__ + ".get_autostop_timeout_hours",
    return_value=1,
)
def test_get_user_sessions_31(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 3, 5, 7, 9, 21, 33, 43]
    total_values = 44
    start_value = 81
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [4]


@mock.patch(
    get_autostop_timeout_hours.__module__ + ".get_autostop_timeout_hours",
    return_value=1,
)
def test_get_user_sessions_32(session, ws_record):
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    active_indices = [0, 3, 5, 7, 9, 21, 43]
    total_values = 44
    start_value = 81
    user_session_data = metric_data_factory(active_indices, total_values, start_value)
    expected_result = expected_sessions_factory(user_session_data, active_indices, 12)
    result = metrics_helper.get_user_sessions(
        user_session_data,
        ws_description(),
        ws_record.description.initial_mode,
        60,
    )
    expected_hours = [session.duration_hours for session in result]
    assert result == expected_result
    assert expected_hours == [2, 1]


def test_process_performance_metrics(session, ws_record, metric_data):
    metrics_helper = MetricsHelper(session, "us-east-1", "test-table")
    current_weighted_avg = mean(metric_data["cpuusage"]["values"]) * 3
    previous_weighted_avg = ws_record.performance_metrics.cpu_usage.weighted_avg()
    expected_avg = Decimal(
        (current_weighted_avg + previous_weighted_avg)
        / (ws_record.performance_metrics.cpu_usage.count + 3),
    )
    result = metrics_helper.process_performance_metrics(
        metric_data, ws_record.performance_metrics
    )

    assert result.cpu_usage.avg == expected_avg
    assert result.cpu_usage.count == 3 + ws_record.performance_metrics.cpu_usage.count


def test_process_performance_metrics_with_no_available_data_in_last_report(
    session, metric_data
):
    metrics_helper = MetricsHelper(session, "us-east-1", "test-table")

    result = metrics_helper.process_performance_metrics(metric_data, None)

    # test when current data does exist
    assert result.cpu_usage.avg == Decimal("2")
    assert result.cpu_usage.count == 3
    assert result.memory_usage.avg == Decimal("5")
    assert result.memory_usage.count == 3

    # test when current data doesn't exist
    assert result.udp_packet_loss_rate == None


def test_process_performance_metrics_with_zero_avg(session, ws_record, metric_data):
    metrics_helper = MetricsHelper(session, "us-east-1", "test-table")
    for data in metric_data:
        metric_data[data]["values"] = [0, 0]
    result = metrics_helper.process_performance_metrics(
        metric_data, ws_record.performance_metrics
    )
    assert result.memory_usage.avg == Decimal("0")
    assert result.memory_usage.count == 71


def test_apply_hours_increment_cap_returns_unchanged_when_within_limit(
    session, ws_record
):
    """Test that billable hours are unchanged when within increment limit"""
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    ws_record.billing_data = WorkspaceBillingData(billable_hours=50)
    time_range = {
        "start_time": "2024-01-01T10:00:00Z",
        "end_time": "2024-01-01T20:00:00Z",
    }
    result = metrics_helper.apply_hours_increment_cap(
        billable_hours=55, ws_record=ws_record, time_range=time_range
    )

    assert result == 55


def test_apply_hours_increment_cap_caps_when_exceeding_limit(session, ws_record):
    """Test that billable hours are capped when exceeding increment limit"""
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")
    ws_record.billing_data = WorkspaceBillingData(billable_hours=100)
    time_range = {
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z",
    }
    result = metrics_helper.apply_hours_increment_cap(
        billable_hours=150, ws_record=ws_record, time_range=time_range
    )

    assert result == 124


def test_apply_hours_increment_cap_handles_zero_previous_hours(session):
    """Test increment cap when there are no previous billable hours"""
    region = "us-east-1"
    metrics_helper = MetricsHelper(session, region, "test-table")

    # Use WorkspaceDescription (no previous billing data)
    ws_description = WorkspaceDescription(
        region="us-east-1",
        account="123456789012",
        workspace_id="ws-12345678",
        directory_id="d-12345",
        usage_threshold=80,
        bundle_type="STANDARD",
        username="testuser",
        computer_name="testcomputer",
        initial_mode="AUTO_STOP",
    )
    time_range = {
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-03T00:00:00Z",
    }
    result = metrics_helper.apply_hours_increment_cap(
        billable_hours=60, ws_record=ws_description, time_range=time_range
    )

    assert result == 48
