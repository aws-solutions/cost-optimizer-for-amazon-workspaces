// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import * as cdk from "aws-cdk-lib";
import * as servicecatalogappregistry from "aws-cdk-lib/aws-servicecatalogappregistry";
import { Aws, Fn, Tags } from "aws-cdk-lib";
import { Construct } from "constructs";

export interface AppRegistryHubResourcesProps extends cdk.StackProps {
  solutionId: string;
  solutionName: string;
  solutionDomain: string;
  solutionVersion: string;
  appRegistryApplicationName: string;
  applicationType: string;
}

export class AppRegistryHubResources extends Construct {
  public readonly applicationTagValue: string;
  constructor(scope: Construct, id: string, props: AppRegistryHubResourcesProps) {
    super(scope, id);
    const application = new servicecatalogappregistry.CfnApplication(this, "AppRegistry", {
      name: Fn.join("-", [props.appRegistryApplicationName, Aws.REGION, Aws.ACCOUNT_ID]),
      description: `Service Catalog application to track and manage all your resources for the solution ${props.solutionName}`,
    });
    application.overrideLogicalId("Application");
    this.applicationTagValue = application.attrApplicationTagValue;

    // Tags for application

    Tags.of(application).add("Solutions:SolutionID", props.solutionId);
    Tags.of(application).add("Solutions:SolutionName", props.solutionName);
    Tags.of(application).add("Solutions:SolutionVersion", props.solutionVersion);
    Tags.of(application).add("Solutions:ApplicationType", props.applicationType);
    Tags.of(application).add("Solutions:SolutionDomain", props.solutionDomain);
    Tags.of(application).add("CloudFoundations:CostOptimizerForWorkspaces", Aws.STACK_NAME);
  }
}
