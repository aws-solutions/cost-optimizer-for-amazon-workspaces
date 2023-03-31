// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from "aws-cdk-lib";
import { Aws, CfnCondition } from 'aws-cdk-lib';
import { CfnCluster, CfnTaskDefinition } from 'aws-cdk-lib/aws-ecs';
import { Effect, ServicePrincipal, Role, PolicyStatement, Policy } from 'aws-cdk-lib/aws-iam';
import { LogGroup } from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import {Rule, Schedule, IRuleTarget, } from 'aws-cdk-lib/aws-events'
import overrideLogicalId from "../cdk-helper/override-logical-id";
import { addCfnNagSuppression } from "../cdk-helper/add-cfn-nag-suppression";
import setCondition from "../cdk-helper/set-condition";

export interface EcsClusterResourcesProps extends cdk.StackProps {
    readonly clusterName: string;
    readonly tagKey: string;
    readonly costOptimizerBucketName: string;
    readonly spokeAccountTableName: string;
    readonly ecsTaskLogGroupName: string;
    readonly ecsTaskRoleName: string;
    readonly spokeAcountWorkspacesRoleName: string
    readonly ecsTaskFamily: string
    readonly containerImage: string;
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
    readonly graphicsLimit: string;
    readonly graphicsProLimit: string;
    readonly metricsEndpoint: string;
    readonly userAgentString: string;
    readonly autoStopTimeoutHours: string;
    readonly regions: string;
    readonly terminateUnusedWorkspaces: string;
    readonly spokeAccountDynamoDBTableName: string
    readonly multiAccountDeploymentCondition: CfnCondition
    readonly createNewVpcConditionLogicalId: string
    readonly existingVpcConditionLogicalId: string
    readonly intraVPCSecurityGroup: string
    readonly existingSecurityGroupId: string
    readonly existingSubnetId1: string
    readonly existingSubnetId2: string
    readonly newSubnetId1: string
    readonly newSubnetId2: string,
    readonly numberOfmonthsForTerminationCheck: string
}


export class EcsClusterResources extends Construct {
    public readonly taskClusterName: string;
    public readonly ecsCloudWatchLogGroup: LogGroup;
    public readonly taskDefinitionArn: string;
    public readonly taskExecutionRoleArn: string;

