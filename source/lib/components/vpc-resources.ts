// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import {Construct} from "constructs";
import * as cdk from "aws-cdk-lib";
import {Tags, CfnCondition, aws_logs} from 'aws-cdk-lib';
import { 
    DefaultInstanceTenancy, CfnInternetGateway, CfnVPC, 
    CfnSecurityGroup, CfnSubnet, CfnRouteTable, CfnVPCGatewayAttachment, 
    CfnSecurityGroupEgress, CfnSubnetRouteTableAssociation, CfnRoute,
    CfnVPCEndpoint} from 'aws-cdk-lib/aws-ec2';
import { Policy, Role, PolicyDocument, PolicyStatement,
        ServicePrincipal, AnyPrincipal} from 'aws-cdk-lib/aws-iam'
import setCondition from "../cdk-helper/set-condition";
import overrideLogicalId from "../cdk-helper/override-logical-id";
import { addCfnNagSuppression } from "../cdk-helper/add-cfn-nag-suppression";

export interface VpcResourcesProps extends cdk.StackProps {
    vpcCIDR: string,
    solutionTagKey: string,
    solutionTagValue: string,
    createNewVpcCondition: CfnCondition,
    subnet1CIDR: string,
    subnet2CIDR: string,
    egressCIDR: string,
    costOptimizerBucketName: string,
    spokeAccountTableName: string,
    createDynamoDBEndpointCondition: CfnCondition,
    ecsTaskRoleName: string
};
export class VpcResources extends Construct {
    public readonly vpc: CfnVPC
    public readonly internetGateway: CfnInternetGateway
    public readonly subnet1: CfnSubnet
    public readonly subnet2: CfnSubnet
    public readonly intraVPCSecurityGroup: CfnSecurityGroup
    public readonly dynamoDbEndpoint: CfnVPCEndpoint

    constructor(scope: Construct, id: string, props:VpcResourcesProps) {
        super(scope, id);

        const vpc = new CfnVPC(this, 'VPC', {
            cidrBlock: props.vpcCIDR,
            instanceTenancy: DefaultInstanceTenancy.DEFAULT,
            enableDnsHostnames: true,
            enableDnsSupport: true
        })
        Tags.of(vpc).add('Name','cost-optimizer-vpc')
        Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue)
        overrideLogicalId(vpc, 'VPC')

        const internetGateway = new CfnInternetGateway(this, 'InternetGateway', {
            tags:[
                {
                    key: 'Name',
                    value: 'cost-optimizer-igw',
                },
                {
                    key: props.solutionTagKey,
                    value: props.solutionTagValue,
                }
            ]
        })
        overrideLogicalId(internetGateway, 'InternetGateway')

