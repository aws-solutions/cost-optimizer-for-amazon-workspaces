// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import "@aws-cdk/assert/jest";
import { App } from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import {
  CostOptimizerHubStack,
  CostOptimizerHubStackProps,
} from "../lib/cost-optimizer-for-amazon-workspaces-hub-stack";

export const props: CostOptimizerHubStackProps = {
  solutionBucketName: "solutions",
  solutionId: "SO0018",
  solutionName: "workspaces-cost-optimizer",
  solutionProvider: "AWS Solutions",
  solutionTradeMarkName: "workspaces-cost-optimizer",
  solutionVersion: "v2.7.7",
};

/*
 * Regression test.
 * Compares the synthesized cfn template from the cdk project with the snapshot in git.
 *
 * Only update the snapshot after making sure that the differences are intended. (Deployment and extensive manual testing)
 */
test("hub stack synth matches the existing snapshot", () => {
  const app = new App();
  const stack = new CostOptimizerHubStack(app, "CostOptimizerHubStack", props);
  const template = Template.fromStack(stack);
  expect(template).toMatchSnapshot();
});

describe("CloudFormation Template Interface Metadata", () => {
  const app = new App();
  const stack = new CostOptimizerHubStack(app, "CostOptimizerHubStack", props);

  it("should correctly define the Pricing Parameters group with expected parameters", () => {
    const rawTemplate = app.synth().getStackArtifact(stack.artifactId).template;
    const parameterGroups = rawTemplate.Metadata["AWS::CloudFormation::Interface"].ParameterGroups;
    const pricingParamsGroup = parameterGroups.find((group: any) => group.Label.default === "Pricing Parameters");
    expect(pricingParamsGroup).toBeDefined();

    const expectedParams = [
      "ValueLimit",
      "StandardLimit",
      "PerformanceLimit",
      "GraphicsG4dnLimit",
      "GraphicsProG4dnLimit",
      "PowerLimit",
      "PowerProLimit",
    ];

    expectedParams.forEach((param) => {
      expect(pricingParamsGroup.Parameters).toContain(param);
    });
  });
});

describe("Limit Parameters", () => {
  const app = new App();
  const stack = new CostOptimizerHubStack(app, "CostOptimizerHubStack", props);
  const template = Template.fromStack(stack);

  const parameters = [
    {
      name: "ValueLimit",
      default: 81,
      type: "Number",
      description:
        "The number of hours a Value instance can run in a month before being converted to ALWAYS_ON. Default is 81.",
    },
    {
      name: "StandardLimit",
      default: 85,
      type: "Number",
      description:
        "The number of hours a Standard instance can run in a month before being converted to ALWAYS_ON. Default is 85.",
    },
    {
      name: "PerformanceLimit",
      default: 80,
      type: "Number",
      description:
        "The number of hours a Performance instance can run in a month before being converted to ALWAYS_ON. Default is 80.",
    },
    {
      name: "PowerLimit",
      default: 92,
      type: "Number",
      description:
        "The number of hours a Power instance can run in a month before being converted to ALWAYS_ON. Default is 92.",
    },
    {
      name: "PowerProLimit",
      default: 78,
      type: "Number",
      description:
        "The number of hours a Power Pro instance can run in a month before being converted to ALWAYS_ON. Default is 78.",
    },
    {
      name: "GraphicsG4dnLimit",
      default: 334,
      type: "Number",
      description:
        "The number of hours a Graphics.g4dn instance can run in a month before being converted to ALWAYS_ON. Default is 334.",
    },
    {
      name: "GraphicsProG4dnLimit",
      default: 80,
      type: "Number",
      description:
        "The number of hours a GraphicsPro.g4dn instance can run in a month before being converted to ALWAYS_ON. Default is 80.",
    },
  ];

  parameters.forEach((param) => {
    it(`${param.name} should have the correct type, default value, and description`, () => {
      template.hasParameter(param.name, { Type: param.type, Default: param.default, Description: param.description });
    });
  });
});
