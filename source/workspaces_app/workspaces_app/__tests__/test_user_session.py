#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Third Party Libraries
import pytest

# Cost Optimizer for Amazon Workspaces
from ..user_session import *

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def user_session_timestamps_factory(length: int) -> list[datetime]:
    time = datetime(2024, 1, 1, 12, 0, 0)
    timestamps = []
    for i in range(length):
        timestamps.append(time)
        time = time + timedelta(minutes=5)
    return timestamps


def convert_time_to_string(session_time: datetime) -> str:
    return session_time.strftime(TIME_FORMAT)


def get_session_time(session: list[datetime]) -> str:
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


def test_user_session_to_ddb_item(user_session, ddb_item):
    result = user_session.to_ddb_obj()

    assert result == ddb_item


def test_from_json(user_session):
    class_as_json = asdict(user_session)
    del class_as_json["session_time"]

    new_user_session = UserSession.from_json(class_as_json)

    assert user_session == new_user_session


def test_class_field_to_ddb_attr_with_underscore():
    test_string = "test_string"

    result = UserSession.class_field_to_ddb_attr(test_string)

    assert result == "TestString"


def test_class_field_to_ddb_attr_without_underscore():
    test_string = "teststring"

    result = UserSession.class_field_to_ddb_attr(test_string)

    assert result == "Teststring"


def test_ddb_attr_to_class_field():
    test_string = "TestString"

    result = UserSession.ddb_attr_to_class_field(test_string)

    assert result == "test_string"


def test_ddb_attr_to_class_field_with_caps():
    test_string = "TESTString"

    result = UserSession.ddb_attr_to_class_field(test_string)

    assert result == "test_string"
