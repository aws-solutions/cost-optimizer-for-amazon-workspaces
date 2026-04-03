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

# Initialize logger
logger = Logger(service="spoke_account_dynamodb")
log_level = str(os.getenv("LOG_LEVEL", "INFO"))
logger.setLevel(log_level)

# Update boto config
boto_config = botocore.config.Config(user_agent_extra=os.getenv("USER_AGENT_STRING"))


class DynamoDBTable:
    """
    Class to represent the DynamoDB table and support the operations on the table
    """

    def __init__(self, table_name: str):
        self.dynamo_db_client = boto3.resource("dynamodb", config=boto_config)
        self.table = self.dynamo_db_client.Table(table_name)

    def put_item(self, account_id: str, role_name: str) -> None:
        """
        This method puts the record with account id and role name in the dynamo table

        Parameters:
            account_id (str): account id of the spoke account
            role_name (str): role name created in the spoke account
        Returns:
            None
        Raises:
            ClientError:
        """
        logger.debug(
            f"Calling put_item with {account_id[-4:]} and {role_name.split('/')[1]}"
        )
        try:
            self.table.put_item(Item={"account_id": account_id, "role_name": role_name})
        except botocore.exceptions.ClientError as e:
            logger.exception(
                f"Error when adding the account id {account_id[-4:]} to dynamodb: {e}"
            )
            raise e

    def delete_item(self, account_id: str, role_name: str) -> None:
        """
        This function deletes the record for the given account and role name in the dynamo table

        Parameters:
            account_id (str): account id of the spoke account
            role_name (str): role name created in the spoke account
        Returns:
            None
        Raises:
            ClientError:
        """
        logger.debug(
            f"Calling delete_item with {account_id[-4:]} and {role_name.split('/')[1]}"
        )
        try:
            self.table.delete_item(
                Key={"account_id": account_id, "role_name": role_name}
            )
        except botocore.exceptions.ClientError as e:
            logger.exception(
                f"Error when deleting the account id {account_id[-4:]} from dynamodb: {e}"
            )
            raise e
