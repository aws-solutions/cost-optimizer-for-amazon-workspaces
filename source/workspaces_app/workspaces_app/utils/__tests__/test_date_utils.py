#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import datetime
import time
from unittest import mock

# Third Party Libraries
from freezegun import freeze_time

# Cost Optimizer for Amazon Workspaces
from .. import date_utils


@mock.patch(
    "time.gmtime",
    mock.MagicMock(return_value=time.struct_time((2020, 11, 30, 0, 0, 0, 3, 335, -1))),
)
def test_get_report_time_for_s3_key_returns_correct_s3_key():
    result = date_utils.get_report_time_for_s3_key()
    assert result == "2020/11/30/"


@freeze_time("2020-05-14 03:21:34")
def test_get_first_day_selected_month_returns_first_day_selected_month():
    result = date_utils.get_first_day_selected_month()
    assert result == datetime.date(2020, 5, 1)


@freeze_time("2020-05-14 03:21:34")
def test_get_start_end_time_first_day_selected_month_returns_start_end_time_current_month():
    result = date_utils.get_start_end_time_first_day_selected_month()
    assert result == ("2020-05-01T00:00:00Z", "2020-05-02T00:00:00Z")


@freeze_time("2020-05-14 03:21:34")
def test_get_start_end_time_first_day_selected_month_returns_start_end_time_for_older_month():
    date_utils.NUMBER_OF_MONTHS = 4
    result = date_utils.get_start_end_time_first_day_selected_month()
    assert result == ("2020-02-01T00:00:00Z", "2020-02-02T00:00:00Z")


@mock.patch(
    "time.gmtime",
    mock.MagicMock(return_value=time.struct_time((2020, 11, 30, 0, 0, 0, 3, 335, -1))),
)
def test_is_last_day_current_month_returns_true():
    result = date_utils.is_last_day_current_month()
    assert result is True


@mock.patch(
    "time.gmtime",
    mock.MagicMock(return_value=time.struct_time((2020, 11, 29, 0, 0, 0, 3, 335, -1))),
)
def test_is_last_day_current_month_returns_false():
    result = date_utils.is_last_day_current_month()
    assert result is False


@mock.patch(
    "time.gmtime",
    mock.MagicMock(return_value=time.struct_time((2020, 11, 29, 0, 0, 0, 3, 335, -1))),
)
def test_get_date_for_today_returns_today_date():
    result = date_utils.get_date_for_today()
    assert result == "11/29/20"


@freeze_time("2020-11-29 03:21:34")
@mock.patch(
    "time.gmtime",
    mock.MagicMock(return_value=time.struct_time((2020, 11, 29, 0, 0, 0, 3, 335, -1))),
)
def test_get_date_time_values_for_processing_returns_all_the_correct_values():
    date_utils.NUMBER_OF_MONTHS = 1
    result = date_utils.get_date_time_values_for_processing()
    assert result == {
        "start_time_for_current_month": "2020-11-01T00:00:00Z",
        "end_time_for_current_month": "2020-11-29T00:00:00Z",
        "last_day_current_month": 30,
        "first_day_selected_month": datetime.date(2020, 11, 1),
        "start_time_selected_date": "2020-11-01T00:00:00Z",
        "end_time_selected_date": "2020-11-02T00:00:00Z",
        "current_month_last_day": False,
        "date_today": "11/29/20",
        "date_for_s3_key": "2020/11/29/",
    }


@freeze_time("2020-05-31 23:00:00", auto_tick_seconds=86400)
def test_get_first_day_selected_month_returns_first_day_selected_month_then_returns_next_month_date():
    result = date_utils.get_first_day_selected_month()
    assert result == datetime.date(2020, 5, 1)
    result = date_utils.get_first_day_selected_month()
    assert result == datetime.date(2020, 6, 1)
