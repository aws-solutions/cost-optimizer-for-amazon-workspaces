// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from "aws-cdk-lib";
import { Aws, CfnCondition } from "aws-cdk-lib";
import { CfnCluster, CfnTaskDefinition } from "aws-cdk-lib/aws-ecs";
import { Effect, ServicePrincipal, Role, PolicyStatement, Policy } from "aws-cdk-lib/aws-iam";
import { LogGroup } from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import { Rule, Schedule, IRuleTarget } from "aws-cdk-lib/aws-events";
import overrideLogicalId from "../cdk-helper/override-logical-id";
import { addCfnNagSuppression } from "../cdk-helper/add-cfn-nag-suppression";
import setCondition from "../cdk-helper/set-condition";

export interface EcsClusterResourcesProps extends cdk.StackProps {
  readonly clusterName: string;
  readonly tagKey: string;
  readonly costOptimizerBucketName: string;
  readonly spokeAccountTableName: string;
  readonly usageTable: cdk.aws_dynamodb.Table;
  readonly userSessionTable: cdk.aws_dynamodb.Table;
  readonly ecsTaskLogGroupName: string;
  readonly ecsTaskRoleName: string;
  readonly spokeAcountWorkspacesRoleName: string;
  readonly ecsTaskFamily: string;
  readonly containerImage: string;
  readonly stableContainerImage: string;
  readonly fargateVpcId: string;
  readonly logLevel: string;
  readonly dryRun: string;
  readonly testEndOfMonth: string;
  readonly sendAnonymousData: string;
  readonly solutionVersion: string;
  readonly solutionId: string;
  readonly uuid: string;
  readonly valueLimit: string;
  readonly standardLimit: string;
  readonly performanceLimit: string;
  readonly powerLimit: string;
  readonly powerProLimit: string;
  readonly graphicsG4dnLimit: string;
  readonly graphicsProG4dnLimit: string;
  readonly metricsEndpoint: string;
  readonly userAgentString: string;
  readonly autoStopTimeoutHours: string;
  readonly regions: string;
  readonly terminateUnusedWorkspaces: string;
  readonly spokeAccountDynamoDBTableName: string;
  readonly multiAccountDeploymentCondition: CfnCondition;
  readonly createNewVpcConditionLogicalId: string;
  readonly existingVpcConditionLogicalId: string;
  readonly intraVPCSecurityGroup: string;
  readonly existingSecurityGroupId: string;
  readonly existingPrivateSubnet1Id: string;
  readonly existingPrivateSubnet2Id: string;
  readonly newPrivateSubnet1Id: string;
  readonly newPrivateSubnet2Id: string;
  readonly numberOfmonthsForTerminationCheck: string;
  readonly stableTagCondition: string;
  readonly stableTagInUse: string;
}

export class EcsClusterResources extends Construct {
  public readonly taskClusterName: string;
  public readonly ecsCloudWatchLogGroup: LogGroup;
  public readonly taskDefinitionArn: string;
  public readonly taskExecutionRoleArn: string;

