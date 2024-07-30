// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { Construct } from "constructs";
import * as cdk from "aws-cdk-lib";
import { Bucket, BlockPublicAccess, BucketEncryption, BucketPolicy } from "aws-cdk-lib/aws-s3";
import overrideLogicalId from "../cdk-helper/override-logical-id";
import { addCfnNagSuppression } from "../cdk-helper/add-cfn-nag-suppression";

export class UsageReportBucketResources extends Construct {
  public readonly reportingBucket: Bucket;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const accessLoggingBucket = new Bucket(this, "AccessLoggingBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      enforceSSL: true,
    });
    overrideLogicalId(accessLoggingBucket, "LogsBucket");
    addCfnNagSuppression(accessLoggingBucket, {
      id: "W35",
      reason: " Access logging is not required for this bucket.",
    });
    addCfnNagSuppression(accessLoggingBucket, {
      id: "W51",
      reason: "Policy is not required for this bucket.",
    });

    const costOptimizerBucket = new Bucket(this, "CostOptimizerBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      serverAccessLogsBucket: accessLoggingBucket,
      serverAccessLogsPrefix: "wco_bucket/",
    });
    costOptimizerBucket.addLifecycleRule({
      enabled: true,
      expiration: cdk.Duration.days(365),
      id: "DeletionRule",
    });
    overrideLogicalId(costOptimizerBucket, "CostOptimizerBucket");

    const costOptimizerBucketPolicy = costOptimizerBucket.policy as BucketPolicy;
    overrideLogicalId(costOptimizerBucketPolicy, "S3BucketPolicy");
    addCfnNagSuppression(costOptimizerBucket, {
      id: "W51",
      reason: "Policy is not required for this bucket.",
    });

    this.reportingBucket = costOptimizerBucket;
  }
}
