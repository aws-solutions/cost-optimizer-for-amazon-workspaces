# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
import os
from dataclasses import dataclass

# AWS Libraries
from aws_lambda_powertools import Logger, Metrics, single_metric
from aws_lambda_powertools.metrics import MetricUnit

METRIC_NAMESPACE = "WorkspacesCostOptimizer"
metrics = Metrics(namespace=METRIC_NAMESPACE)

logger = Logger(service="dashboard_metrics")
log_level = str(os.getenv("LogLevel", "INFO"))
logger.setLevel(log_level)


@dataclass
class BillingMetrics:
    hourly_billed: int = 0
    monthly_billed: int = 0


@dataclass
class ConversionMetrics:
    hourly_to_monthly: int = 0
    monthly_to_hourly: int = 0
    conversion_errors: int = 0
    conversion_skips: int = 0


class DashboardMetrics:
    def __init__(self):
        self.billing_metrics = BillingMetrics()
        self.conversion_metrics = ConversionMetrics()
        self.termination_metrics = 0
        self.total_workspaces = 0
        logger.info(f"Initialized DashboardMetrics")

    def update_total_workspaces(self, count: int):
        try:
            self.total_workspaces += count
        except Exception as e:
            logger.error(f"Error updating total workspaces: {str(e)}")

    def update_billing_metrics(self, metric_name: str):
        try:
            if metric_name == "hourly_billed":
                self.billing_metrics.hourly_billed += 1
            elif metric_name == "monthly_billed":
                self.billing_metrics.monthly_billed += 1
            else:
                logger.error(f"Invalid billing metric name: {metric_name}")
        except Exception as e:
            logger.error(f"Error updating billing metrics: {str(e)}")

    def update_conversion_metrics(self, metric_name: str):
        try:
            if metric_name == "hourly_to_monthly":
                self.conversion_metrics.hourly_to_monthly += 1
            elif metric_name == "monthly_to_hourly":
                self.conversion_metrics.monthly_to_hourly += 1
            elif metric_name == "conversion_errors":
                self.conversion_metrics.conversion_errors += 1
            elif metric_name == "conversion_skips":
                self.conversion_metrics.conversion_skips += 1
            else:
                logger.error(f"Invalid conversion metric name: {metric_name}")
        except Exception as e:
            logger.error(f"Error updating conversion metrics: {str(e)}")

    def update_termination_metrics(self):
        try:
            self.termination_metrics += 1
        except Exception as e:
            logger.error(f"Error updating termination metrics: {str(e)}")

    def publish_metrics(
        self, execution_time: float, is_dry_run: str, terminate_unused_workspaces: str
    ):
        try:
            metrics_to_publish = [
                ("TotalWorkspaces", self.total_workspaces),
                ("HourlyBilledWorkspaces", self.billing_metrics.hourly_billed),
                ("MonthlyBilledWorkspaces", self.billing_metrics.monthly_billed),
                ("ConversionErrors", self.conversion_metrics.conversion_errors),
                ("ConversionSkips", self.conversion_metrics.conversion_skips),
                (
                    "HourlyToMonthlyConversions",
                    self.conversion_metrics.hourly_to_monthly,
                ),
                (
                    "MonthlyToHourlyConversions",
                    self.conversion_metrics.monthly_to_hourly,
                ),
                ("EcsTaskExecutionTime", execution_time),
            ]

            for metric_name, metric_value in metrics_to_publish:
                logger.debug(f"Publishing metric: {metric_name} = {metric_value}")
                if metric_name in [
                    "HourlyToMonthlyConversions",
                    "MonthlyToHourlyConversions",
                ]:
                    with single_metric(
                        namespace=METRIC_NAMESPACE,
                        name=metric_name,
                        unit=MetricUnit.Count,
                        value=metric_value,
                    ) as metric:
                        metric.add_dimension(name="DryRun", value=str(is_dry_run))
                else:
                    metrics.add_metric(
                        name=metric_name, unit=MetricUnit.Count, value=metric_value
                    )

            if terminate_unused_workspaces == "Yes":
                termination_status = "Terminated"
            elif terminate_unused_workspaces == "Dry Run":
                termination_status = "DryRun"
            else:
                termination_status = None
                logger.debug(
                    "Not Publishing termination metrics because terminate action was not called"
                )

            if termination_status:
                with single_metric(
                    namespace=METRIC_NAMESPACE,
                    name="TerminatedWorkspaces",
                    unit=MetricUnit.Count,
                    value=self.termination_metrics,
                ) as metric:
                    metric.add_dimension(
                        name="TerminationStatus", value=termination_status
                    )
            logger.debug(
                f"Publishing metric: TerminatedWorkspaces = {self.termination_metrics}"
            )

            metrics.flush_metrics()
            logger.info("All metrics published successfully")
        except Exception as e:
            logger.exception(f"Failed to publish metrics: {str(e)}")
