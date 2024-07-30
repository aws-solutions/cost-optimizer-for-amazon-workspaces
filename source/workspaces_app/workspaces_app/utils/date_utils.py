#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import calendar
import datetime
import os
import time

# Third Party Libraries
from dateutil.relativedelta import relativedelta

# set the default duration for termination check as 1 month
NUMBER_OF_MONTHS = os.getenv("NumberOfMonthsForTerminationCheck", 1)
YEAR_MONTH_STRING = "%Y-%m"

# AWS Libraries
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="date_utils")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)


def get_first_day_selected_month():
    relative_date = datetime.datetime.now(datetime.timezone.utc) - relativedelta(
        months=int(NUMBER_OF_MONTHS) - 1
    )
    first_date_selected_month = relative_date.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).date()
    logger.debug(f"First day of selected month is {first_date_selected_month}")
    return first_date_selected_month


def get_start_end_time_first_day_selected_month():
    """
    This function returns start and end time for the first day of the selected month based on customer input
    """
    first_date_selected_month = get_first_day_selected_month()
    star_time_selected_date = (
        first_date_selected_month.strftime(YEAR_MONTH_STRING) + "-01T00:00:00Z"
    )
    end_time_selected_date = (
        first_date_selected_month.strftime(YEAR_MONTH_STRING) + "-02T00:00:00Z"
    )
    logger.debug(
        f"Start time for first day of selected month is {star_time_selected_date}"
    )
    logger.debug(
        f"End time for first day of selected month is {end_time_selected_date}"
    )
    return star_time_selected_date, end_time_selected_date


def is_last_day_current_month():
    """
    This function returns true if today is the last day of month, else returns false
    """
    today = int(time.strftime("%d", time.gmtime()))
    last_day = calendar.monthrange(
        int(time.strftime("%Y", time.gmtime())), int(time.strftime("%m", time.gmtime()))
    )[1]
    logger.debug(f"Today is {today}")
    logger.debug(f"Today is {today}")
    logger.debug(f"Last day of month is {last_day}")
    return today == last_day


def get_date_for_today():
    date_for_today = time.strftime("%D", time.gmtime())
    logger.info(f"Returning today date as {date_for_today}")
    return date_for_today


def get_date_time_values_for_processing():
    start_time = time.strftime("%Y-%m", time.gmtime()) + "-01T00:00:00Z"
    end_time = time.strftime("%Y-%m-%dT%H:00:00Z", time.gmtime())
    last_day = calendar.monthrange(
        int(time.strftime("%Y", time.gmtime())), int(time.strftime("%m", time.gmtime()))
    )[1]
    first_day_selected_month = get_first_day_selected_month()
    (
        star_time_selected_date,
        end_time_selected_date,
    ) = get_start_end_time_first_day_selected_month()
    current_month_last_day = is_last_day_current_month()

    return {
        "start_time_for_current_month": start_time,
        "end_time_for_current_month": end_time,
        "last_day_current_month": last_day,
        "first_day_selected_month": first_day_selected_month,
        "start_time_selected_date": star_time_selected_date,
        "end_time_selected_date": end_time_selected_date,
        "current_month_last_day": current_month_last_day,
        "date_today": get_date_for_today(),
        "date_for_s3_key": get_report_time_for_s3_key(),
    }


def get_report_time_for_s3_key():
    time_for_s3_key = time.strftime("%Y/%m/%d/", time.gmtime())
    logger.debug(f"Returning time for s3 key as {time_for_s3_key}")
    return time_for_s3_key
