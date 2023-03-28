// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import {Duration} from 'aws-cdk-lib';
import {Construct} from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import {CfnPermission, Code,Runtime} from "aws-cdk-lib/aws-lambda";
import { Effect, PolicyStatement, Role, ServicePrincipal, Policy, AnyPrincipal } from 'aws-cdk-lib/aws-iam';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import overrideLogicalId from '../cdk-helper/override-logical-id';
import { addCfnNagSuppression } from '../cdk-helper/add-cfn-nag-suppression';
export interface RegisterSpokeAccountResourcesProps extends cdk.StackProps {
    solutionId: string;
    solutionName: string;
    solutionVersion: string;
    solutionBucketName: string;
    spokeAccountTableName: string;
    logLevel: string;
    organizationId: string,
    registerSpokeAccountLambdaFunctionName: string
}

export class RegisterSpokeAccountResources extends Construct {

    constructor(scope: Construct, id: string, props: RegisterSpokeAccountResourcesProps) {
        super(scope, id);

        const registerSpokeAccountsFunctionLambdaRole = new Role(this, 'RegisterSpokeAccountsFunctionLambdaRole', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com')
        });
        overrideLogicalId(registerSpokeAccountsFunctionLambdaRole, 'RegisterSpokeAccountsFunctionLambdaRole')

        const registerSpokeAccountsFunctionLambdaPolicy = new Policy(this, 'RegisterSpokeAccountsFunctionLambdaPolicy', {
            policyName: 'InvokeECSTaskPolicy',
            statements: [
                new PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: [
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents'
                    ],
                    resources: [
                        `arn:${cdk.Aws.PARTITION}:logs:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:log-group:/${cdk.Aws.PARTITION}/lambda/*`
                    ]
                }),
                new PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: [
                        'dynamodb:PutItem',
                        'dynamodb:DeleteItem',
                    ],
                    resources: [
                        `arn:${cdk.Aws.PARTITION}:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.spokeAccountTableName}`
                    ]
                }),
                new PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: [
                        'iam:PassRole'
                    ],
                    resources: [
                        registerSpokeAccountsFunctionLambdaRole.roleArn
                    ]
                }),
                new PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: [
                        'xray:PutTraceSegments',
                        'xray:PutTelemetryRecords'
                    ],
                    resources: ['*']
                })
            ]
        });

        registerSpokeAccountsFunctionLambdaPolicy.attachToRole(registerSpokeAccountsFunctionLambdaRole)
        overrideLogicalId(registerSpokeAccountsFunctionLambdaPolicy, 'RegisterSpokeAccountsFunctionLambdaPolicy')

        const deploymentSourceBucket = Bucket.fromBucketAttributes(this, 'SolutionRegionalBucket', {
            bucketName: props.solutionBucketName + '-' + cdk.Aws.REGION
        });

        const registerSpokeAccountLambdaFunction = new lambda.Function(this, 'RegisterSpokeAccountLambdaFunction', {
            functionName: cdk.Fn.join("-", [props.registerSpokeAccountLambdaFunctionName, cdk.Aws.REGION]),
            runtime: Runtime.PYTHON_3_9,
            tracing: lambda.Tracing.ACTIVE,
            timeout: Duration.seconds(20),
            role: registerSpokeAccountsFunctionLambdaRole.withoutPolicyUpdates(),
            code: Code.fromBucket(deploymentSourceBucket, `${props.solutionName}/${props.solutionVersion}/register_spoke_lambda.zip`),
            handler: 'register_spoke_lambda/register_spoke_accounts.lambda_handler',
            environment: {
                USER_AGENT_STRING: `AwsSolution/${props.solutionId}/${props.solutionVersion}`,
                DDB_TABLE_NAME: props.spokeAccountTableName,
                LOG_LEVEL: props.logLevel
            },
            
        });

        registerSpokeAccountLambdaFunction.addPermission('SpokeAccountLambdaFunctionPermission',{
            action: 'lambda:InvokeFunction',
            principal: new AnyPrincipal(),
            organizationId: props.organizationId
        })
        overrideLogicalId(registerSpokeAccountLambdaFunction, 'RegisterSpokeAccountsFunction')
        addCfnNagSuppression(registerSpokeAccountLambdaFunction, {
            id: 'W58',
            reason: 'The lambda function has access to write logs'
        })
        addCfnNagSuppression(registerSpokeAccountLambdaFunction, {
            id: 'W89',
            reason: 'The lambda function does not need access to resources in VPC'
        })
        addCfnNagSuppression(registerSpokeAccountLambdaFunction, {
            id: 'W92',
            reason: 'ReservedConcurrentExecutions depends on the number of events for event bus'
        })
        addCfnNagSuppression(registerSpokeAccountLambdaFunction, {
            id: 'W12',
            reason: 'Resource * is necessary for xray:PutTraceSegments and xray:PutTelemetryRecords.'
        })

        const cfnLambdaPermission = registerSpokeAccountLambdaFunction.node.children[1] as CfnPermission
        overrideLogicalId(cfnLambdaPermission, 'RegisterSpokeAccountsFunctionResourcePolicy')
        addCfnNagSuppression(cfnLambdaPermission, {
            id: 'F13',
            reason: 'Lambda principal is a wildcard to allow persmissions to all accounts in the Organization.'
        })
    }
}