        const subnet1 = new CfnSubnet(this, 'Subnet1', {
            cidrBlock: props.subnet1CIDR,
            vpcId: vpc.ref,
            availabilityZone: cdk.Stack.of(this).availabilityZones[0]
        })
        overrideLogicalId(subnet1, 'Subnet1')
        Tags.of(subnet1).add('Name', 'cost-optimizer-vpc-subnet1')
        Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue)

        const subnet2 = new CfnSubnet(this, 'Subnet2', {
            cidrBlock: props.subnet2CIDR,
            vpcId: vpc.ref,
            availabilityZone: cdk.Stack.of(this).availabilityZones[1]
        })
        overrideLogicalId(subnet2, 'Subnet2')
        Tags.of(subnet2).add('Name', 'cost-optimizer-vpc-subnet2')
        Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue)

        const intraVPCSecurityGroup =  new CfnSecurityGroup(this, 'IntraVPCSecurityGroup', {
            groupDescription: 'Security group that allows inbound from the VPC and outbound to the Internet',
            vpcId: vpc.ref
        })
        overrideLogicalId(intraVPCSecurityGroup, 'IntraVPCSecurityGroup')
        addCfnNagSuppression(intraVPCSecurityGroup, {
            id: 'W36',
            reason: 'flagged as not having a Description, property is GroupDescription not Description'
        });
        addCfnNagSuppression(intraVPCSecurityGroup, {
            id: 'W40',
            reason: 'IpProtocol set to -1 (any) as ports are not known prior to running tests'
        });
        
        const mainRouteTable = new CfnRouteTable(this, 'MainRouteTable', {
            vpcId: vpc.ref,
        })
        overrideLogicalId(mainRouteTable, 'MainRouteTable')

        const internetGatewayAttachment = new CfnVPCGatewayAttachment(this, 'InternetGatewayAttachment', {
            internetGatewayId: internetGateway.ref,
            vpcId: vpc.ref,
        })
        overrideLogicalId(internetGatewayAttachment, 'InternetGatewayAttachment')
        
        const securityGroupEgress = new CfnSecurityGroupEgress(this, 'SecurityGroupEgress', {
            groupId: intraVPCSecurityGroup.attrGroupId,
            ipProtocol: '-1',
            cidrIp: props.egressCIDR
        })
        overrideLogicalId(securityGroupEgress, 'SecurityGroupEgress')
        
        const routeToInternet = new CfnRoute(this, 'RouteToInternet', {
            destinationCidrBlock: '0.0.0.0/0',
            routeTableId: mainRouteTable.ref,
            gatewayId: internetGateway.ref
        })
        routeToInternet.addDependency(internetGatewayAttachment)
        overrideLogicalId(routeToInternet, 'RouteToInternet')

        const subnet1RouteTableAssociation = new CfnSubnetRouteTableAssociation(this, 'Subnet1RouteTableAssociation', {
            routeTableId: mainRouteTable.ref,
            subnetId: subnet1.attrSubnetId
        })
        overrideLogicalId(subnet1RouteTableAssociation, 'Subnet1RouteTableAssociation')
        
        const subnet2RouteTableAssociation = new CfnSubnetRouteTableAssociation(this, 'Subnet2RouteTableAssociation', {
            routeTableId: mainRouteTable.ref,
            subnetId: subnet2.attrSubnetId
        })
        overrideLogicalId(subnet2RouteTableAssociation, 'Subnet2RouteTableAssociation')

        const accountCondition = {
            StringEquals: {
              'aws:PrincipalArn': [ 
                `arn:${cdk.Aws.PARTITION}:iam::${cdk.Aws.ACCOUNT_ID}:role/${props.ecsTaskRoleName}-${cdk.Aws.REGION}`
            ],
            },
          };

        const s3EndPointPolicyDocument = new PolicyDocument({
            statements: [new PolicyStatement({
                actions: [
                    's3:PutObject'
                ],
                principals: [new AnyPrincipal],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:s3:::${props.costOptimizerBucketName}/*`,
                ],
                conditions:accountCondition
            })],
        });
        
        const s3GatewayEndpoint = new CfnVPCEndpoint(this, 'S3GatewayEndpoint', {
            routeTableIds: [mainRouteTable.ref],
            vpcId: vpc.ref,
            serviceName: `com.amazonaws.${cdk.Aws.REGION}.s3`,            
            policyDocument: s3EndPointPolicyDocument
        })
        overrideLogicalId(s3GatewayEndpoint, 'S3GatewayEndpoint')

        const dynamoDBEndPointPolicyDocument = new PolicyDocument({
            statements: [new PolicyStatement({
                actions: [
                    'dynamodb:Scan'
                ],
                principals: [new AnyPrincipal],
                resources: [
                    `arn:${cdk.Aws.PARTITION}:dynamodb:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:table/${props.spokeAccountTableName}`
                ],
                conditions:accountCondition
            })],
        });

        const dynamodbGatewayEndpoint = new CfnVPCEndpoint(this, 'DynamoDBGatewayEndpoint', {
            routeTableIds: [mainRouteTable.ref],
            vpcId: vpc.ref,
            serviceName: `com.amazonaws.${cdk.Aws.REGION}.dynamodb`,            
            policyDocument: dynamoDBEndPointPolicyDocument
        })
        setCondition(dynamodbGatewayEndpoint, props.createDynamoDBEndpointCondition)
        overrideLogicalId(dynamodbGatewayEndpoint, 'DynamoDBGatewayEndpoint')

        const flowLogGroup = new aws_logs.LogGroup(this, 'FlowLogGroup', {})
        overrideLogicalId(flowLogGroup, 'FlowLogGroup')
        addCfnNagSuppression(flowLogGroup, {
            id: 'W84',
            reason: 'CloudWatch logs are encrypted by the service.'
        })
        addCfnNagSuppression(flowLogGroup, {
            id: 'W86',
            reason: 'CloudWatch logs are set to never expire.'
        })

        const flowLogRole = new Role(this, 'FlowLogRole', {
            assumedBy: new ServicePrincipal('vpc-flow-logs.amazonaws.com')
        })
        overrideLogicalId(flowLogRole, 'FlowLogRole')

        const flowLog = new cdk.aws_ec2.CfnFlowLog(this, 'FlowLog', {
            deliverLogsPermissionArn: flowLogRole.roleArn,
            logGroupName: flowLogGroup.logGroupName,
            resourceId: vpc.ref,
            resourceType: 'VPC',
            trafficType: 'ALL'
        })
        overrideLogicalId(flowLog, 'FlowLog')
        
        const flowLogsPolicyDocument = new PolicyDocument({
            statements: [new PolicyStatement({
                actions: [
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                    'logs:DescribeLogGroups',
                    'logs:DescribeLogStreams'
                ],
                resources: [ flowLogGroup.logGroupArn]
            })],
        });
        
        const flowLogsPolicy = new Policy(this, 'FlowLogsPolicy', {
            policyName: 'flowlogs-policy',
            document: flowLogsPolicyDocument
        })
        flowLogsPolicy.attachToRole(flowLogRole)
        overrideLogicalId(flowLogsPolicy, 'FlowLogsPolicy')

        this.vpc = vpc
        this.internetGateway = internetGateway
        this.subnet1 = subnet1
        this. subnet2 = subnet2
        this.intraVPCSecurityGroup = intraVPCSecurityGroup
        this.dynamoDbEndpoint = dynamodbGatewayEndpoint

    }
}
