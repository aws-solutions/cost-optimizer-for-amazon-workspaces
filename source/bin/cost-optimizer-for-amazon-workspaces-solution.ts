// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import {DefaultStackSynthesizer} from 'aws-cdk-lib';
import {CostOptimizerHubStack, CostOptimizerHubStackProps} from "../lib/cost-optimizer-for-amazon-workspaces-hub-stack";
import {CostOptimizerSpokeStack, CostOptimizerSpokeStackProps} from "../lib/cost-optimizer-for-amazon-workspaces-spoke-stack";

function getEnvElement(envVariableName: string): string {
    const value: string | undefined = process.env[envVariableName];
    if (value == undefined) throw new Error(`Missing required environment variable ${envVariableName}`)
    return value;
}

const SOLUTION_VERSION = getEnvElement('SOLUTION_VERSION');
const SOLUTION_NAME = getEnvElement('SOLUTION_NAME');
const SOLUTION_ID = process.env['SOLUTION_ID'] || 'SO0018';
const SOLUTION_BUCKET_NAME = getEnvElement('DIST_OUTPUT_BUCKET');
const SOLUTION_TMN = getEnvElement('SOLUTION_TRADEMARKEDNAME');
const SOLUTION_PROVIDER = 'AWS Solution Development';

const app = new cdk.App();

let costOptimizerHubStackProperties: CostOptimizerHubStackProps = {
    solutionId: SOLUTION_ID,
    solutionTradeMarkName: SOLUTION_TMN,
    solutionProvider: SOLUTION_PROVIDER,
    solutionBucketName: SOLUTION_BUCKET_NAME,
    solutionName: SOLUTION_NAME,
    solutionVersion: SOLUTION_VERSION,
    description: '(' + SOLUTION_ID + ') - '+ SOLUTION_NAME +': A solution for automatically optimizing the cost of Amazon Workspaces version ' + SOLUTION_VERSION,
    synthesizer: new DefaultStackSynthesizer({
    generateBootstrapVersionRule: false
    })
}

let costOptimizerSpokeStackProperties: CostOptimizerSpokeStackProps = {
    solutionId: SOLUTION_ID + 'S',
    solutionTradeMarkName: SOLUTION_TMN,
    solutionProvider: SOLUTION_PROVIDER,
    solutionBucketName: SOLUTION_BUCKET_NAME,
    solutionName: SOLUTION_NAME,
    solutionVersion: SOLUTION_VERSION,
    description: '(' + SOLUTION_ID + 'S' + ') - The AWS CloudFormation spoke template' +
    ' for deployment of the ' + SOLUTION_NAME + ', Version: ' + SOLUTION_VERSION,
    synthesizer: new DefaultStackSynthesizer({
    generateBootstrapVersionRule: false
    })
}

new CostOptimizerHubStack(
    app,
    'cost-optimizer-for-amazon-workspaces',
    costOptimizerHubStackProperties,
);

new CostOptimizerSpokeStack(
    app,
    'cost-optimizer-for-amazon-workspaces-spoke',
    costOptimizerSpokeStackProperties
);

app.synth();