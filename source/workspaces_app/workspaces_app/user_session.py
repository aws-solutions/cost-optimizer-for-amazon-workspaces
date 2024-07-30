#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import logging
import os
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from decimal import Decimal
from typing import Optional

# AWS Libraries
import botocore
from boto3.dynamodb.types import TypeSerializer

log = logging.getLogger(__name__)

botoConfig = botocore.config.Config(
    max_pool_connections=100,
    retries={"max_attempts": 20, "mode": "standard"},
    user_agent_extra=os.getenv("UserAgentString"),
)


@dataclass(frozen=True)
class UserSession:
    workspace_id: str
    session_time: str = field(init=False)
    directory_id: str
    region: str
    account: str
    username: str
    active_sessions: list[datetime]
    duration_hours: int = 0
    in_session_latency: Optional[Decimal] = None
    cpu_usage: Optional[Decimal] = None
    memory_usage: Optional[Decimal] = None
    root_volume_disk_usage: Optional[Decimal] = None
    user_volume_disk_usage: Optional[Decimal] = None
    udp_packet_loss_rate: Optional[Decimal] = None

    def __post_init__(self):
        TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        start = self.active_sessions[0].strftime(TIME_FORMAT)
        end = self.active_sessions[-1].strftime(TIME_FORMAT)
        object.__setattr__(self, "session_time", start + " - " + end)

    @classmethod
    def from_json(cls, json: dict[str, any]) -> "UserSession":
        class_keys = [field.name for field in fields(cls)]
        filtered_json_keys = {
            key: value for key, value in json.items() if key in class_keys
        }

        if all(key in class_keys for key in filtered_json_keys):
            return cls(**filtered_json_keys)
        else:
            raise KeyError(
                "JSON does not contain all keys needed to create a UserSession instance"
            )

    def to_ddb_obj(self) -> dict[str, any]:
        """
        This method creates DynamoDB serialized dictionary from a UserSession rd for
        use with DynamoDB write calls.
        :return: a dictionary serialized as a DynamoDB item
        """
        serializer = TypeSerializer()
        class_as_json = asdict(self)
        TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
        class_as_json["active_sessions"] = [
            time.strftime(TIME_FORMAT) if class_as_json["active_sessions"] else None
            for time in class_as_json["active_sessions"]
        ]
        ddb_obj = {
            self.class_field_to_ddb_attr(key): serializer.serialize(value)
            for key, value in class_as_json.items()
        }
        return ddb_obj

    @staticmethod
    def class_field_to_ddb_attr(field_name: str) -> str:
        """
        This method converts a class field name to its corresponding
        DynamoDB attribute name
        :param field_name: the name of the class field
        :return: a string corresponding to a DynamoDB attribute
        """
        field_name_words = field_name.split("_")
        field_name_words[:] = [
            word.upper() if word in ("cpu", "udp") else word.capitalize()
            for word in field_name_words
        ]

        return "".join(field_name_words)

    @staticmethod
    def ddb_attr_to_class_field(ddb_attr: str) -> str:
        """
        This method changes a DynamoDB attr name to its corresponding
        class field name
        :param attr: the name of DynamoDB attribute
        :return: a string corresponding to a WorkspaceRecord field
        """
        class_field = re.sub(r"[a-z](?=[A-Z])|[A-Z](?=[A-Z][a-z])", r"\g<0>_", ddb_attr)

        return class_field.lower()
