// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { Fn, Aws, Duration, Tags } from "aws-cdk-lib";
import {
  Color,
  GraphWidget,
  GraphWidgetView,
  LegendPosition,
  Metric,
  Dashboard,
  PeriodOverride,
  Row,
  SingleValueWidget,
  TextWidget,
} from "aws-cdk-lib/aws-cloudwatch";
import { Construct } from "constructs";

export interface WorkspacesDashboardResourcesProps {
  solutionId: string;
  solutionVersion: string;
}

export class WorkspacesDashboardResources extends Construct {
  public readonly dashboard: Dashboard;

  constructor(scope: Construct, id: string, props: WorkspacesDashboardResourcesProps) {
    super(scope, id);

    const uniqueSuffix = Fn.select(2, Fn.split("/", Aws.STACK_ID));
    const dashboardName = Fn.join("-", [Aws.STACK_NAME, "Dashboard", uniqueSuffix]);

    this.dashboard = new Dashboard(this, "WorkspacesCostOptimizerDashboard", {
      dashboardName: dashboardName,
      defaultInterval: Duration.days(30),
      periodOverride: PeriodOverride.INHERIT,
    });

    const workspacesHeader = new TextWidget({
      markdown: "# WorkSpaces Overview",
      width: 24,
      height: 1,
    });

    const totalWorkspacesWidget = new SingleValueWidget({
      title: "Total number of WorkSpaces Monitored in the last 24 hours",
      metrics: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "TotalWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
          label: "Total Workspaces",
        }),
      ],
      width: 6,
      height: 6,
    });

    const billingDistributionPieWidget = new GraphWidget({
      title: "WorkSpaces Billing Mode Distribution in the last 24 hours",
      left: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "HourlyBilledWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
          label: "Hourly Billed",
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "MonthlyBilledWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
          label: "Monthly Billed",
        }),
      ],
      view: GraphWidgetView.PIE,
      width: 6,
      height: 6,
      setPeriodToTimeRange: false,
    });

    const billingDistributionWidget = new GraphWidget({
      title: "WorkSpaces Billing Mode Distribution Over Time",
      left: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "HourlyBilledWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
        }).with({
          label: "Hourly Billed",
          color: Color.ORANGE,
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "MonthlyBilledWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
        }).with({
          label: "Monthly Billed",
          color: Color.BLUE,
        }),
      ],
      leftYAxis: {
        label: "Number of WorkSpaces",
        showUnits: false,
        min: 0,
      },
      width: 12,
      height: 6,
      view: GraphWidgetView.TIME_SERIES,
      stacked: true,
      legendPosition: LegendPosition.BOTTOM,
    });

    const conversionsWidget = new SingleValueWidget({
      title: `Billing Mode Conversions`,
      metrics: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "MonthlyToHourlyConversions",
          statistic: "Sum",
          dimensionsMap: { DryRun: "No" },
        }).with({
          label: "Monthly to Hourly",
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "HourlyToMonthlyConversions",
          statistic: "Sum",
          dimensionsMap: { DryRun: "No" },
        }).with({
          label: "Hourly to Monthly",
        }),
      ],
      setPeriodToTimeRange: true,
      width: 6,
      height: 6,
    });

    const terminatedWorkspacesWidget = new SingleValueWidget({
      title: `Total Terminated Workspaces`,
      metrics: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "TerminatedWorkspaces",
          statistic: "Sum",
          dimensionsMap: { TerminationStatus: "Terminated" },
        }).with({
          label: "Terminated Workspaces",
        }),
      ],
      setPeriodToTimeRange: true,
      width: 6,
      height: 6,
    });

    const terminatedWorkspacesGraphWidget = new GraphWidget({
      title: "Total Terminated Workspaces Over Time",
      left: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "TerminatedWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
          dimensionsMap: { TerminationStatus: "Terminated" },
        }).with({
          label: "Actual Terminations",
          color: Color.GREEN,
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "TerminatedWorkspaces",
          statistic: "Maximum",
          period: Duration.days(1),
          dimensionsMap: { TerminationStatus: "DryRun" },
        }).with({
          label: "Dry Run Terminations",
          color: Color.PURPLE,
        }),
      ],
      leftYAxis: {
        label: "Number of Workspaces",
        showUnits: false,
        min: 0,
      },
      width: 12,
      height: 6,
      view: GraphWidgetView.TIME_SERIES,
      stacked: true,
      legendPosition: LegendPosition.BOTTOM,
    });

    const unconvertedWorkspacesWidget = new GraphWidget({
      title: "Unconverted Workspaces",
      left: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "ConversionErrors",
          statistic: "Maximum",
          period: Duration.days(1),
        }).with({
          label: "Conversion Failures",
          color: Color.RED,
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "ConversionSkips",
          statistic: "Maximum",
          period: Duration.days(1),
        }).with({
          label: "Skip_Convert tagged Workspaces",
          color: Color.GREY,
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "MonthlyToHourlyConversions",
          statistic: "Maximum",
          dimensionsMap: { DryRun: "Yes" },
        }).with({
          label: "Monthly to Hourly (Dry Run)",
          color: Color.GREEN,
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "HourlyToMonthlyConversions",
          statistic: "Maximum",
          dimensionsMap: { DryRun: "Yes" },
        }).with({
          label: "Hourly to Monthly (Dry Run)",
          color: Color.BLUE,
        }),
      ],
      leftYAxis: {
        label: "Number of WorkSpaces",
        showUnits: false,
        min: 0,
      },
      width: 12,
      height: 6,
      stacked: true,
      legendPosition: LegendPosition.BOTTOM,
      view: GraphWidgetView.TIME_SERIES,
    });

    const hourlyToMonthlyConversionsWidget = new GraphWidget({
      title: "Hourly to Monthly Billing Mode Conversions Over Time",
      left: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "HourlyToMonthlyConversions",
          statistic: "Maximum",
          period: Duration.days(1),
          dimensionsMap: { DryRun: "Yes" },
        }).with({
          label: "Dry Run",
          color: Color.BLUE,
        }),
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "HourlyToMonthlyConversions",
          statistic: "Maximum",
          period: Duration.days(1),
          dimensionsMap: { DryRun: "No" },
        }).with({
          label: "Actual",
          color: Color.GREEN,
        }),
      ],
      leftYAxis: {
        label: "Number of Conversions",
        showUnits: false,
        min: 0,
      },
      width: 12,
      height: 6,
      view: GraphWidgetView.TIME_SERIES,
      stacked: true,
      legendPosition: LegendPosition.BOTTOM,
    });

    const ecsExecutionTimeWidget = new GraphWidget({
      title: "ECS Task Execution Time",
      left: [
        new Metric({
          namespace: "WorkspacesCostOptimizer",
          metricName: "EcsTaskExecutionTime",
          statistic: "Maximum",
          period: Duration.days(1),
        }),
      ],
      leftYAxis: { label: "Minutes", showUnits: false, min: 0 },
      width: 24,
      height: 6,
      legendPosition: LegendPosition.BOTTOM,
      view: GraphWidgetView.TIME_SERIES,
    });

    this.dashboard.addWidgets(
      workspacesHeader,
      new Row(totalWorkspacesWidget, billingDistributionPieWidget, billingDistributionWidget),
      new Row(conversionsWidget, terminatedWorkspacesWidget, terminatedWorkspacesGraphWidget),
      new Row(unconvertedWorkspacesWidget, hourlyToMonthlyConversionsWidget),
      new Row(ecsExecutionTimeWidget),
    );

    Tags.of(this).add("SolutionId", props.solutionId);
    Tags.of(this).add("SolutionVersion", props.solutionVersion);
  }
}
