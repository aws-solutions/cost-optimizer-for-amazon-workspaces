// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import '@aws-cdk/assert/jest';
import {App} from 'aws-cdk-lib';
import {Template} from "aws-cdk-lib/assertions";
import {CostOptimizerHubStack, CostOptimizerHubStackProps} from "../lib/cost-optimizer-for-amazon-workspaces-hub-stack";

export const props: CostOptimizerHubStackProps = {
    solutionBucketName: 'solutions',
    solutionId: 'SO0218',
    solutionName: 'workspaces-cost-optimizer',
    solutionProvider: 'AWS Solutions',
    solutionTradeMarkName: 'workspaces-cost-optimizer',
    solutionVersion: 'v2.6.0'
};

/*
 * Regression test.
 * Compares the synthesized cfn template from the cdk project with the snapshot in git.
 *
 * Only update the snapshot after making sure that the differences are intended. (Deployment and extensive manual testing)
 */
test('hub stack synth matches the existing snapshot', () => {
    const app = new App();
    const stack = new CostOptimizerHubStack( app, 'CostOptimizerHubStack', props);
    const template = Template.fromStack(stack);
    expect(template).toMatchSnapshot();
});
