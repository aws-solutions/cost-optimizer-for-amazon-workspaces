// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import * as cdk from "aws-cdk-lib";
import * as appreg from "@aws-cdk/aws-servicecatalogappregistry-alpha";
import { Aws, CfnCondition, Fn, Tags } from "aws-cdk-lib";
import { CfnApplication } from "aws-cdk-lib/aws-applicationinsights";
import { CfnAttributeGroup, CfnAttributeGroupAssociation, CfnResourceAssociation } from "aws-cdk-lib/aws-servicecatalogappregistry";
import { CfnResourceShare } from "aws-cdk-lib/aws-ram";
import { Construct } from "constructs";
import overrideLogicalId from "../cdk-helper/override-logical-id";
import setCondition from "../cdk-helper/set-condition";

export interface AppRegistryHubResourcesProps extends cdk.StackProps {
    solutionId: string;
    solutionName: string;
    solutionDomain: string;
    solutionVersion: string;
    appRegistryApplicationName: string;
    applicationType: string;
    managementAccountId: string;
    orgId: string,
    multiAccountDeploymentCondition: CfnCondition
}

export class AppRegistryHubResources extends Construct {
    constructor(scope: Construct, id: string, props: AppRegistryHubResourcesProps ) {
    super(scope, id);
    const application = new appreg.Application(this, "AppRegistry", {
        applicationName: Fn.join("-", [
        props.appRegistryApplicationName,
        Aws.REGION,
        Aws.ACCOUNT_ID,
    ]),
    description: `Service Catalog application to track and manage all your resources for the solution ${props.solutionName}`,
    });
    const cfnApplication = application.node.defaultChild as CfnApplication
    overrideLogicalId(cfnApplication, 'Application')

    const cfnresourceAssociation = new CfnResourceAssociation(this, 'CfnResourceAssociation', {
        application: application.applicationId,
        resource: Aws.STACK_ID,
        resourceType: 'CFN_STACK'
    })
    overrideLogicalId(cfnresourceAssociation, 'AppRegistryApplicationStackAssociation')

    const attributeGroup = new appreg.AttributeGroup(this, "DefaultApplicationAttributeGroup", {
        attributeGroupName: Fn.join("-", [
            props.appRegistryApplicationName,
            Aws.REGION,
            Aws.ACCOUNT_ID
        ]),
        description: "Attribute group for solution information",
        attributes: {
            applicationType: props.applicationType,
            version: props.solutionVersion,
            solutionID: props.solutionId,
            solutionName: props.solutionName,
        },
    });
    
    const cfnAttributeGroup = attributeGroup.node.defaultChild as CfnAttributeGroup
    overrideLogicalId(cfnAttributeGroup, 'DefaultApplicationAttributeGroup')

    const cfnAttributeGroupAssociation = new CfnAttributeGroupAssociation(this, 'AttributeGroupAssociation', {
        application: application.applicationId,
        attributeGroup: attributeGroup.attributeGroupId
    })
    overrideLogicalId(cfnAttributeGroupAssociation, 'AppRegistryApplicationAttributeAssociation')

    const appInsights = new CfnApplication(this, "ApplicationInsightsConfiguration", {
        resourceGroupName: Fn.join("-", [
            "AWS_AppRegistry_Application",
            props.appRegistryApplicationName,
            Aws.REGION,
            Aws.ACCOUNT_ID,
        ]),
        autoConfigurationEnabled: true,
        cweMonitorEnabled: true,
        opsCenterEnabled: true,
    });
    appInsights.addDependency(cfnApplication)
    overrideLogicalId(appInsights, 'ApplicationInsightsConfiguration')
    
    const resourceShare = new CfnResourceShare(this, "ApplicationShare", {
        name: Aws.STACK_NAME,
        allowExternalPrincipals: false,
        permissionArns: [
            `arn:${Aws.PARTITION}:ram::aws:permission/AWSRAMPermissionServiceCatalogAppRegistryApplicationAllowAssociation`,
        ],
        principals: [
            `arn:${Aws.PARTITION}:organizations::${props.managementAccountId}:organization/${props.orgId}`,
        ],
        resourceArns: [application.applicationArn],
    });

    overrideLogicalId(resourceShare, 'ApplicationShare')
    setCondition(resourceShare, props.multiAccountDeploymentCondition)

    // Tags for application

    Tags.of(application).add("SolutionID", props.solutionId);
    Tags.of(application).add("SolutionName", props.solutionName);
    Tags.of(application).add("SolutionVersion", props.solutionVersion);
    Tags.of(application).add("ApplicationType", props.applicationType);
    Tags.of(application).add("SolutionDomain", props.solutionDomain);
    Tags.of(application).add("CloudFoundations:CostOptimizerForWorkspaces", Aws.STACK_NAME);

    }
}

