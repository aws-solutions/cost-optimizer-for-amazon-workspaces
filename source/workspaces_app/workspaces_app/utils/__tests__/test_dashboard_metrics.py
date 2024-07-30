# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party Libraries
import pytest

# Cost Optimizer for Amazon Workspaces
from workspaces_app.utils.dashboard_metrics import DashboardMetrics


@pytest.fixture
def dashboard_metrics():
    return DashboardMetrics()


def test_update_total_workspaces(dashboard_metrics):
    dashboard_metrics.update_total_workspaces(5)
    assert dashboard_metrics.total_workspaces == 5

    dashboard_metrics.update_total_workspaces(3)
    assert dashboard_metrics.total_workspaces == 8


def test_update_billing_metrics(dashboard_metrics):
    dashboard_metrics.update_billing_metrics("hourly_billed")
    assert dashboard_metrics.billing_metrics.hourly_billed == 1
    assert dashboard_metrics.billing_metrics.monthly_billed == 0

    dashboard_metrics.update_billing_metrics("monthly_billed")
    assert dashboard_metrics.billing_metrics.hourly_billed == 1
    assert dashboard_metrics.billing_metrics.monthly_billed == 1

    dashboard_metrics.update_billing_metrics("hourly_billed")
    assert dashboard_metrics.billing_metrics.hourly_billed == 2
    assert dashboard_metrics.billing_metrics.monthly_billed == 1


def test_update_conversion_metrics(dashboard_metrics):
    dashboard_metrics.update_conversion_metrics("hourly_to_monthly")
    assert dashboard_metrics.conversion_metrics.hourly_to_monthly == 1
    assert dashboard_metrics.conversion_metrics.monthly_to_hourly == 0
    assert dashboard_metrics.conversion_metrics.conversion_errors == 0
    assert dashboard_metrics.conversion_metrics.conversion_skips == 0

    dashboard_metrics.update_conversion_metrics("monthly_to_hourly")
    dashboard_metrics.update_conversion_metrics("conversion_errors")
    dashboard_metrics.update_conversion_metrics("conversion_skips")

    assert dashboard_metrics.conversion_metrics.hourly_to_monthly == 1
    assert dashboard_metrics.conversion_metrics.monthly_to_hourly == 1
    assert dashboard_metrics.conversion_metrics.conversion_errors == 1
    assert dashboard_metrics.conversion_metrics.conversion_skips == 1


def test_update_termination_metrics(dashboard_metrics):
    dashboard_metrics.update_termination_metrics()
    assert dashboard_metrics.termination_metrics == 1

    dashboard_metrics.update_termination_metrics()
    assert dashboard_metrics.termination_metrics == 2


@patch("workspaces_app.utils.dashboard_metrics.single_metric")
@patch("workspaces_app.utils.dashboard_metrics.metrics")
def test_publish_metrics(mock_metrics, mock_single_metric, dashboard_metrics):
    mock_context_manager = MagicMock()
    mock_single_metric.return_value.__enter__.return_value = mock_context_manager

    dashboard_metrics.update_total_workspaces(10)
    dashboard_metrics.update_billing_metrics("hourly_billed")
    dashboard_metrics.update_billing_metrics("monthly_billed")
    dashboard_metrics.update_conversion_metrics("hourly_to_monthly")
    dashboard_metrics.update_conversion_metrics("monthly_to_hourly")
    dashboard_metrics.update_conversion_metrics("conversion_errors")
    dashboard_metrics.update_conversion_metrics("conversion_skips")
    dashboard_metrics.update_termination_metrics()

    dashboard_metrics.publish_metrics(60.0, "False", "Yes")

    assert mock_single_metric.call_count == 3
    assert mock_metrics.add_metric.call_count == 6
    assert mock_metrics.flush_metrics.call_count == 1

    mock_context_manager.add_dimension.assert_called_with(
        name="TerminationStatus", value="Terminated"
    )


def test_error_handling(dashboard_metrics, caplog):
    with patch.object(dashboard_metrics, "total_workspaces", None):
        dashboard_metrics.update_total_workspaces(1)
        assert "Error updating total workspaces" in caplog.text

    caplog.clear()

    dashboard_metrics.update_billing_metrics("invalid_metric")
    assert "Invalid billing metric name: invalid_metric" in caplog.text

    caplog.clear()

    dashboard_metrics.update_conversion_metrics("invalid_metric")
    assert "Invalid conversion metric name: invalid_metric" in caplog.text

    caplog.clear()

    with patch.object(dashboard_metrics, "termination_metrics", None):
        dashboard_metrics.update_termination_metrics()
        assert "Error updating termination metrics" in caplog.text

    caplog.clear()

    with patch(
        "workspaces_app.utils.dashboard_metrics.metrics.add_metric",
        side_effect=Exception("Test exception"),
    ):
        dashboard_metrics.publish_metrics(60.0, "False", "Yes")
        assert "Failed to publish metrics" in caplog.text


def test_dry_run_termination(dashboard_metrics):
    dashboard_metrics.update_termination_metrics()
    dashboard_metrics.publish_metrics(60.0, "True", "Dry Run")
    assert dashboard_metrics.termination_metrics == 1


def test_no_termination(dashboard_metrics):
    dashboard_metrics.publish_metrics(60.0, "False", "No")
    assert dashboard_metrics.termination_metrics == 0
