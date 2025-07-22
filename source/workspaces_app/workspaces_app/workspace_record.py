#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import logging
import os
import re
from dataclasses import asdict, dataclass, field, fields
from decimal import Decimal

# AWS Libraries
import botocore
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

log = logging.getLogger(__name__)

botoConfig = botocore.config.Config(
    max_pool_connections=100,
    retries={"max_attempts": 20, "mode": "standard"},
    user_agent_extra=os.getenv("UserAgentString"),
)


@dataclass(frozen=True)
class WeightedAverage:
    avg: Decimal
    count: int

    def weighted_avg(self):
        return self.avg * self.count

    def merge(self, other_wa: "WeightedAverage") -> "WeightedAverage":
        merged_count = self.count + other_wa.count
        merged_avg = Decimal(
            str((self.weighted_avg() + other_wa.weighted_avg()) / merged_count)
        )
        return WeightedAverage(avg=merged_avg, count=merged_count)


@dataclass(frozen=True)
class WorkspacePerformanceMetrics:
    in_session_latency: WeightedAverage | None
    cpu_usage: WeightedAverage | None
    memory_usage: WeightedAverage | None
    root_volume_disk_usage: WeightedAverage | None
    user_volume_disk_usage: WeightedAverage | None
    udp_packet_loss_rate: WeightedAverage | None

    def to_json(self) -> dict[str, any]:
        class_as_dict = asdict(self)
        class_as_json = {}
        for key, value in class_as_dict.items():
            if value is not None:
                class_as_json |= {
                    key: value.get("avg"),
                    key + "_count": value.get("count"),
                }
            else:  # there is no data for the performance metric
                class_as_json |= {key: None, key + "_count": 0}
        return class_as_json

    @classmethod
    def from_json(cls, json: dict[str, any]) -> "WorkspacePerformanceMetrics":
        class_keys = [field.name for field in fields(cls)]
        filtered_json_keys = {
            key: value for key, value in json.items() if key in class_keys
        }
        performance_metrics = {}
        for key in filtered_json_keys:
            count_key = key + "_count"

            if all(key in json for key in [key, count_key]):
                if json[key] is not None:
                    performance_metrics |= {
                        key: WeightedAverage(avg=json[key], count=json[count_key])
                    }
                else:
                    performance_metrics |= {key: None}
            else:
                raise KeyError(
                    "JSON does not contain all keys needed to create a WorkspacePerformanceMetrics instance"
                )

        return cls(**performance_metrics)

    @classmethod
    def is_performance_metric(cls, class_field: str) -> bool:
        return class_field in [
            "in_session_latency",
            "cpu_usage",
            "memory_usage",
            "root_volume_disk_usage",
            "user_volume_disk_usage",
            "udp_packet_loss_rate",
        ]


@dataclass(frozen=True)
class WorkspaceDescription:
    region: str
    account: str
    workspace_id: str
    directory_id: str
    usage_threshold: int | None
    bundle_type: str
    username: str
    computer_name: str
    initial_mode: str

    def to_json(self) -> dict[str, any]:
        return asdict(self)

    @classmethod
    def from_json(cls, json: dict[str, any]) -> "WorkspaceDescription":
        class_keys = [field.name for field in fields(cls)]
        filtered_json_keys = {
            key: value for key, value in json.items() if key in class_keys
        }

        if all(key in class_keys for key in filtered_json_keys):
            return cls(**filtered_json_keys)
        else:
            raise KeyError(
                "JSON does not contain all keys needed to create a WorkspaceDescription instance"
            )


@dataclass(frozen=True)
class WorkspaceBillingData:
    billable_hours: int = 0
    change_reported: str = ""
    new_mode: str = ""
    workspace_terminated: str = ""

    def to_json(self) -> dict[str, any]:
        return asdict(self)

    @classmethod
    def from_json(cls, json: dict[str, any]) -> "WorkspaceBillingData":
        class_keys = [field.name for field in fields(cls)]
        filtered_json_keys = {
            key: value for key, value in json.items() if key in class_keys
        }

        if all(key in class_keys for key in filtered_json_keys):
            return cls(**filtered_json_keys)
        else:
            raise KeyError(
                "JSON does not contain all keys needed to create a WorkspaceBillingData instance"
            )