  constructor(scope: Construct, id: string, props: EcsClusterResourcesProps) {
    super(scope, id);

    const ecsCluster = new CfnCluster(this, "EcsCluster", {
      clusterName: props.clusterName,
      clusterSettings: [{ name: "containerInsights", value: "enabled" }],
      tags: [
        {
          key: props.tagKey,
          value: Aws.STACK_NAME,
        },
      ],
    });
    overrideLogicalId(ecsCluster, "CostOptimizerCluster");

    const costOptimizerAdminRole = new Role(this, "CostOptimizerAdminRole", {
      assumedBy: new ServicePrincipal("ecs-tasks.amazonaws.com"),
      roleName: cdk.Fn.join("-", [props.ecsTaskRoleName, cdk.Aws.REGION]),
    });
    overrideLogicalId(costOptimizerAdminRole, "CostOptimizerAdminRole");
    addCfnNagSuppression(costOptimizerAdminRole, {
      id: "W28",
      reason: "Static naming is necessary for hub account to assume this role",
    });
    const adminRoleNode = costOptimizerAdminRole.node.findChild("Resource") as cdk.aws_iam.CfnRole;
    const adminRoleMetadata = adminRoleNode.cfnOptions?.metadata;
    if (adminRoleMetadata) {
      adminRoleMetadata.guard = {
        SuppressedRules: ["CFN_NO_EXPLICIT_RESOURCE_NAMES"],
      };
    }
    const costOptimizerAdminPolicy = new Policy(this, "CostOptimizerAdminPolicy", {
      policyName: "CostOptimizerAdminPolicy",
      statements: [
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
          resources: [
            cdk.Arn.format(
              {
                service: "logs",
                resource: "log-group",
                resourceName: "/ecs/wco-task/*",
                arnFormat: cdk.ArnFormat.COLON_RESOURCE_NAME,
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: [
            "workspaces:DescribeTags",
            "workspaces:DescribeWorkspaces",
            "workspaces:DescribeWorkspaceDirectories",
            "workspaces:ModifyWorkspaceProperties",
            "workspaces:TerminateWorkspaces",
            "workspaces:DescribeWorkspacesConnectionStatus",
          ],
          resources: [
            cdk.Arn.format(
              {
                service: "workspaces",
                resource: "directory",
                resourceName: "*",
                partition: cdk.Aws.PARTITION,
                region: "*",
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
            cdk.Arn.format(
              {
                service: "workspaces",
                resource: "workspace",
                resourceName: "*",
                partition: cdk.Aws.PARTITION,
                region: "*",
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
            cdk.Arn.format(
              {
                service: "workspaces",
                resource: "workspacebundle",
                resourceName: "*",
                partition: cdk.Aws.PARTITION,
                region: "*",
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["s3:PutObject", "s3:GetObject"],
          resources: [
            cdk.Arn.format(
              {
                service: "s3",
                resource: props.costOptimizerBucketName,
                resourceName: "*",
                partition: cdk.Aws.PARTITION,
                region: "",
                account: "",
              },
              cdk.Stack.of(this),
            ),
          ],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["s3:ListBucket"],
          resources: [`arn:${cdk.Aws.PARTITION}:s3:::${props.costOptimizerBucketName}`],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["cloudwatch:GetMetricStatistics", "cloudwatch:GetMetricData"],
          resources: ["*"],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["cloudwatch:PutMetricData"],
          resources: ["*"],
          conditions: {
            StringEquals: {
              "cloudwatch:namespace": "WorkspacesCostOptimizer",
            },
          },
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["sts:AssumeRole"],
          resources: [
            cdk.Arn.format(
              {
                service: "iam",
                resource: "role",
                resourceName: `${props.spokeAcountWorkspacesRoleName}-${cdk.Aws.REGION}`,
                partition: cdk.Aws.PARTITION,
                region: "",
                account: "*",
              },
              cdk.Stack.of(this),
            ),
          ],
        }),
      ],
    });
    props.usageTable.grant(costOptimizerAdminPolicy, "dynamodb:GetItem", "dynamodb:PutItem");
    costOptimizerAdminPolicy.attachToRole(costOptimizerAdminRole);
    overrideLogicalId(costOptimizerAdminPolicy, "CostOptimizerAdminPolicy");
    addCfnNagSuppression(costOptimizerAdminPolicy, {
      id: "W76",
      reason: "Admin policy needed for Fargate container",
    });
    addCfnNagSuppression(costOptimizerAdminPolicy, {
      id: "W12",
      reason: "getMetricData and getMetricStatistics requires * policy",
    });
    props.userSessionTable.grant(costOptimizerAdminPolicy, "dynamodb:BatchWriteItem");
    costOptimizerAdminPolicy.attachToRole(costOptimizerAdminRole);
    overrideLogicalId(costOptimizerAdminPolicy, "CostOptimizerAdminPolicy");

    const costOptimizerDynamoDBPolicy = new Policy(this, "CostOptimizerDynamoDBPolicy", {
      policyName: "CostOptimizerDynamoDBPolicy",
      statements: [
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["dynamodb:Scan"],
          resources: [
            cdk.Arn.format(
              {
                service: "dynamodb",
                resource: "table",
                resourceName: props.spokeAccountTableName,
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
        }),
      ],
    });
    costOptimizerDynamoDBPolicy.attachToRole(costOptimizerAdminRole);
    overrideLogicalId(costOptimizerDynamoDBPolicy, "CostOptimizerDynamoDBPolicy");
    setCondition(costOptimizerDynamoDBPolicy, props.multiAccountDeploymentCondition);

    const ecsTaskLogGroup = new LogGroup(this, "CostOptimizerLogs", {
      logGroupName: cdk.Fn.join("/", [props.ecsTaskLogGroupName, Aws.STACK_NAME]),
      retention: 365,
    });
    overrideLogicalId(ecsTaskLogGroup, "CostOptimizerLogs");
    addCfnNagSuppression(ecsTaskLogGroup, {
      id: "W84",
      reason: "KMS encryption unnecessary for log group",
    });

    const dynamoDbTableName = cdk.Fn.conditionIf(
      props.multiAccountDeploymentCondition.logicalId,
      props.spokeAccountDynamoDBTableName,
      cdk.Aws.NO_VALUE,
    ).toString();

    const image = cdk.Fn.conditionIf(
      props.stableTagCondition,
      props.stableContainerImage,
      props.containerImage,
    ).toString();

    const ecsTaskDefinition = new CfnTaskDefinition(this, "EcsTaskDefinition", {
      cpu: "256",
      family: props.ecsTaskFamily,
      memory: "1024",
      networkMode: "awsvpc",
      executionRoleArn: costOptimizerAdminRole.roleArn,
      requiresCompatibilities: ["FARGATE"],
      taskRoleArn: costOptimizerAdminRole.roleArn,
      tags: [],
      containerDefinitions: [
        {
          essential: true,
          name: "workspace-cost-optimizer",
          image: image,
          cpu: 256,
          readonlyRootFilesystem: true,
          logConfiguration: {
            logDriver: "awslogs",
            options: {
              "awslogs-group": ecsTaskLogGroup.logGroupName,
              "awslogs-stream-prefix": "ecs",
              "awslogs-region": `${Aws.REGION}`,
            },
          },
          environment: [
            {
              name: "LogLevel",
              value: props.logLevel,
            },
            {
              name: "DryRun",
              value: props.dryRun,
            },
            {
              name: "TestEndOfMonth",
              value: props.testEndOfMonth,
            },
            {
              name: "SendAnonymousData",
              value: props.sendAnonymousData,
            },
            {
              name: "SolutionVersion",
              value: props.solutionVersion,
            },
            {
              name: "SolutionID",
              value: props.solutionId,
            },
            {
              name: "UUID",
              value: props.uuid,
            },
            {
              name: "BucketName",
              value: props.costOptimizerBucketName,
            },
            {
              name: "ValueLimit",
              value: props.valueLimit,
            },
            {
              name: "StandardLimit",
              value: props.standardLimit,
            },
            {
              name: "PerformanceLimit",
              value: props.performanceLimit,
            },
            {
              name: "PowerLimit",
              value: props.powerLimit,
            },
            {
              name: "PowerProLimit",
              value: props.powerProLimit,
            },
            {
              name: "GraphicsG4dnLimit",
              value: props.graphicsG4dnLimit,
            },
            {
              name: "GraphicsProG4dnLimit",
              value: props.graphicsProG4dnLimit,
            },
            {
              name: "MetricsEndpoint",
              value: props.metricsEndpoint,
            },
            {
              name: "UserAgentString",
              value: props.userAgentString,
            },
            {
              name: "AutoStopTimeoutHours",
              value: props.autoStopTimeoutHours,
            },
            {
              name: "Regions",
              value: props.regions,
            },
            {
              name: "TerminateUnusedWorkspaces",
              value: props.terminateUnusedWorkspaces,
            },
            {
              name: "SpokeAccountDynamoDBTable",
              value: dynamoDbTableName,
            },
            {
              name: "UsageTable",
              value: props.usageTable.tableName,
            },
            {
              name: "UserSessionTable",
              value: props.userSessionTable.tableName,
            },
            {
              name: "NumberOfMonthsForTerminationCheck",
              value: props.numberOfmonthsForTerminationCheck,
            },
            {
              name: "ImageVersion",
              value: image,
            },
            {
              name: "StableTag",
              value: props.stableTagInUse,
            },
          ],
        },
      ],
    });
    overrideLogicalId(ecsTaskDefinition, "CostOptimizerTaskDefinition");

    const eventsRole = new Role(this, "EventsRuleRole", {
      assumedBy: new ServicePrincipal("events.amazonaws.com"),
    });
    overrideLogicalId(eventsRole, "InvokeECSTaskRole");

    const eventsRolePolicy = new Policy(this, "EventsRolePolicy", {
      policyName: "InvokeECSTaskPolicy",
      statements: [
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["ecs:RunTask"],
          resources: [
            cdk.Arn.format(
              {
                service: "ecs",
                resource: "task-definition",
                resourceName: "wco-task",
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
            cdk.Arn.format(
              {
                service: "ecs",
                resource: "task-definition",
                resourceName: "wco-task:*",
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["iam:PassRole"],
          resources: [costOptimizerAdminRole.roleArn],
        }),
      ],
    });

    eventsRolePolicy.attachToRole(eventsRole);
    overrideLogicalId(eventsRolePolicy, "InvokeECSTaskPolicy");

    const securityGroups = cdk.Fn.conditionIf(
      props.createNewVpcConditionLogicalId,
      props.intraVPCSecurityGroup,
      props.existingSecurityGroupId,
    ).toString();
    const ecsPrivateSubnet1 = cdk.Fn.conditionIf(
      props.createNewVpcConditionLogicalId,
      props.newPrivateSubnet1Id,
      cdk.Aws.NO_VALUE,
    ).toString();
    const ecsPrivateSubnet2 = cdk.Fn.conditionIf(
      props.createNewVpcConditionLogicalId,
      props.newPrivateSubnet2Id,
      cdk.Aws.NO_VALUE,
    ).toString();
    const ecsExistingPrivateSubnet1 = cdk.Fn.conditionIf(
      props.existingVpcConditionLogicalId,
      props.existingPrivateSubnet1Id,
      cdk.Aws.NO_VALUE,
    ).toString();
    const ecsExistingPrivateSubnet2 = cdk.Fn.conditionIf(
      props.existingVpcConditionLogicalId,
      props.existingPrivateSubnet2Id,
      cdk.Aws.NO_VALUE,
    ).toString();

    const ecsTarget: IRuleTarget = {
      bind: () => ({
        id: "CostOptimizerTaskDefinition",
        arn: ecsCluster.attrArn,
        role: eventsRole,
        ecsParameters: {
          launchType: "FARGATE",
          taskDefinitionArn: ecsTaskDefinition.attrTaskDefinitionArn,
          propagateTags: "TASK_DEFINITION",
          networkConfiguration: {
            awsVpcConfiguration: {
              assignPublicIp: "DISABLED",
              securityGroups: [securityGroups],
              subnets: [ecsPrivateSubnet1, ecsPrivateSubnet2, ecsExistingPrivateSubnet1, ecsExistingPrivateSubnet2],
            },
          },
        },
      }),
    };

    const scheduleRule = new Rule(this, "rule", {
      enabled: true,
      description: "Rule to trigger WorkSpacesCostOptimizer function on a schedule.",
      schedule: Schedule.cron({ minute: "0", hour: "23", day: "*", year: "*" }),
      targets: [ecsTarget],
    });
    overrideLogicalId(scheduleRule, "ScheduleRule");

    this.taskClusterName = ecsCluster.ref;
    this.taskExecutionRoleArn = costOptimizerAdminRole.roleArn;
    this.ecsCloudWatchLogGroup = ecsTaskLogGroup;
    this.taskDefinitionArn = ecsTaskDefinition.ref;
  }
}
