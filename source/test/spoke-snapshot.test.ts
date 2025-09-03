// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from "aws-cdk-lib";
import { DefaultStackSynthesizer } from "aws-cdk-lib";
import {
  CostOptimizerSpokeStack,
  CostOptimizerSpokeStackProps,
} from "../lib/cost-optimizer-for-amazon-workspaces-spoke-stack";
import { Template } from "aws-cdk-lib/assertions";

export const costOptimizerSpokeStackProperties: CostOptimizerSpokeStackProps = {
  solutionId: "SO0018",
  solutionTradeMarkName: "cost-optimizer-for-amazon-workspaces",
  solutionProvider: "aws",
  solutionBucketName: "solutions",
  solutionName: "workspaces-cost-optimizer",
  solutionVersion: "v2.8.1",
  description:
    "(" +
    "SO0018" +
    ") - The AWS CloudFormation spoke template" +
    " for deployment of the " +
    "workspaces-cost-optimizer" +
    ", Version: " +
    "v2.8.1",
  synthesizer: new DefaultStackSynthesizer({
    generateBootstrapVersionRule: false,
  }),
};

test("spoke stack synth matches the existing snapshot", () => {
  const app = new cdk.App();
  const costOptimizerSpokeStack = new CostOptimizerSpokeStack(
    app,
    "cost-optimizer-for-amazon-workspaces-spoke",
    costOptimizerSpokeStackProperties,
  );
  const template = Template.fromStack(costOptimizerSpokeStack);
  expect(template.toJSON()).toMatchSnapshot();
});
