#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import time
import unittest

# Third Party Libraries
import jmespath
import pytest

# AWS Libraries
import botocore

# Cost Optimizer for Amazon Workspaces
from .. import s3_utils


# Class used to mock a boto3 page iterator. Boto3 uses jmespath
# for their search function, this class imitates the functionality.
class MockPaginator:
    def __init__(self, result):
        self.result = result

    def search(self, expression):
        compiled = jmespath.compile(expression)
        results = compiled.search(self.result)
        yield from results

    def __iter__(self):
        yield (self.result)


@unittest.mock.patch(s3_utils.__name__ + ".s3_put_report")
@unittest.mock.patch(s3_utils.__name__ + ".create_s3_key")
@unittest.mock.patch("boto3.session.Session")
def test_upload_report(mock_session, mock_create_s3_key, mock_s3_put_report):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    s3_key = "a_key"
    mock_create_s3_key.return_value = s3_key
    session = mock_session()
    stack_parameters = {"BucketName": "a_bucket"}
    report_body = "a_report"
    directory_id = "a_directory"
    directory_region = "a_region"
    account = "111111111111"
    s3_utils.upload_report(
        session,
        date_time_values,
        stack_parameters,
        report_body,
        directory_id,
        directory_region,
        account,
    )
    mock_create_s3_key.assert_called_once_with(
        stack_parameters, directory_id, directory_region, account, date_time_values
    )
    mock_s3_put_report.assert_called_once_with(
        session, stack_parameters["BucketName"], report_body, s3_key
    )


@unittest.mock.patch(s3_utils.__name__ + ".s3_put_report")
@unittest.mock.patch(s3_utils.__name__ + ".create_s3_key")
@unittest.mock.patch("boto3.session.Session")
def test_upload_report_no_directory(
    mock_session, mock_create_s3_key, mock_s3_put_report
):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    s3_key = "a_key"
    mock_create_s3_key.return_value = s3_key
    session = mock_session()
    stack_parameters = {"BucketName": "a_bucket"}
    report_body = "a_report"
    s3_utils.upload_report(session, date_time_values, stack_parameters, report_body)
    mock_create_s3_key.assert_called_once_with(
        stack_parameters, None, None, None, date_time_values
    )
    mock_s3_put_report.assert_called_once_with(
        session, stack_parameters["BucketName"], report_body, s3_key
    )


def get_format_string() -> str:
    return "%Y-%m-%dT%H:%M:%SZ"


@pytest.fixture()
def mock_end_time():
    end_time = time.gmtime()
    s3_utils.end_time = time.strftime(get_format_string(), end_time)
    yield end_time


def get_path_format_string() -> str:
    return "%Y/%m/%d/"


def test_create_s3_key(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "No", "TestEndOfMonth": "No"}
    directory_id = "a_directory"
    directory_region = "a-region"
    account = "111111111111"
    expected_key = (
        "2023/03/15/"
        + directory_region
        + "_"
        + account
        + "_"
        + directory_id
        + "_daily.csv"
    )
    actual_key = s3_utils.create_s3_key(
        stack_parameters, directory_id, directory_region, account, date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_no_directory_id(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "No", "TestEndOfMonth": "No"}
    expected_key = "2023/03/15/" + "aggregated_daily.csv"
    actual_key = s3_utils.create_s3_key(
        stack_parameters, None, None, "", date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_no_directory_id_dry_run(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "Yes", "TestEndOfMonth": "No"}
    expected_key = "2023/03/15/" + "aggregated_dry-run_daily.csv"
    actual_key = s3_utils.create_s3_key(
        stack_parameters, None, None, "", date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_no_directory_id_end_of_month(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "No", "TestEndOfMonth": "Yes"}
    expected_key = "2023/03/15/" + "aggregated_end-of-month.csv"
    actual_key = s3_utils.create_s3_key(
        stack_parameters, None, None, "", date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_no_directory_id_dry_run_end_of_month(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "Yes", "TestEndOfMonth": "Yes"}
    expected_key = "2023/03/15/" + "aggregated_dry-run_end-of-month.csv"
    actual_key = s3_utils.create_s3_key(
        stack_parameters, None, None, "", date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_dry_run(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "Yes", "TestEndOfMonth": "No"}
    directory_id = "a_directory"
    directory_region = "a-region"
    account = "111111111111"
    expected_key = (
        "2023/03/15/"
        + directory_region
        + "_"
        + account
        + "_"
        + directory_id
        + "_dry-run_daily.csv"
    )
    actual_key = s3_utils.create_s3_key(
        stack_parameters, directory_id, directory_region, account, date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_end_of_month(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "No", "TestEndOfMonth": "Yes"}
    directory_id = "a_directory"
    directory_region = "a-region"
    account = "111111111111"
    expected_key = (
        "2023/03/15/"
        + directory_region
        + "_"
        + account
        + "_"
        + directory_id
        + "_end-of-month.csv"
    )
    actual_key = s3_utils.create_s3_key(
        stack_parameters, directory_id, directory_region, account, date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_dry_run_end_of_month(mock_end_time):
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "Yes", "TestEndOfMonth": "Yes"}
    directory_id = "a_directory"
    directory_region = "a-region"
    account = "111111111111"
    expected_key = (
        "2023/03/15/"
        + directory_region
        + "_"
        + account
        + "_"
        + directory_id
        + "_dry-run_end-of-month.csv"
    )
    actual_key = s3_utils.create_s3_key(
        stack_parameters, directory_id, directory_region, account, date_time_values
    )
    assert actual_key == expected_key


def test_create_s3_key_uses_latest_report_date_if_provided():
    date_time_values = {"date_for_s3_key": "2023/03/15/"}
    stack_parameters = {"DryRun": "Yes", "TestEndOfMonth": "Yes"}
    directory_id = None
    directory_region = None
    account = None
    latest_s3_report = "2023/03/14/"
    expected_key = "2023/03/14/" + "aggregated_dry-run_end-of-month.csv"
    actual_key = s3_utils.create_s3_key(
        stack_parameters,
        directory_id,
        directory_region,
        account,
        date_time_values,
        latest_s3_report,
    )
    assert actual_key == expected_key


@unittest.mock.patch("boto3.session.Session")
def test_put_report(mock_session):
    session = mock_session()
    bucket_name = "a_bucket_name"
    report_body = "a_report"
    s3_key = "a_key"
    s3_utils.s3_put_report(session, bucket_name, report_body, s3_key)
    session.client.return_value.put_object.assert_called_once_with(
        Bucket=bucket_name, Body=report_body, Key=s3_key
    )


@unittest.mock.patch("boto3.session.Session")
def test_put_report_error(mock_session):
    session = mock_session()
    bucket_name = "a_bucket_name"
    report_body = "a_report"
    s3_key = "a_key"
    session.client.return_value.put_object.side_effect = (
        botocore.exceptions.ClientError({}, "an_error")
    )
    s3_utils.s3_put_report(session, bucket_name, report_body, s3_key)
    session.client.return_value.put_object.assert_called_once_with(
        Bucket=bucket_name, Body=report_body, Key=s3_key
    )
