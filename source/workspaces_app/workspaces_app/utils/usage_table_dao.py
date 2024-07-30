#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os

# AWS Libraries
import boto3
import botocore
from aws_lambda_powertools import Logger

# Cost Optimizer for Amazon Workspaces
from ..workspace_record import WorkspaceDescription, WorkspaceRecord

# Initialize logger
logger = Logger(service="workspace_usage_table_dao")
log_level = os.getenv("LogLevel", "INFO")
logger.setLevel(log_level)

boto_config = botocore.config.Config(
    retries={"max_attempts": 20, "mode": "standard"},
    user_agent_extra=os.getenv("UserAgentString"),
)


class UsageTableDAO:
    def __init__(self, session: boto3.session.Session, table_name: str, region: str):
        self.region = region
        self.table_name = table_name
        self.client = session.client("dynamodb", config=boto_config)

    def update_ddb_item(
        self,
        ws_record: WorkspaceRecord,
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
            record_as_ddb_item = ws_record.to_ddb_obj()
            self.client.put_item(TableName=self.table_name, Item=record_as_ddb_item)
        except Exception as e:
            logger.exception(
                "Exception occurred while updating the usage table. Error: {}".format(e)
            )
            raise e

    def get_workspace_ddb_item(
        self, ws_description: WorkspaceDescription
    ) -> WorkspaceRecord | WorkspaceDescription:
        """
        This method retrieves the DDB item corresponding to a workspace
        :param session: A boto3 session
        :param table_name: The name of the workspace usage table
        :param ws_description: The WorkspaceDescription object representing the workspace
        :param region: The region in which the workspace exists
        :returns: A DDB entry for the specified workspace if it exist,
        otherwise return the workspace description.
        """
        ws_record = ws_description
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key={
                    "WorkspaceId": {"S": ws_description.workspace_id},
                    "Region": {
                        "S": self.region,
                    },
                },
            )
            ddb_item = response.get("Item")
            if ddb_item:
                ws_record = WorkspaceRecord.from_ddb_obj(ddb_item, ws_description)
        except Exception as e:
            logger.exception(
                "Exception occurred while getting workspace {} from the usage table. Error {}".format(
                    ws_description.workspace_id, e
                )
            )
        return ws_record
