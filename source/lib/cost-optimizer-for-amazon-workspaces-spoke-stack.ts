// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import { Construct } from "constructs";
import { CfnParameter, Aws, Tags, Fn, CfnOutput, 
    Duration, CustomResource } from 'aws-cdk-lib';
import { Policy, Role, PolicyDocument, PolicyStatement,
    ServicePrincipal, ArnPrincipal } from 'aws-cdk-lib/aws-iam'
import { Bucket } from 'aws-cdk-lib/aws-s3';
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Code, Runtime } from "aws-cdk-lib/aws-lambda";
import { AppRegistrySpokeResources, AppRegistrySpokeResourcesProps } from './components/app-registry-spoke-resources';
import overrideLogicalId from './cdk-helper/override-logical-id';
import { addCfnNagSuppression } from './cdk-helper/add-cfn-nag-suppression';
export interface CostOptimizerSpokeStackProps extends cdk.StackProps {
    solutionId: string;
    solutionTradeMarkName: string;
    solutionProvider: string;
    solutionBucketName: string;
    solutionName: string;
    solutionVersion: string;
}

export class CostOptimizerSpokeStack extends cdk.Stack {

    constructor(scope: Construct, id: string, props: CostOptimizerSpokeStackProps) {
        super(scope, id, props);

        const hubAccountId = new CfnParameter(this, 'HubAccountId', {
            description: "The ID of the hub account for the solution. This stack should be deployed in the same region as the hub stack in the hub account.",
            type: "String",
            allowedPattern: '^\\d{12}$',
        });

        const logLevel = new CfnParameter(this, 'LogLevel', {
            type: 'String',
            default: 'INFO',
            allowedValues: ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
        });

        this.templateOptions.metadata = {
            "AWS::CloudFormation::Interface": {
                ParameterGroups: [
                    {
                        Label: {default: "Hub account information"},
                        Parameters: [hubAccountId.logicalId]
                    },
                    {
                        Label: {default: "Testing parameters"},
                        Parameters: [logLevel.logicalId]
                    },
                ],
                ParameterLabels: {
                    [hubAccountId.logicalId]: {
                        default: "Hub account ID",
                    },
                    [logLevel.logicalId]: {
                        default: "Logging level",
                    },
                }
            }
        };

        const mappings = new cdk.CfnMapping(this, "Solution");
        mappings.setValue("Data", "ID", props.solutionId);
        mappings.setValue("Data", "Version", props.solutionVersion);
        mappings.setValue("Data", "HubAccountAdminRoleName", 'Workspaces-Cost-Optimizer');
        mappings.setValue("Data", "HubAccountRegistrationFunctionName", 'Register-Spoke-Accounts');
        mappings.setValue("Data", "SpokeAccountWorkspacesRole", 'Workspaces-Admin-Spoke');
        mappings.setValue("Data", "TagKey", 'CloudFoundations:CostOptimizerForWorkspaces');
        mappings.setValue("Data", "AppRegistryApplicationName", 'workspaces-cost-optimizer');
        

        const workspacesManagementRole = new Role(this, 'WorkspacesManagementRole', {
            assumedBy: new ArnPrincipal(
                Fn.sub('arn:${Partition}:iam::${HubAccountId}:role/${RoleName}-${Region}', {
                    'Partition': cdk.Aws.PARTITION,
                    'HubAccountId': hubAccountId.valueAsString,
                    'RoleName': mappings.findInMap('Data','HubAccountAdminRoleName'),
                    'Region': cdk.Aws.REGION,
                })),
            roleName: `${mappings.findInMap('Data','SpokeAccountWorkspacesRole')}-${cdk.Aws.REGION}`,
        });
        Tags.of(workspacesManagementRole).add(mappings.findInMap('Data','TagKey'),Aws.STACK_NAME);
        overrideLogicalId(workspacesManagementRole, 'WorkSpacesManagementRole');
        addCfnNagSuppression(workspacesManagementRole, {
            id: 'W28',
            reason: 'Static naming is necessary for hub account to assume this role'
        })
        
        const workspacesManagementRolePolicyDocument = new PolicyDocument({
            statements: [new PolicyStatement({
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
                actions: [
                    'cloudwatch:GetMetricStatistics'
                ],
                resources: [
                    `*`,
                ]
            })],
        });

        const workspacesManagementRolePolicy = new Policy(this, 'WorkspacesManagementRolePolicy', {
            policyName: `${cdk.Aws.STACK_NAME}-workspaces-management-role-policy`,
            document: workspacesManagementRolePolicyDocument
        });
        workspacesManagementRolePolicy.attachToRole(workspacesManagementRole);
        overrideLogicalId(workspacesManagementRolePolicy, 'WorkSpacesManagementRolePolicy');
        addCfnNagSuppression(workspacesManagementRolePolicy, {
            id: 'W12',
            reason: 'CloudWatch GetMetricStatistics does not support resource level permissions'
        })
 
        const accountRegistrationProviderRole = new Role(this, 'AccountRegistrationProviderRole', {
            assumedBy: new ServicePrincipal(`lambda.amazonaws.com`)
        });
        Tags.of(accountRegistrationProviderRole).add(mappings.findInMap('Data','TagKey'),Aws.STACK_NAME);
        overrideLogicalId(accountRegistrationProviderRole,'AccountRegistrationProviderRole');

        const accountRegistrationProviderRolePolicyDocument = new PolicyDocument({
            statements: [new PolicyStatement({
                actions: [
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents'
                ],
                resources: [
                    Fn.sub('arn:${Partition}:logs:${Region}:${AccountId}:log-group:/${Partition}/lambda/*', {
                        'Partition': cdk.Aws.PARTITION,
                        'Region': cdk.Aws.REGION,
                        'AccountId': cdk.Aws.ACCOUNT_ID
                    })
                ]
            }),
            new PolicyStatement({
                actions: [
                    'lambda:InvokeFunction'
                ],
                resources: [
                    Fn.sub('arn:${Partition}:lambda:${Region}:${HubAccountId}:function:${FunctionName}-${Region}', {
                        'Partition': cdk.Aws.PARTITION,
                        'Region': cdk.Aws.REGION,
                        'HubAccountId': hubAccountId.valueAsString,
                        'FunctionName': mappings.findInMap('Data','HubAccountRegistrationFunctionName')
                    })
                ]
            }),
            new PolicyStatement({
                actions: [
                    'xray:PutTraceSegments',
                    'xray:PutTelemetryRecords'
                ],
                resources: [
                    '*'
                ]
            })],
        });

        const accountRegistrationProviderRolePolicy = new Policy(this, 'AccountRegistrationProviderRolePolicy', {
            policyName: `${cdk.Aws.STACK_NAME}-account-registration-provider-role-policy`,
            document: accountRegistrationProviderRolePolicyDocument
        });
        accountRegistrationProviderRolePolicy.attachToRole(accountRegistrationProviderRole);
        overrideLogicalId(accountRegistrationProviderRolePolicy, 'AccountRegistrationProviderRolePolicy');

        const deploymentSourceBucket = Bucket.fromBucketAttributes(this, 'SolutionRegionalBucket', {
            bucketName: props.solutionBucketName + '-' + cdk.Aws.REGION
        });

        const accountRegistrationProviderLambdaFunction = new lambda.Function(this, 'AccountRegistrationProvider', {
            description: "WorkspacesCostOptimizer spoke account registration custom resource provider",
            runtime: Runtime.PYTHON_3_9,
            tracing: lambda.Tracing.ACTIVE,
            timeout: Duration.seconds(300),
            role: accountRegistrationProviderRole.withoutPolicyUpdates(),
            code: Code.fromBucket(deploymentSourceBucket, `${props.solutionName}/${props.solutionVersion}/account_registration_provider.zip`),
            handler: 'account_registration_provider.account_registration_provider.event_handler',
            environment: {
                USER_AGENT_STRING: `AwsSolution/${props.solutionId}/${props.solutionVersion}`,
                LOG_LEVEL: logLevel.valueAsString,
                REGISTER_LAMBDA_ARN: `arn:${cdk.Aws.PARTITION}:lambda:${cdk.Aws.REGION}:${hubAccountId.valueAsString}:function:${mappings.findInMap('Data','HubAccountRegistrationFunctionName')}-${cdk.Aws.REGION}`,
                MANAGEMENT_ROLE_ARN: workspacesManagementRole.roleArn
            }
        });

        Tags.of(accountRegistrationProviderLambdaFunction).add(mappings.findInMap('Data','TagKey'),Aws.STACK_NAME);
        overrideLogicalId(accountRegistrationProviderLambdaFunction, "AccountRegistrationProvider");
        addCfnNagSuppression(accountRegistrationProviderLambdaFunction, {
            id: 'W58',
            reason: 'The lambda function has access to write logs'
        })
        addCfnNagSuppression(accountRegistrationProviderLambdaFunction, {
            id: 'W89',
            reason: 'The lambda function does not need access to resources in VPC'
        })
        addCfnNagSuppression(accountRegistrationProviderLambdaFunction, {
            id: 'W92',
            reason: 'The lambda function only executes on stack creation and deletion and so does not need reserved concurrency.'
        })

        const customResource = new CustomResource(this, 'CustomResourceAccountRegistration', {
            resourceType: 'Custom::AccountRegistration',
            serviceToken: accountRegistrationProviderLambdaFunction.functionArn,
        });
        customResource.node.addDependency(accountRegistrationProviderRolePolicy)
        overrideLogicalId(customResource, 'AccountRegistration');

        const appRegistrySpokeResourcesProps: AppRegistrySpokeResourcesProps = {
            solutionId: props.solutionId,
            solutionName: props.solutionName,
            solutionVersion: props.solutionVersion,
            hubAccountId: hubAccountId.valueAsString,
            appRegistryApplicationName: 'workspaces-cost-optimizer',
            applicationType: 'AWS-Solutions'
        }

        new AppRegistrySpokeResources(this, 'AppRegistrySpokeResources', appRegistrySpokeResourcesProps);

        new CfnOutput(this, 'SolutionIDOutput', {
            value: mappings.findInMap('Data','ID'),
            exportName: 'SolutionID'
        }).overrideLogicalId('SolutionID');

        new CfnOutput(this, 'SolutionVersionOutput', {
            value: mappings.findInMap('Data','Version'),
            exportName: 'SolutionVersion'
        }).overrideLogicalId('SolutionVersion');

        new CfnOutput(this, 'LogLevelOutput', {
            value: logLevel.valueAsString,
            exportName: 'LogLevel'
        }).overrideLogicalId('LogLevel');

    }
}

