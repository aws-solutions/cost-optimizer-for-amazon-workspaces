#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
import time
from itertools import batched

# AWS Libraries
import boto3
import botocore
from aws_lambda_powertools import Logger

# Cost Optimizer for Amazon Workspaces
from ..user_session import UserSession

# Initialize logger
logger = Logger(service="workspace_usage_table_dao")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)

boto_config = botocore.config.Config(
    retries={"max_attempts": 20, "mode": "standard"},
    user_agent_extra=os.getenv("UserAgentString"),
)


class UserSessionDAO:
    def __init__(self, session: boto3.session.Session, table_name: str, region: str):
        self.region = region
        self.table_name = table_name
        self.client = session.client("dynamodb", config=boto_config)

    def update_ddb_items(
        self,
        user_sessions: list[UserSession],
    ):
        """
        :param session: A boto3 session
        :param table_name: The name of the workspace usage table
        :param report_body: Report body containing the workspace analysis data
        :param directory_region: The region in which the directory exists
        :param account: The aws account for the workspace
        This method writes the workspace analysis data to DynamoDB
        """
        try:
            list_ddb_items = [
                UserSession.to_ddb_obj(session) for session in user_sessions
            ]
            for batch in batched(list_ddb_items, 25):
                response = self.client.batch_write_item(
                    RequestItems={
                        self.table_name: [
                            {"PutRequest": {"Item": item}} for item in batch
                        ]
                    }
                )
                retries = 0
                max_retries = 5
                while response.get("UnprocessedItems") and retries < max_retries:
                    retries += 1
                    time.sleep(2**retries + 10)
                    response = self.client.batch_write_item(
                        RequestItems=response.get("UnprocessedItems")
                    )
                if retries >= max_retries:
                    logger.exception(
                        "Unable to write the following user sessions to the table: {}, retries left: {}".format(
                            response.get("UnprocessedItems"), max_retries - retries
                        )
                    )
        except Exception as e:
            logger.exception(
                "Exception occurred while updating the user session table. Error: {}".format(
                    e
                )
            )
