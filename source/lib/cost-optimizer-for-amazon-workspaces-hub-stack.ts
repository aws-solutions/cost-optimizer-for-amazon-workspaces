// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import {CfnParameter, Aws, Aspects, CfnOutput} from 'aws-cdk-lib';
import {Construct} from "constructs";
import { VpcResources, VpcResourcesProps } from './components/vpc-resources';
import { ConditionAspect } from './cdk-helper/condition-aspect'
import { UsageReportBucketResources } from './components/usage-report-bucket-resources';
import { AttributeType, BillingMode, Table, TableEncryption } from 'aws-cdk-lib/aws-dynamodb';
import { EcsClusterResources, EcsClusterResourcesProps } from './components/ecs-cluster-resources';
import { RegisterSpokeAccountResources, RegisterSpokeAccountResourcesProps} from './components/register-spoke-account-resources';
import { UUIDResources, UUIDResourcesProps } from './components/uuid-resources';
import { AppRegistryHubResources, AppRegistryHubResourcesProps } from './components/app-registry-hub-resources';
import overrideLogicalId from './cdk-helper/override-logical-id';
import setCondition from './cdk-helper/set-condition';
export interface CostOptimizerHubStackProps extends cdk.StackProps {
    solutionId: string;
    solutionTradeMarkName: string;
    solutionProvider: string;
    solutionBucketName: string;
    solutionName: string;
    solutionVersion: string;
}

export class CostOptimizerHubStack extends cdk.Stack {

