// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { Aws, Fn, Tags, aws_applicationinsights as applicationinsights } from "aws-cdk-lib";
import * as appreg from "@aws-cdk/aws-servicecatalogappregistry-alpha";
import { CfnAttributeGroupAssociation, CfnResourceAssociation } from "aws-cdk-lib/aws-servicecatalogappregistry";
import { Construct } from "constructs";
import overrideLogicalId from "../cdk-helper/override-logical-id";
export interface AppRegistrySpokeResourcesProps {
  solutionId: string;
  solutionName: string;
  solutionVersion: string;
  hubAccountId: string;
  appRegistryApplicationName: string;
  applicationType: string;
}

export class AppRegistrySpokeResources extends Construct {
  constructor(scope: Construct, id: string, props: AppRegistrySpokeResourcesProps) {
    super(scope, id);

    const resourceAssociation = new CfnResourceAssociation(this, "AppRegistryApplicationStackAssociation", {
      application: Fn.join("-", [props.appRegistryApplicationName, Aws.REGION, props.hubAccountId]),
      resource: Aws.STACK_ID,
      resourceType: "CFN_STACK",
    });
    overrideLogicalId(resourceAssociation, "AppRegistryApplicationStackAssociation");

    const attributeGroup = new appreg.AttributeGroup(this, "DefaultApplicationAttributes", {
      attributeGroupName: `${Aws.REGION}-${Aws.STACK_NAME}`,
      description: "Attribute group for solution information",
      attributes: {
        applicationType: props.applicationType,
        version: props.solutionVersion,
        solutionID: props.solutionId,
        solutionName: props.solutionName,
      },
    });
    Tags.of(attributeGroup).add("CloudFoundations:CostOptimizerForWorkspaces", Aws.STACK_NAME);
    overrideLogicalId(attributeGroup, "DefaultApplicationAttributes");

    const attributeGroupAssociation = new CfnAttributeGroupAssociation(
      this,
      "AppRegistryApplicationAttributeAssociation",
      {
        application: Fn.join("-", [props.appRegistryApplicationName, Aws.REGION, props.hubAccountId]),
        attributeGroup: attributeGroup.attributeGroupId,
      },
    );
    overrideLogicalId(attributeGroupAssociation, "AppRegistryApplicationAttributeAssociation");

    const applicationInsightsConfiguration = new applicationinsights.CfnApplication(
      this,
      "ApplicationInsightsConfiguration",
      {
        resourceGroupName: `AWS_CloudFormation_Stack-${Aws.STACK_NAME}`,
        autoConfigurationEnabled: true,
        cweMonitorEnabled: true,
        opsCenterEnabled: true,
      },
    );
    Tags.of(applicationInsightsConfiguration).add("CloudFoundations:CostOptimizerForWorkspaces", Aws.STACK_NAME);
    overrideLogicalId(applicationInsightsConfiguration, "ApplicationInsightsConfiguration");
  }
}
