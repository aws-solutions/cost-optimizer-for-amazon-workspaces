// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { CfnResource } from "aws-cdk-lib";
import { IConstruct } from "constructs";

export default function overrideLogicalId(resource: IConstruct | CfnResource, logicalId: string) {
  let cfnResource = resource as CfnResource;
  if (!cfnResource.cfnOptions) {
    cfnResource = resource.node.defaultChild as CfnResource;
  }
  if (!cfnResource) {
    throw new Error("Unable to override logical ID, not a CfnResource");
  }
  cfnResource.overrideLogicalId(logicalId);
}
