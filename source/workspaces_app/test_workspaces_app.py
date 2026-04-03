#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
import unittest
from time import struct_time

# Third Party Libraries
import main
import pytest

# AWS Libraries
import boto3
from botocore import stub


@pytest.fixture(scope="module", autouse=True)
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["SOLUTION_ID"] = "SOTestID"
    os.environ["AWS_ACCOUNT"] = "123456789012"


def test_process_input_regions_1():
    valid_workspaces_regions = ["us-east-1"]
    result = main.process_input_regions([], valid_workspaces_regions)
    assert result == {"us-east-1"}


def test_process_input_regions_2():
    valid_workspaces_regions = ["us-east-1", "us-west-2"]
    result = main.process_input_regions(
        "us-west-2, us-east-1, us-east-2", valid_workspaces_regions
    )
    assert result == {"us-east-1", "us-west-2"}


def test_process_input_regions_3():
    valid_workspaces_regions = ["us-east-1", "us-west-2"]
    result = main.process_input_regions(
        '"us-west-2", "us-east-1", us-east-2', valid_workspaces_regions
    )
    assert result == {"us-east-1", "us-west-2"}


def test_process_input_regions_4():
    valid_workspaces_regions = ["us-east-1", "us-west-2"]
    result = main.process_input_regions(
        '"us-west-2", "us-east-1", us-east-2', valid_workspaces_regions
    )
    assert result == {"us-east-1", "us-west-2"}


def test_process_input_regions_5():
    valid_workspaces_regions = ["us-east-1", "us-west-2"]
    result = main.process_input_regions(
        '"us-west-2", us-east-2, 1234,ajdfbkjfb', valid_workspaces_regions
    )
    assert result == {"us-west-2"}


@unittest.mock.patch("boto3.session.Session")
def test_get_partition(mock_session):
    sts_client = boto3.client("sts")
    stub_sts = stub.Stubber(sts_client)
    partition = "some-partition"
    stub_sts.add_response(
        "get_caller_identity",
        {
            "UserId": "string",
            "Account": "111111111111",
            "Arn": f"arn:{partition}:iam::111111111111:user/root",
        },
    )
    mock_session.return_value.client.return_value = sts_client
    stub_sts.activate()
    assert main.get_partition() == partition
    stub_sts.deactivate()


@unittest.mock.patch("boto3.session.Session")
def test_get_account(mock_session):
    sts_client = boto3.client("sts")
    stub_sts = stub.Stubber(sts_client)
    account = "111111111111"
    stub_sts.add_response(
        "get_caller_identity",
        {
            "UserId": "string",
            "Account": account,
            "Arn": "arn:some-partition:iam::111111111111:user/root",
        },
    )
    mock_session.return_value.client.return_value = sts_client
    stub_sts.activate()
    assert main.get_account() == account
    stub_sts.deactivate()


@unittest.mock.patch("boto3.session.Session")
def test_get_valid_workspaces_regions(mock_session):
    parition_to_valid_region = {
        "aws-us-gov": ["us-gov-west-1"],
        "aws-cn": ["cn-northwest-1"],
        "aws": [
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-south-1",
            "ap-southeast-1",
            "ap-southeast-2",
            "ca-central-1",
            "eu-central-1",
            "eu-west-1",
            "eu-west-2",
            "sa-east-1",
            "us-east-1",
            "us-west-2",
            "af-south-1",
        ],
        "aws-iso": ["us-iso-east-1", "us-iso-west-1"],
        "aws-iso-b": ["us-isob-east-1"],
    }

    for partition, valid_region in parition_to_valid_region.items():
        mock_session.return_value = valid_region
        assert main.get_valid_workspaces_regions(partition) == valid_region


@unittest.mock.patch.dict(
    os.environ,
    {
        "LogLevel": "1",
        "DryRun": "1",
        "TestEndOfMonth": "1",
        "SendAnonymousData": "1",
        "SolutionVersion": "1",
        "SolutionID": "1",
        "UUID": "1",
        "BucketName": "1",
        "ValueLimit": "1",
        "StandardLimit": "1",
        "PerformanceLimit": "1",
        "PowerLimit": "1",
        "PowerProLimit": "1",
        "GraphicsG4dnLimit": "1",
        "GraphicsProG4dnLimit": "1",
        "UsageTable": "1",
        "UserSessionTable": "1",
    },
)
def test_get_stack_parameters_keyerror_missing_env_TerminateUnusedWorkspaces():
    try:
        main.get_stack_parameters()
    except KeyError as e:
        assert str(e.args[0]) in "TerminateUnusedWorkspaces"


stack_parameters = {
    "LogLevel": "1",
    "DryRun": "1",
    "TestEndOfMonth": "1",
    "SendAnonymousData": "1",
    "SolutionVersion": "1",
    "SolutionID": "1",
    "UUID": "1",
    "BucketName": "1",
    "ValueLimit": "1",
    "StandardLimit": "1",
    "PerformanceLimit": "1",
    "PowerLimit": "1",
    "PowerProLimit": "1",
    "GraphicsG4dnLimit": "1",
    "GraphicsProG4dnLimit": "1",
    "TerminateUnusedWorkspaces": "1",
    "UsageTable": "1",
    "UserSessionTable": "1",
}


@unittest.mock.patch.dict(os.environ, stack_parameters)
@unittest.mock.patch(
    "time.gmtime",
    unittest.mock.MagicMock(return_value=struct_time((2023, 1, 1, 1, 1, 1, 6, 1, 0))),
)
def test_get_stack_parameters():
    assert main.get_stack_parameters() == stack_parameters


@unittest.mock.patch(
    "time.gmtime",
    unittest.mock.MagicMock(return_value=struct_time((2023, 1, 31, 1, 1, 1, 2, 31, 0))),
)
def test_set_end_of_month_TestEndOfMonth_set():
    stack_parameters = {"TestEndOfMonth": "No"}
    main.set_end_of_month(stack_parameters)
    assert stack_parameters["TestEndOfMonth"] == "Yes"


@unittest.mock.patch(
    "time.gmtime",
    unittest.mock.MagicMock(return_value=struct_time((2023, 1, 1, 1, 1, 1, 6, 1, 0))),
)
def test_set_end_of_month_TestEndOfMonth_untouched():
    stack_parameters = {"TestEndOfMonth": "No"}
    main.set_end_of_month(stack_parameters)
    assert stack_parameters["TestEndOfMonth"] == "No"
