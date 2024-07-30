#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
from collections import namedtuple
from typing import Union

# AWS Libraries
from aws_lambda_powertools import Logger
from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import ClientError

logger = Logger(service="account_registry")

AccountInfo = namedtuple("AccountInfo", ["account_id", "role_name"])


class AccountRegistry:
    def get_accounts(self) -> list[AccountInfo]:
        raise NotImplementedError()


class DynamoDbAccountRegistry(AccountRegistry):
    def __init__(self, table: any) -> None:
        super().__init__()
        self._table = table

    def get_accounts(self) -> list[AccountInfo]:
        items: list[dict[str, str]] = []
        scan_kwargs = {"ProjectionExpression": "account_id, role_name"}
        try:
            done: bool = False
            start_key: Union[dict[str, any], None] = None
            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key
                response = self._table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))
                start_key = response.get("LastEvaluatedKey", None)
                done = start_key is None
        except ClientError as exception:
            logger.error(
                "Error scanning for accounts: %s: %s",
                exception.response.get("Error").get("Code"),
                exception.response.get("Error").get("Message"),
            )
            raise

        return [AccountInfo(**item) for item in items]


class NullAccountRegistry(AccountRegistry):
    def get_accounts(self) -> list[AccountInfo]:
        return []


def get_account_registry(session: Session) -> AccountRegistry:
    boto_config = Config(
        user_agent_extra=os.environ.get("UserAgentString"), retries={"mode": "standard"}
    )
    table_name: str = os.getenv("SpokeAccountDynamoDBTable")
    if table_name:
        dynamodb = session.resource("dynamodb", config=boto_config)
        table = dynamodb.Table(table_name)
        return DynamoDbAccountRegistry(table)
    # Single account deployment
    return NullAccountRegistry()
