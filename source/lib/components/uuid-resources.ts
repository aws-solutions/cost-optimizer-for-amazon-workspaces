// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from "aws-cdk-lib";
import { Duration, CustomResource, Tags } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { CfnFunction, Code, Runtime } from "aws-cdk-lib/aws-lambda";
import { Effect, PolicyStatement, Role, ServicePrincipal, Policy } from "aws-cdk-lib/aws-iam";
import { Bucket } from "aws-cdk-lib/aws-s3";
import overrideLogicalId from "../cdk-helper/override-logical-id";
import { addCfnNagSuppression } from "../cdk-helper/add-cfn-nag-suppression";

export interface UUIDResourcesProps extends cdk.StackProps {
  solutionId: string;
  solutionName: string;
  solutionVersion: string;
  solutionBucketName: string;
  logLevel: string;
  solutionDataKey: string;
}

export class UUIDResources extends Construct {
  public readonly uuid: string;

  constructor(scope: Construct, id: string, props: UUIDResourcesProps) {
    super(scope, id);

    const uuidGeneratorFunctionLambdaRole = new Role(this, "UUIDGeneratorFunctionLambdaRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
    });

    const uuidGeneratorFunctionPolicy = new Policy(this, "UUIDGeneratorFunctionPolicy", {
      policyName: "SolutionHelperPolicy",
      statements: [
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
          resources: [
            cdk.Arn.format(
              {
                service: "logs",
                resource: "log-group",
                resourceName: `/${cdk.Aws.PARTITION}/lambda/*`,
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
          actions: ["iam:PassRole"],
          resources: [uuidGeneratorFunctionLambdaRole.roleArn],
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["cloudformation:DescribeStacks"],
          resources: [
            cdk.Arn.format(
              {
                service: "cloudformation",
                resource: "stack",
                resourceName: `${cdk.Aws.STACK_NAME}/*`,
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
          actions: ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
          resources: ["*"],
        }),
      ],
    });

    uuidGeneratorFunctionPolicy.attachToRole(uuidGeneratorFunctionLambdaRole);
    addCfnNagSuppression(uuidGeneratorFunctionPolicy, {
      id: "W12",
      reason: "X-ray requires * policy",
    });
    const deploymentSourceBucket = Bucket.fromBucketAttributes(this, "SolutionRegionalBucket", {
      bucketName: props.solutionBucketName + "-" + cdk.Aws.REGION,
    });

    const uuidGeneratorLambdaFunction = new lambda.Function(this, "UUIDGeneratorLambdaFunction", {
      runtime: Runtime.PYTHON_3_11,
      description: "Solution Helper Lambda Function",
      tracing: lambda.Tracing.ACTIVE,
      timeout: Duration.seconds(300),
      role: uuidGeneratorFunctionLambdaRole.withoutPolicyUpdates(),
      code: Code.fromBucket(
        deploymentSourceBucket,
        `${props.solutionName}/${props.solutionVersion}/uuid_generator.zip`,
      ),
      handler: "uuid_generator/uuid_generator.lambda_handler",
      environment: {
        USER_AGENT_STRING: `AwsSolution/${props.solutionId}/${props.solutionVersion}`,
        LOG_LEVEL: props.logLevel,
      },
    });

    Tags.of(uuidGeneratorLambdaFunction).add(props.solutionDataKey, cdk.Aws.STACK_NAME);
    const cfnUUIDGeneratorLambdaFunction = uuidGeneratorLambdaFunction.node.defaultChild as CfnFunction;
    cfnUUIDGeneratorLambdaFunction.overrideLogicalId("SolutionHelperFunction");
    overrideLogicalId(uuidGeneratorLambdaFunction, "SolutionHelperFunction");
    addCfnNagSuppression(uuidGeneratorLambdaFunction, {
      id: "W58",
      reason: "The lambda function has access to write logs",
    });
    addCfnNagSuppression(uuidGeneratorLambdaFunction, {
      id: "W89",
      reason: "The lambda function does not need access to resources in VPC",
    });
    addCfnNagSuppression(uuidGeneratorLambdaFunction, {
      id: "W92",
      reason:
        "The lambda function only executes on stack creation and deletion and so does not need reserved concurrency.",
    });
    addCfnNagSuppression(uuidGeneratorLambdaFunction, {
      id: "W12",
      reason: "Resource * is necessary for xray:PutTraceSegments and xray:PutTelemetryRecords.",
    });
    overrideLogicalId(uuidGeneratorFunctionLambdaRole, "SolutionHelperRole");
    overrideLogicalId(uuidGeneratorFunctionPolicy, "SolutionHelperPolicy");

    const uuidCustomResource = new CustomResource(this, "UUIDCustomResource", {
      resourceType: "Custom::UUIDGenerator",
      serviceToken: uuidGeneratorLambdaFunction.functionArn,
      properties: {
        Region: cdk.Aws.REGION,
        DependsOn: uuidGeneratorLambdaFunction.functionArn,
      },
    });
    overrideLogicalId(uuidCustomResource, "UUIDGenerator");

    this.uuid = uuidCustomResource.getAtt("UUID").toString();
  }
}
