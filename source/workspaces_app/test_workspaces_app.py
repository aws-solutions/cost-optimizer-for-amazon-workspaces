#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import main
import botocore
import boto3
import pytest
import unittest
import os


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
    valid_workspaces_regions = ['us-east-1']
    result = main.process_input_regions([], valid_workspaces_regions)
    assert result == {'us-east-1'}


def test_process_input_regions_2():
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = main.process_input_regions('us-west-2, us-east-1, us-east-2', valid_workspaces_regions)
    assert result == {'us-east-1', 'us-west-2'}


def test_process_input_regions_3():
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = main.process_input_regions('"us-west-2", "us-east-1", us-east-2', valid_workspaces_regions)
    assert result == {'us-east-1', 'us-west-2'}


def test_process_input_regions_4():
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = main.process_input_regions('"us-west-2", "us-east-1", us-east-2', valid_workspaces_regions)
    assert result == {'us-east-1', 'us-west-2'}


def test_process_input_regions_5():
    valid_workspaces_regions = ['us-east-1', 'us-west-2']
    result = main.process_input_regions('"us-west-2", us-east-2, 1234,ajdfbkjfb', valid_workspaces_regions)
    assert result == {'us-west-2'}


@unittest.mock.patch('boto3.session.Session')
def test_get_partition(mock_session):
    sts_client = boto3.client('sts')
    stub_sts = botocore.stub.Stubber(sts_client)
    partition = 'some-partition'
    stub_sts.add_response('get_caller_identity', {
        'UserId': 'string',
        'Account': '111111111111',
        'Arn': f'arn:{partition}:iam::111111111111:user/root'
    })
    mock_session.return_value.client.return_value = sts_client
    stub_sts.activate()
    assert main.get_partition() == partition
    stub_sts.deactivate()