    constructor(scope: Construct, id: string, props: EcsClusterResourcesProps ) {
    
    super(scope, id);

    const ecsCluster = new CfnCluster(this, 'EcsCluster', {
        clusterName: props.clusterName,
        clusterSettings: [{ 'name': 'containerInsights', 'value': 'enabled' }],
        tags: [
            {
            'key': props.tagKey,
            'value': Aws.STACK_NAME
            }
        ]
    });
    overrideLogicalId(ecsCluster, 'CostOptimizerCluster')

    const costOptimizerAdminRole = new Role(this, 'CostOptimizerAdminRole', {
        assumedBy: new ServicePrincipal('ecs-tasks.amazonaws.com'),
        roleName: cdk.Fn.join('-', [props.ecsTaskRoleName, cdk.Aws.REGION])
    });
    overrideLogicalId(costOptimizerAdminRole, 'CostOptimizerAdminRole')
    addCfnNagSuppression(costOptimizerAdminRole, {
        id: 'W28',
        reason: 'Static naming is necessary for hub account to assume this role'
    })
    
    const costOptimizerAdminPolicy = new Policy(this, 'CostOptimizerAdminPolicy', {
        policyName: 'CostOptimizerAdminPolicy',
        statements: [
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents'
                ],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:logs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:log-group:/ecs/wco-task/*`
                ]
            }),
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'ecr:GetAuthorizationToken'
                ],
                resources: ['*']
            }),
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'workspaces:DescribeTags',
                    'workspaces:DescribeWorkspaces',
                    'workspaces:DescribeWorkspaceDirectories',
                    'workspaces:ModifyWorkspaceProperties',
                    'workspaces:TerminateWorkspaces',
                    'workspaces:DescribeWorkspacesConnectionStatus'
                ],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:workspaces:*:${cdk.Aws.ACCOUNT_ID}:directory/*`,
                    `arn:${cdk.Aws.PARTITION}:workspaces:*:${cdk.Aws.ACCOUNT_ID}:workspace/*`,
                    `arn:${cdk.Aws.PARTITION}:workspaces:*:${cdk.Aws.ACCOUNT_ID}:workspacebundle/*`
                ]
            }),
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    's3:PutObject'
                ],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:s3:::${props.costOptimizerBucketName}/*`,
                ]
            }),
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'cloudwatch:GetMetricStatistics'
                ],
                resources: ['*']
            }),
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'sts:AssumeRole'
                ],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:iam::*:role/${props.spokeAcountWorkspacesRoleName}-${cdk.Aws.REGION}`
                ]
            })
        ]
    })
    costOptimizerAdminPolicy.attachToRole(costOptimizerAdminRole)
    overrideLogicalId(costOptimizerAdminPolicy, 'CostOptimizerAdminPolicy')
    addCfnNagSuppression(costOptimizerAdminPolicy, {
        id: 'W12',
        reason: 'ecr:GetAuthorizationToken only supports * as the resource'
    })
    
    const costOptimizerDynamoDBPolicy = new Policy(this, 'CostOptimizerDynamoDBPolicy', {
        policyName: 'CostOptimizerDynamoDBPolicy',
        statements: [
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'dynamodb:Scan'
                ],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.spokeAccountTableName}`,
                ]
            })
        ]

    })
    costOptimizerDynamoDBPolicy.attachToRole(costOptimizerAdminRole)
    overrideLogicalId(costOptimizerDynamoDBPolicy, 'CostOptimizerDynamoDBPolicy')
    setCondition(costOptimizerDynamoDBPolicy, props.multiAccountDeploymentCondition)

    const ecsTaskLogGroup = new LogGroup(this, 'CostOptimizerLogs', {
        logGroupName: cdk.Fn.join('/',[props.ecsTaskLogGroupName, Aws.STACK_NAME]),
        retention: 365
    });
    overrideLogicalId(ecsTaskLogGroup, 'CostOptimizerLogs')
    addCfnNagSuppression(ecsTaskLogGroup, {
        id: 'W84',
        reason: 'KMS encryption unnecessary for log group'
    })

    const dynamoDbTableName = cdk.Fn.conditionIf(props.multiAccountDeploymentCondition.logicalId, props.spokeAccountDynamoDBTableName, cdk.Aws.NO_VALUE).toString()
    
    const ecsTaskDefinition = new CfnTaskDefinition(this, 'EcsTaskDefinition', {
        cpu: '256',
        family: props.ecsTaskFamily,
        memory: '1024',
        networkMode: 'awsvpc',
        executionRoleArn: costOptimizerAdminRole.roleArn,
        requiresCompatibilities: ['FARGATE'],
        taskRoleArn: costOptimizerAdminRole.roleArn,
        tags:[],
        containerDefinitions: [{
            essential: true,
            name: 'workspace-cost-optimizer',
            image: props.containerImage,
            cpu: 256,
            readonlyRootFilesystem: true,
            logConfiguration: {
                logDriver: 'awslogs',
                options: {
                'awslogs-group': ecsTaskLogGroup.logGroupName,
                'awslogs-stream-prefix': 'ecs',
                'awslogs-region': `${Aws.REGION}`
                }
            },
            environment: [
                {
                    name: 'LogLevel',
                    value: props.logLevel
                },
                {
                    name: 'DryRun',
                    value: props.dryRun
                },
                {
                    name: 'TestEndOfMonth',
                    value: props.testEndOfMonth
                },
                {
                    name: 'SendAnonymousData',
                    value: props.sendAnonymousData
                },
                {
                    name: 'SolutionVersion',
                    value: props.solutionVersion
                },
                {
                    name: 'SolutionID',
                    value: props.solutionId
                },
                {
                    name: 'UUID',
                    value: props.uuid
                },
                {
                    name: 'BucketName',
                    value: props.costOptimizerBucketName
                },
                {
                    name: 'ValueLimit',
                    value: props.valueLimit
                },
                {
                    name: 'StandardLimit',
                    value: props.standardLimit
                },
                {
                    name: 'PerformanceLimit',
                    value: props.performanceLimit
                },
                {
                    name: 'PowerLimit',
                    value: props.powerLimit
                },
                {
                    name: 'PowerProLimit',
                    value: props.powerProLimit
                },
                {
                    name: 'GraphicsLimit',
                    value: props.graphicsLimit
                },
                {
                    name: 'GraphicsProLimit',
                    value: props.graphicsProLimit
                },
                {
                    name: 'MetricsEndpoint',
                    value: props.metricsEndpoint
                },
                {
                    name: 'UserAgentString',
                    value: props.userAgentString
                },
                {
                    name: 'AutoStopTimeoutHours',
                    value: props.autoStopTimeoutHours
                },
                {
                    name: 'Regions',
                    value: props.regions
                },
                {
                    name: 'TerminateUnusedWorkspaces',
                    value: props.terminateUnusedWorkspaces
                },
                {
                    name: 'SpokeAccountDynamoDBTable',
                    value: dynamoDbTableName
                },
                {
                    name: 'NumberOfMonthsForTerminationCheck',
                    value: props.numberOfmonthsForTerminationCheck
                }

            ]
        }],
    });
    overrideLogicalId(ecsTaskDefinition, 'CostOptimizerTaskDefinition')

    const eventsRole = new Role(this, 'EventsRuleRole', {
        assumedBy: new ServicePrincipal('events.amazonaws.com'),
    });
    overrideLogicalId(eventsRole, 'InvokeECSTaskRole')
    

    const eventsRolePolicy = new Policy(this, 'EventsRolePolicy', {
        policyName: 'InvokeECSTaskPolicy',
        statements: [
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'ecs:RunTask'
                ],
                resources:[
                    `arn:${cdk.Aws.PARTITION}:ecs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:task-definition/wco-task`,
                    `arn:${cdk.Aws.PARTITION}:ecs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:task-definition/wco-task:*`,
                ]
            }),
            new PolicyStatement({
                effect: Effect.ALLOW,
                actions: [
                    'iam:PassRole'
                ],
                resources:[
                    costOptimizerAdminRole.roleArn
                ]
            })
        ]
    })

    eventsRolePolicy.attachToRole(eventsRole)
    overrideLogicalId(eventsRolePolicy, 'InvokeECSTaskPolicy')

    const securityGroups = cdk.Fn.conditionIf(props.createNewVpcConditionLogicalId, props.intraVPCSecurityGroup, props.existingSecurityGroupId).toString()
    const ecsSubnet1 = cdk.Fn.conditionIf(props.createNewVpcConditionLogicalId, props.newSubnetId1, cdk.Aws.NO_VALUE).toString()
    const ecsSubnet2 = cdk.Fn.conditionIf(props.createNewVpcConditionLogicalId, props.newSubnetId2, cdk.Aws.NO_VALUE).toString()
    const ecsSubnet3 = cdk.Fn.conditionIf(props.existingVpcConditionLogicalId, props.existingSubnetId1, cdk.Aws.NO_VALUE).toString()
    const ecsSubnet4 = cdk.Fn.conditionIf(props.existingVpcConditionLogicalId, props.existingSubnetId2, cdk.Aws.NO_VALUE).toString()

    const ecsTarget: IRuleTarget = {
        bind: () => ({
            id: 'CostOptimizerTaskDefinition',
            arn: ecsCluster.attrArn,
            role: eventsRole,
            ecsParameters:{
                launchType: 'FARGATE',
                taskDefinitionArn: ecsTaskDefinition.attrTaskDefinitionArn,
                propagateTags: 'TASK_DEFINITION',
                networkConfiguration: {
                    awsVpcConfiguration: {
                        assignPublicIp: 'ENABLED',
                        securityGroups:[securityGroups],
                        subnets: [ecsSubnet1, ecsSubnet2, ecsSubnet3, ecsSubnet4]
                    }
                }
            }

        })
    }

    const scheduleRule = new Rule(this, 'rule', {
        enabled: true,
        description: 'Rule to trigger WorkSpacesCostOptimizer function on a schedule.',
        schedule: Schedule.cron({minute: '0', hour: '23', day: '*', year: '*' }),
        targets: [ecsTarget]
    });
    overrideLogicalId(scheduleRule, 'ScheduleRule')
    
    this.taskClusterName = ecsCluster.ref;
    this.taskExecutionRoleArn = costOptimizerAdminRole.roleArn;
    this.ecsCloudWatchLogGroup = ecsTaskLogGroup
    this.taskDefinitionArn = ecsTaskDefinition.ref;

    }
}