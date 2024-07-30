#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
import typing

# AWS Libraries
import boto3
import botocore
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="wco_report_s3_utils")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)

boto_config = botocore.config.Config(
    retries={"max_attempts": 20, "mode": "standard"},
    user_agent_extra=os.getenv("UserAgentString"),
)


def upload_report(
    session: boto3.session.Session,
    date_time_values,
    stack_parameters: dict,
    report_body: str,
    directory_id: typing.Union[str, None] = None,
    directory_region: typing.Union[str, None] = None,
    account: str = None,
):
    """
    :param directory_region: Region for the directory
    :param directory_id: ID for the directory
    :param report_body: body of the report
    :param stack_parameters: parameters for the stack
    This method uploads the workspace report to the cost optimizer bucket.
    """
    logger.debug("Uploading the csv report to s3 bucket.")
    s3_key = create_s3_key(
        stack_parameters, directory_id, directory_region, account, date_time_values
    )
    bucket_name = stack_parameters["BucketName"]
    s3_put_report(session, bucket_name, report_body, s3_key)
    logger.debug("Successfully uploaded csv file to %s", s3_key)


def create_s3_key(
    stack_parameters: dict,
    directory_id: typing.Union[str, None],
    directory_region: typing.Union[str, None],
    account: str,
    date_time_values: dict,
    latest_s3_report="",
) -> str:
    """
    :param: stack_parameters: parameters for the stack
    :param: directory_id: ID for the directory
    :param: Region for the directory
    This method creates the s3 key for the report.
    """
    logger.debug("Creating s3 key for report")
    time_for_s3_key = latest_s3_report or date_time_values.get("date_for_s3_key")
    if directory_id:
        s3_key = time_for_s3_key + directory_region + "_" + account + "_" + directory_id
    else:
        s3_key = time_for_s3_key + "aggregated"
    if stack_parameters["DryRun"] == "Yes":
        s3_key += "_dry-run"
    if stack_parameters["TestEndOfMonth"] == "Yes":
        s3_key += "_end-of-month"
    else:
        s3_key += "_daily"
    s3_key += ".csv"
    logger.debug("Returning s3 key as {}".format(s3_key))

    return s3_key


def s3_put_report(
    session: boto3.session.Session, bucket_name: str, report_body: str, s3_key: str
) -> None:
    """
    :param: bucket_name: Name of the bucket to upload report
    :param: report_body: body of the report
    :param: s3_key: key for the s3 report
    This method puts report to s3 bucket
    """
    logger.debug(
        "Putting report to s3 bucket {} with key: {}".format(bucket_name, s3_key)
    )
    try:
        session.client("s3", config=boto_config).put_object(
            Bucket=bucket_name, Body=report_body, Key=s3_key
        )
        logger.debug(
            "Successfully uploaded the report to s3 bucket {} with key: {}".format(
                bucket_name, s3_key
            )
        )
    except botocore.exceptions.ClientError as e:
        logger.exception(
            "Exception occurred while uploading the report to s3 bucket. Error {}".format(
                e
            )
        )