@dataclass
class WorkspaceRecord:
    description: WorkspaceDescription
    billing_data: WorkspaceBillingData
    performance_metrics: WorkspacePerformanceMetrics
    report_date: str = ""
    last_reported_metric_period: str = ""
    last_known_user_connection: str = ""
    tags: str = ""
    workspace_type: str = ""

    def to_json(self) -> dict[str, any]:
        return {
            **self.description.to_json(),
            **self.billing_data.to_json(),
            **self.performance_metrics.to_json(),
            "report_date": self.report_date,
            "last_reported_metric_period": self.last_reported_metric_period,
            "last_known_user_connection": self.last_known_user_connection,
            "tags": self.tags,
            "workspace_type": self.workspace_type,
        }

    def to_ddb_obj(self) -> dict[str, any]:
        """
        This method creates DynamoDB serialized dictionary from a WorkspaceRecord for
        use with DynamoDB write calls.
        :return: a dictionary serialized as a DynamoDB item
        """
        class_as_json = self.to_json()
        ddb_obj = {}

        for key, value in class_as_json.items():
            ddb_obj |= self.serialize(key, value)

        return ddb_obj

    def to_csv(self) -> str:
        """
        This method returns the workspace record as a string for use with a csv
        :return: a string representation of the workspace
        """

        raw_csv = ",".join(
            (
                self.description.workspace_id,
                str(self.billing_data.billable_hours),
                str(self.description.usage_threshold),
                self.billing_data.change_reported,
                self.description.bundle_type,
                self.description.initial_mode,
                self.billing_data.new_mode,
                self.description.username,
                self.description.computer_name,
                self.description.directory_id,
                self.billing_data.workspace_terminated,
                str(getattr(self.performance_metrics.in_session_latency, "avg", "")),
                str(getattr(self.performance_metrics.cpu_usage, "avg", "")),
                str(getattr(self.performance_metrics.memory_usage, "avg", "")),
                str(
                    getattr(self.performance_metrics.root_volume_disk_usage, "avg", "")
                ),
                str(
                    getattr(self.performance_metrics.user_volume_disk_usage, "avg", "")
                ),
                str(getattr(self.performance_metrics.udp_packet_loss_rate, "avg", "")),
                self.tags,
                self.workspace_type,
                self.report_date
                + "\n",  # Adding quotes to the string to help with csv format
            )
        )
        csv = (
            raw_csv.replace(",-M-", ",ToMonthly")
            .replace(",-H-", ",ToHourly")
            .replace(",-E-", ",Failed to change the mode")
            .replace(",-N-", ",No Change")
            .replace(",-S-", ",Skipped")
        )
        return csv

    @classmethod
    def from_ddb_obj(
        cls, ddb_item: dict[str, any], ws_description
    ) -> "WorkspaceRecord":
        """
        This method creates workspace record from a DynamoDB item
        :param ddb_item: a serialized DynamoDB item
        :return: a WorkspaceRecord
        """
        ddb_as_json = {}

        for key, value in ddb_item.items():
            ddb_as_json |= cls.deserialize(key, value)

        return cls(
            description=ws_description,
            billing_data=WorkspaceBillingData.from_json(ddb_as_json),
            report_date=ddb_as_json["report_date"],
            last_reported_metric_period=ddb_as_json["last_reported_metric_period"],
            last_known_user_connection=ddb_as_json["last_known_user_connection"],
            performance_metrics=WorkspacePerformanceMetrics.from_json(ddb_as_json),
            tags=ddb_as_json["tags"],
            workspace_type=ddb_as_json["workspace_type"],
        )

    @staticmethod
    def serialize(field_name: str, field_value: any) -> dict[str, any]:
        """
        This method serializes a class field for use with DynamoDB
        :param field_name: the name of the class field
        :param field_value: the current value of the class field
        :return: a dict of a  serialized DynamoDB item
        """
        serializer = TypeSerializer()
        ddb_attr = WorkspaceRecord.class_field_to_ddb_attr(field_name)

        return {ddb_attr: serializer.serialize(field_value)}

    @staticmethod
    def deserialize(attr_name: str, attr_value: dict[str, any]) -> dict[str, any]:
        """
        This method deserializes a DynamoDB attribute to a class field
        :param attr_name: the name of DynamoDB attribute
        :param attr_value: the serialized value of the DynamoDB attr
        :return: a dict of representing a class field
        """
        deserializer = TypeDeserializer()
        class_attr = WorkspaceRecord.ddb_attr_to_class_field(attr_name)

        return {class_attr: deserializer.deserialize(attr_value)}

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

    @staticmethod
    def csv_header() -> str:
        """
        This method returns the csv headers for the workspace record csv report
        class field name
        :return: a string for the csv headers
        """
        return (
            "WorkspaceID,Billable Hours,Usage Threshold,Change Reported,Bundle Type,Initial Mode,"
            "New Mode,Username,Computer Name,DirectoryId,WorkspaceTerminated,insessionlatency,"
            "cpuusage,memoryusage,rootvolumediskusage,uservolumediskusage,udppacketlossrate,Tags,WorkspaceType,ReportDate,\n"
        )