    constructor(scope: Construct, id: string, props: CostOptimizerHubStackProps) {
        super(scope, id, props);

        const createNewVPC = new CfnParameter(this, 'CreateNewVPC', {
            description: 'Select "Yes" to deploy the solution in a new VPC.',
            type: 'String',
            default: 'Yes',
            allowedValues: ['Yes', 'No']
        });

        const existingSubnet1Id = new CfnParameter(this, 'ExistingSubnet1Id', {
            description: 'Subnet ID to launch ECS task. Leave this blank is you selected "Yes" for "Create New VPC"',
            type: 'String',
            default: ''
        });

        const existingSubnet2Id = new CfnParameter(this, 'ExistingSubnet2Id', {
            description: 'Subnet ID to launch ECS task. Leave this blank is you selected "Yes" for "Create New VPC"',
            type: 'String',
            default: ''
        });

        const existingSecurityGroupId = new CfnParameter(this, 'ExistingSecurityGroupId', {
            description: 'Security Group Id to launch ECS task. Leave this blank is you selected "Yes" for "Create New VPC"',
            type: 'String',
            default: ''
        });

        const vpcCIDR = new CfnParameter(this, 'VpcCIDR', {
            description: 'This VPC launches containers. Change addresses only if it conflicts with your network.',
            type: 'String',
            default: '10.215.0.0/16',
            allowedPattern: '(?:^$|(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2}))',
            constraintDescription: 'must be a valid IP CIDR range of the form x.x.x.x/x.',
            minLength: 9,
            maxLength: 18
        });

        const subnet1CIDR = new CfnParameter(this, 'Subnet1CIDR', {
            type: 'String',
            default: '10.215.10.0/24',
            allowedPattern: '(?:^$|(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2}))',
            constraintDescription: 'must be a valid IP CIDR range of the form x.x.x.x/x.',
            minLength: 9,
            maxLength: 18
        });

        const subnet2CIDR = new CfnParameter(this, 'Subnet2CIDR', {
            type: 'String',
            default: '10.215.20.0/24',
            allowedPattern: '(?:^$|(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2}))',
            constraintDescription: 'must be a valid IP CIDR range of the form x.x.x.x/x.',
            minLength: 9,
            maxLength: 18
        });

        const egressCIDR = new CfnParameter(this, 'EgressCIDR', {
            type: 'String',
            description: 'The Cidir Block to restrict the ECS container outbound access',
            default: '0.0.0.0/0',
            allowedPattern: '(?:^$|(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2}))',
            constraintDescription: 'must be a valid IP CIDR range of the form x.x.x.x/x.',
            minLength: 9,
            maxLength: 18
        });

        const logLevel = new CfnParameter(this, 'LogLevel', {
            type: 'String',
            default: 'INFO',
            allowedValues: ['CRITICAL', 'ERROR', 'INFO', 'WARNING', 'DEBUG']
        });

        const dryRun = new CfnParameter(this, 'DryRun', {
            type: 'String',
            description: 'Solution will generate a change log, but not execute any changes.',
            default: 'Yes',
            allowedValues: ['Yes', 'No']
        });

        const testEndOfMonth = new CfnParameter(this, 'TestEndOfMonth', {
            type: 'String',
            description: 'Overrides date and forces the solution to run as if it is the end of the month.',
            default: 'No',
            allowedValues: ['Yes', 'No']
        });

        const regions = new CfnParameter(this, 'Regions', {
            type: 'String',
            description: 'The list of AWS regions which the solution will scan. Example - us-east-1, us-west-2. Leave blank to scan all regions.',
            default: ''
        });

        const terminateUnusedWorkspaces = new CfnParameter(this, 'TerminateUnusedWorkspaces', {
            type: 'String',
            description: 'Select "Yes" to terminate Workspaces not used for a month.',
            default: 'No',
            allowedValues: ['Yes', 'No', 'Dry Run']
        });

        const valueLimit = new CfnParameter(this, 'ValueLimit', {
            type: 'Number',
            description: 'The number of hours a Value instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 81
        });

        const standardLimit = new CfnParameter(this, 'StandardLimit', {
            type: 'Number',
            description: 'The number of hours a Standard instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 85
        });

        const performanceLimit = new CfnParameter(this, 'PerformanceLimit', {
            type: 'Number',
            description: 'The number of hours a Performance instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 83
        });

        const powerLimit = new CfnParameter(this, 'PowerLimit', {
            type: 'Number',
            description: 'The number of hours a Power instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 83
        });

        const powerProLimit = new CfnParameter(this, 'PowerProLimit', {
            type: 'Number',
            description: 'The number of hours a Power Pro instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 80
        });

        const graphicsLimit = new CfnParameter(this, 'GraphicsLimit', {
            type: 'Number',
            description: 'The number of hours a Graphics instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 217
        });

        const graphicsProLimit = new CfnParameter(this, 'GraphicsProLimit', {
            type: 'Number',
            description: 'The number of hours a Graphics Pro instance can run in a month before being converted to ALWAYS_ON. Default is 81.',
            default: 80
        });

        const organizationID = new CfnParameter(this, 'OrganizationID', {
            type: 'String',
            description: 'Organization ID to support multi account deployment. Leave blank for single account deployments.',
            allowedPattern: '^$|^o-[a-z0-9]{10,32}$',
            default: ''
        });

        const managementAccountId = new CfnParameter(this, 'ManagementAccountId', {
            type: 'String',
            description: 'Account ID for the management account of the Organization. Leave blank for single account deployments.',
            default: ''
        });

        const numberOfMonthsForTerminationCheck = new CfnParameter(this, 'NumberOfMonthsForTerminationCheck', {
            type: 'String',
            description: 'Provide the number of months to check for inactive period before termination. Default value is 1 month.',
            default: '1',
            allowedValues: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
        });


        this.templateOptions.metadata = {
            "AWS::CloudFormation::Interface": {
                ParameterGroups: [
                    {
                        Label: {default: "Select New or Existing VPC for AWS Fargate"},
                        Parameters: [createNewVPC.logicalId]
                    },
                    {
                        Label: {default: "Existing VPC Settings"},
                        Parameters: [existingSubnet1Id.logicalId, existingSubnet2Id.logicalId, existingSecurityGroupId.logicalId]
                    },
                    {
                        Label: {default: "New VPC Settings"},
                        Parameters: [vpcCIDR.logicalId, subnet1CIDR.logicalId, subnet2CIDR.logicalId, egressCIDR.logicalId]
                    },
                    {
                        Label: {default: "Testing Parameters"},
                        Parameters: [dryRun.logicalId, testEndOfMonth.logicalId, logLevel.logicalId]
                    },
                    {
                        Label: {default: "Pricing Parameters"},
                        Parameters: [valueLimit.logicalId, standardLimit.logicalId, performanceLimit.logicalId, graphicsLimit.logicalId, graphicsProLimit.logicalId, powerLimit.logicalId, powerProLimit.logicalId]
                    },
                    {
                        Label: {default: "List of AWS Regions"},
                        Parameters: [regions.logicalId]
                    },
                    {
                        Label: {default: "Terminate unused workspaces"},
                        Parameters: [terminateUnusedWorkspaces.logicalId, numberOfMonthsForTerminationCheck.logicalId]
                    },
                    {
                        Label: {default: "Multi account deployment"},
                        Parameters: [organizationID.logicalId, managementAccountId.logicalId]
                    }
                ],
                ParameterLabels: {
                    [vpcCIDR.logicalId]: {
                        default: "AWS Fargate VPC CIDR Block",
                    },
                    [subnet1CIDR.logicalId]: {
                        default: "AWS Fargate Subnet 1 CIDR Block",
                    },
                    [subnet2CIDR.logicalId]: {
                        default: "AWS Fargate Subnet 2 CIDR Block",
                    },
                    [egressCIDR.logicalId]: {
                        default: "AWS Fargate SecurityGroup CIDR Block",
                    },
                    [dryRun.logicalId]: {
                        default: "Launch in Dry Run Mode",
                    },
                    [testEndOfMonth.logicalId]: {
                        default: "Simulate End of Month Cleanup",
                    },
                    [logLevel.logicalId]: {
                        default: "Log Level",
                    },
                    [createNewVPC.logicalId]: {
                        default: "Create New VPC",
                    },
                    [existingSubnet1Id.logicalId]: {
                        default: "Subnet ID for first subnet",
                    },
                    [existingSubnet2Id.logicalId]: {
                        default: "Subnet ID for second subnet",
                    },
                    [existingSecurityGroupId.logicalId]: {
                        default: "Security group ID to launch ECS task",
                    },
                    [regions.logicalId]: {
                        default: "List of AWS Regions",
                    },
                    [terminateUnusedWorkspaces.logicalId]: {
                        default: "Terminate workspaces not used for a month",
                    },
                    [organizationID.logicalId]: {
                        default: "Organization ID for multi account deployment",
                    },
                    [managementAccountId.logicalId]: {
                        default: "Account ID of the Management Account for the Organization",
                    },
                    [numberOfMonthsForTerminationCheck.logicalId]: {
                        default: "Number of months for termination check"
                    }
                },
            },
        };


        const mappings = new cdk.CfnMapping(this, "Solution")
        mappings.setValue("Data", "ClusterName", 'cost-optimizer-cluster')
        mappings.setValue("Data", "TaskDefinitionName", 'wco-task')
        mappings.setValue("Data", "LogGroupName", '/ecs/wco-task')
        mappings.setValue("Data", "ID", props.solutionId)
        mappings.setValue("Data", "Version", props.solutionVersion)
        mappings.setValue("Data", "SendAnonymousUsageData", 'True')
        mappings.setValue("Data", "MetricsURL", 'https://metrics.awssolutionsbuilder.com/generic')
        mappings.setValue("Data", "AutoStopTimeoutHours", 1)
        mappings.setValue("Data", "Image", 'PUBLIC_ECR_REGISTRY/workspaces-cost-optimizer:PUBLIC_ECR_TAG')
        mappings.setValue("Data", "RoleName", 'Workspaces-Cost-Optimizer')
        mappings.setValue("Data", "RegisterLambdaFunctionName", 'Register-Spoke-Accounts')
        mappings.setValue("Data", "SpokeAccountWorkspacesRole", 'Workspaces-Admin-Spoke')
        mappings.setValue("Data", "TagKey", 'CloudFoundations:CostOptimizerForWorkspaces')
        mappings.setValue("Data", "AppRegistryApplicationName", 'workspaces-cost-optimizer')
        mappings.setValue("Data", "SolutionName", 'Cost Optimizer for Amazon Workspaces')


        const createNewVPCCondition = new cdk.CfnCondition(this, 'CreateNewVPCCondition', {
            expression: cdk.Fn.conditionEquals(createNewVPC.valueAsString, 'Yes'),
        });

        const useExistingVPCCondition = new cdk.CfnCondition(this, 'UseExistingVPCCondition', {
            expression: cdk.Fn.conditionEquals(createNewVPC.valueAsString, 'No'),
        });
        
        const organizationIdInputParameter = new cdk.CfnCondition(this, 'organizationIdInputParameter', {
            expression: cdk.Fn.conditionEquals(organizationID.valueAsString, ''),
        });

        const managementIdInputParameter = new cdk.CfnCondition(this, 'managementIdInputParameter', {
            expression: cdk.Fn.conditionEquals(managementAccountId.valueAsString, ''),
        });

        const managementAccountSetupCondition = new cdk.CfnCondition(this, 'ManagementAccountSetupCondition', {
            expression: cdk.Fn.conditionNot(managementIdInputParameter),
        });

        const organizationSetupCondition  = new cdk.CfnCondition(this, 'OrganizationSetupCondition', {
            expression: cdk.Fn.conditionNot(organizationIdInputParameter),
        });

        const multiAccountDeploymentCondition = new cdk.CfnCondition(this, 'MultiAccountDeploymentCondition', {
            expression: cdk.Fn.conditionAnd(organizationSetupCondition, managementAccountSetupCondition),
        });
        
        const createDynamoDBEndpointCondition = new cdk.CfnCondition(this, 'CreateDynamoDBEndpointCondition', {
            expression: cdk.Fn.conditionAnd(createNewVPCCondition, multiAccountDeploymentCondition),
        });
        
        const reportingBucket = new UsageReportBucketResources(this, 'UsageReportBucketResources')

        const spokeAccountTable = new Table(this, 'SpokeAccountTable', {
            pointInTimeRecovery: true,
            removalPolicy: cdk.RemovalPolicy.RETAIN,
            encryption: TableEncryption.AWS_MANAGED,
            billingMode: BillingMode.PAY_PER_REQUEST,
            partitionKey: {name: 'account_id', type: AttributeType.STRING},
            sortKey: {name: 'role_name', type: AttributeType.STRING}
        })

        overrideLogicalId(spokeAccountTable, 'SpokeAccountTable')
        setCondition(spokeAccountTable, multiAccountDeploymentCondition)
        
        const costOptimizerVpcProps: VpcResourcesProps ={
            vpcCIDR: vpcCIDR.valueAsString,
            solutionTagKey: mappings.findInMap('Data','TagKey'),
            solutionTagValue: Aws.STACK_NAME,
            createNewVpcCondition: createNewVPCCondition,
            subnet1CIDR: subnet1CIDR.valueAsString,
            subnet2CIDR: subnet2CIDR.valueAsString,
            egressCIDR: egressCIDR.valueAsString,
            costOptimizerBucketName: reportingBucket.reportingBucket.bucketName,
            spokeAccountTableName: spokeAccountTable.tableName,
            createDynamoDBEndpointCondition: createDynamoDBEndpointCondition,
            ecsTaskRoleName: mappings.findInMap('Data','RoleName')
        }

        const costOptimizerVpc = new VpcResources(this, 'CostOptimizerVpc', costOptimizerVpcProps)

        Aspects.of(costOptimizerVpc).add(new ConditionAspect(createNewVPCCondition))
        Aspects.of(costOptimizerVpc.dynamoDbEndpoint).add(new ConditionAspect(createDynamoDBEndpointCondition))
        

        const uuidResourcesProps: UUIDResourcesProps = {
            solutionId: props.solutionId,
            solutionName: props.solutionName,
            solutionVersion: props.solutionVersion,
            solutionBucketName: props.solutionBucketName,
            logLevel: logLevel.valueAsString,
            solutionDataKey: mappings.findInMap('Data', 'TagKey')
        }
        
        const uuidGenerator = new UUIDResources(this, 'UUIDGenerator', uuidResourcesProps)

        const ecsClusterProps: EcsClusterResourcesProps = {
            clusterName: mappings.findInMap('Data','ClusterName'),
            tagKey: mappings.findInMap('Data','TagKey'),
            costOptimizerBucketName: reportingBucket.reportingBucket.bucketName,
            spokeAccountTableName: spokeAccountTable.tableName,
            ecsTaskLogGroupName: mappings.findInMap('Data','LogGroupName'),
            ecsTaskRoleName: mappings.findInMap('Data','RoleName'),
            spokeAcountWorkspacesRoleName: mappings.findInMap('Data','SpokeAccountWorkspacesRole'),
            ecsTaskFamily: mappings.findInMap('Data','TaskDefinitionName'),
            containerImage: mappings.findInMap('Data','Image'),
            fargateVpcId: costOptimizerVpc.vpc.attrVpcId,
            logLevel: logLevel.valueAsString,
            dryRun: dryRun.valueAsString,
            testEndOfMonth: testEndOfMonth.valueAsString,
            sendAnonymousData: mappings.findInMap('Data','SendAnonymousUsageData'),
            solutionVersion: mappings.findInMap('Data','Version'),
            solutionId: mappings.findInMap('Data','ID'),
            uuid: uuidGenerator.uuid,
            valueLimit: valueLimit.valueAsString,
            standardLimit: standardLimit.valueAsString,
            performanceLimit: performanceLimit.valueAsString,
            powerLimit: powerLimit.valueAsString,
            powerProLimit: powerProLimit.valueAsString,
            graphicsLimit: graphicsLimit.valueAsString,
            graphicsProLimit: graphicsProLimit.valueAsString,
            metricsEndpoint: mappings.findInMap('Data','MetricsURL'),
            userAgentString: cdk.Fn.sub('AwsSolution/${SolutionID}/${Version}', {
                'SolutionID': mappings.findInMap('Data','ID'),
                'Version': mappings.findInMap('Data','Version')
            }),
            autoStopTimeoutHours: mappings.findInMap('Data','AutoStopTimeoutHours'),
            regions: regions.valueAsString,
            terminateUnusedWorkspaces: terminateUnusedWorkspaces.valueAsString,
            spokeAccountDynamoDBTableName: spokeAccountTable.tableName,
            multiAccountDeploymentCondition: multiAccountDeploymentCondition,
            createNewVpcConditionLogicalId: createNewVPCCondition.logicalId,
            existingVpcConditionLogicalId: useExistingVPCCondition.logicalId,
            intraVPCSecurityGroup: costOptimizerVpc.intraVPCSecurityGroup.attrGroupId,
            existingSecurityGroupId: existingSecurityGroupId.valueAsString,
            existingSubnetId1: existingSubnet1Id.valueAsString,
            existingSubnetId2: existingSubnet2Id.valueAsString,
            newSubnetId1: costOptimizerVpc.subnet1.attrSubnetId,
            newSubnetId2: costOptimizerVpc.subnet2.attrSubnetId,
            numberOfmonthsForTerminationCheck: numberOfMonthsForTerminationCheck.valueAsString
        }

        new EcsClusterResources(this, 'EcsClusterResources', ecsClusterProps)

        const registerSpokeAccountProps: RegisterSpokeAccountResourcesProps = {
            solutionId: props.solutionId,
            solutionName: props.solutionName,
            solutionVersion: props.solutionVersion,
            solutionBucketName: props.solutionBucketName,
            spokeAccountTableName: spokeAccountTable.tableName,
            logLevel: logLevel.valueAsString,
            organizationId: organizationID.valueAsString,
            registerSpokeAccountLambdaFunctionName: mappings.findInMap('Data','RegisterLambdaFunctionName')
        }
        
        const registerSpokeAccountFunction = new RegisterSpokeAccountResources(this, 'RegisterSpokeAccount', registerSpokeAccountProps)
        Aspects.of(registerSpokeAccountFunction).add(new ConditionAspect(multiAccountDeploymentCondition))

        const appRegistryHubProps: AppRegistryHubResourcesProps = {
            solutionDomain: 'CloudFoundations',
            solutionId: props.solutionId,
            solutionName: props.solutionName,
            solutionVersion: props.solutionVersion,
            applicationType: 'AWS-Solutions',
            appRegistryApplicationName: mappings.findInMap('Data', 'AppRegistryApplicationName'),
            managementAccountId: managementAccountId.valueAsString,
            orgId: organizationID.valueAsString,
            multiAccountDeploymentCondition: multiAccountDeploymentCondition
        }

        new AppRegistryHubResources(this, 'AppRegistryHubResources', appRegistryHubProps)


        // Outputs
        new CfnOutput(this, 'BucketNameOutput', {
            description: 'The name of the bucket created by the solution.',
            value: reportingBucket.reportingBucket.bucketName
        }).overrideLogicalId('BucketName');

        new CfnOutput(this, 'UUID', {
            description: 'Unique identifier for this solution',
            value: uuidGenerator.uuid
        }).overrideLogicalId('UUID');

        new CfnOutput(this, 'LogLevelOutput', {
            value: logLevel.valueAsString,
            exportName: 'LogLevel'
        }).overrideLogicalId('LogLevel');

        new CfnOutput(this, 'DryRunOutput', {
            value: dryRun.valueAsString,
            exportName: 'DryRun'
        }).overrideLogicalId('DryRun');

        new CfnOutput(this, 'SendAnonymousDataOutput', {
            value: mappings.findInMap('Data','SendAnonymousUsageData'),
            exportName: 'SendAnonymousData'
        }).overrideLogicalId('SendAnonymousData');

        new CfnOutput(this, 'SolutionIDOutput', {
            value: mappings.findInMap('Data','ID'),
            exportName: 'SolutionID'
        }).overrideLogicalId('SolutionID');

        new CfnOutput(this, 'SolutionVersionOutput', {
            value: mappings.findInMap('Data','Version'),
            exportName: 'SolutionVersion'
        }).overrideLogicalId('SolutionVersion');

        new CfnOutput(this, 'TestEndOfMonthOutput', {
            value: testEndOfMonth.valueAsString,
            exportName: 'TestEndOfMonth'
        }).overrideLogicalId('TestEndOfMonth');

        new CfnOutput(this, 'ValueLimitOutput', {
            value: valueLimit.valueAsString,
            exportName: 'ValueLimit'
        }).overrideLogicalId('ValueLimit');

        new CfnOutput(this, 'StandardLimitOutput', {
            value: standardLimit.valueAsString,
            exportName: 'StandardLimit'
        }).overrideLogicalId('StandardLimit');

        new CfnOutput(this, 'PerformanceLimitOutput', {
            value: performanceLimit.valueAsString,
            exportName: 'PerformanceLimit'
        }).overrideLogicalId('PerformanceLimit');

        new CfnOutput(this, 'PowerLimitOutput', {
            value: powerLimit.valueAsString,
            exportName: 'PowerLimit'
        }).overrideLogicalId('PowerLimit');

        new CfnOutput(this, 'PowerProLimitOutput', {
            value: powerProLimit.valueAsString,
            exportName: 'PowerProLimit'
        }).overrideLogicalId('PowerProLimit');

        new CfnOutput(this, 'GraphicsLimitOutput', {
            value: graphicsLimit.valueAsString,
            exportName: 'GraphicsLimit'
        }).overrideLogicalId('GraphicsLimit');

        new CfnOutput(this, 'GraphicsProLimitOutput', {
            value: graphicsProLimit.valueAsString,
            exportName: 'GraphicsProLimit'
        }).overrideLogicalId('GraphicsProLimit');
        
    }
}
