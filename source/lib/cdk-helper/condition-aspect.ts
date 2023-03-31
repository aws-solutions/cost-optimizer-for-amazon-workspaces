// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
/**
 * CDK Aspect implementation to set up conditions to the entire Construct resources
 */

import { IConstruct } from "constructs"
import { IAspect, CfnCondition, CfnResource } from "aws-cdk-lib";

export class ConditionAspect implements IAspect {
    private readonly condition: CfnCondition;
  
    constructor(condition: CfnCondition) {
      this.condition = condition;
    }
    /**
     * Implement IAspect.visit to set the condition to whole resources in Construct.
     * @param {IConstruct} node Construct node to visit
     */
    visit(node: IConstruct): void {
      const resource = node as CfnResource;
      if (resource.cfnOptions) {
        resource.cfnOptions.condition = this.condition;
      }
    }
  }