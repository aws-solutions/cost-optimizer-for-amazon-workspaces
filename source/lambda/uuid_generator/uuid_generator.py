#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
import uuid

# Third Party Libraries
import cfnresponse

# AWS Libraries
import boto3
import botocore
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="cfn_stack_uuid_generator")
log_level = str(os.getenv("LOG_LEVEL", "INFO"))
logger.setLevel(log_level)

boto_config = botocore.config.Config(user_agent_extra=os.getenv("USER_AGENT_STRING"))
cfn_client = boto3.client("cloudformation", config=boto_config)


def lambda_handler(event, context):
    # Returns UUID for metrics.
    # Generates new UUID for new deployment and retrieves existing UUID for an update event.

    try:
        logger.info(event)
        logger.info(context)
        request = event.get("RequestType")
        response_data = {"UUID": ""}
        if request == "Create":
            uuid_value = generate_new_uuid()
            response_data = {"UUID": uuid_value}
        elif request == "Update":
            uuid_value = get_uuid_for_update_event(event)
            response_data = {"UUID": uuid_value}
        logger.info(response_data)
        cfnresponse.send(event, context, "SUCCESS", response_data)
    except Exception as e:
        logger.error(f"Exception: {e}")
        cfnresponse.send(event, context, "FAILED", {}, context.log_stream_name)


def get_uuid_for_update_event(event):
    existing_uuid = get_existing_uuid_from_current_stack(event)
    if existing_uuid == "":
        uuid_value = generate_new_uuid()
    else:
        uuid_value = existing_uuid
    return uuid_value


def get_existing_uuid_from_current_stack(event):
    response = describe_existing_stack(event)
    existing_uuid = ""
    if response.get("Stacks"):
        output_list = response.get("Stacks")[0].get("Outputs")
        logger.info(output_list)
        for item in output_list:
            if item.get("OutputKey") == "UUID":
                existing_uuid = item.get("OutputValue")
    return existing_uuid


def describe_existing_stack(event):
    response = {}
    try:
        response = cfn_client.describe_stacks(StackName=event.get("StackId"))
    except Exception as e:
        logger.exception(
            f"Error occurred when calling the describe stack operation {e}"
        )

    logger.info(f"Response for describe stack is {response}")
    return response


def generate_new_uuid():
    return str(uuid.uuid4())
