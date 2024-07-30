// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { Construct } from "constructs";
import * as cdk from "aws-cdk-lib";
import { Tags, CfnCondition, aws_logs } from "aws-cdk-lib";
import {
  DefaultInstanceTenancy,
  CfnInternetGateway,
  CfnVPC,
  CfnSecurityGroup,
  CfnSubnet,
  CfnRouteTable,
  CfnVPCGatewayAttachment,
  CfnSecurityGroupEgress,
  CfnSubnetRouteTableAssociation,
  CfnRoute,
  CfnVPCEndpoint,
  CfnNatGateway,
  CfnEIP,
} from "aws-cdk-lib/aws-ec2";
import { Policy, Role, PolicyDocument, PolicyStatement, ServicePrincipal, AnyPrincipal } from "aws-cdk-lib/aws-iam";
import setCondition from "../cdk-helper/set-condition";
import overrideLogicalId from "../cdk-helper/override-logical-id";
import { addCfnNagSuppression } from "../cdk-helper/add-cfn-nag-suppression";

export interface VpcResourcesProps extends cdk.StackProps {
  vpcCIDR: string;
  solutionTagKey: string;
  solutionTagValue: string;
  createNewVpcCondition: CfnCondition;
  publicSubnetCIDR: string;
  privateSubnet1CIDR: string;
  privateSubnet2CIDR: string;
  egressCIDR: string;
  costOptimizerBucketName: string;
  spokeAccountTableName: string;
  usageTable: string;
  userSessionTable: string;
  createDynamoDBEndpointCondition: CfnCondition;
  ecsTaskRoleName: string;
}
export class VpcResources extends Construct {
  public readonly vpc: CfnVPC;
  public readonly internetGateway: CfnInternetGateway;
  public readonly publicSubnet: CfnSubnet;
  public readonly privateSubnet1: CfnSubnet;
  public readonly privateSubnet2: CfnSubnet;
  public readonly intraVPCSecurityGroup: CfnSecurityGroup;
  public readonly dynamoDbEndpoint: CfnVPCEndpoint;

  constructor(scope: Construct, id: string, props: VpcResourcesProps) {
    super(scope, id);

    const vpc = new CfnVPC(this, "VPC", {
      cidrBlock: props.vpcCIDR,
      instanceTenancy: DefaultInstanceTenancy.DEFAULT,
      enableDnsHostnames: true,
      enableDnsSupport: true,
    });
    Tags.of(vpc).add("Name", "cost-optimizer-vpc");
    Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue);
    overrideLogicalId(vpc, "VPC");

    const internetGateway = new CfnInternetGateway(this, "InternetGateway", {
      tags: [
        {
          key: "Name",
          value: "cost-optimizer-igw",
        },
        {
          key: props.solutionTagKey,
          value: props.solutionTagValue,
        },
      ],
    });
    overrideLogicalId(internetGateway, "InternetGateway");

    // Transitioning from two public to one public and two private subnets.
    // The old public subnet used to have "Subnet1" as its logical ID
    // Reusing the logical ID "Subnet1" for the new public subnet to avoid conflicts during customer updates

    const publicSubnet = new CfnSubnet(this, "PublicSubnet", {
      cidrBlock: props.publicSubnetCIDR,
      vpcId: vpc.ref,
      availabilityZone: cdk.Stack.of(this).availabilityZones[0],
    });
    overrideLogicalId(publicSubnet, "Subnet1");
    Tags.of(publicSubnet).add("Name", "cost-optimizer-vpc-public-subnet");
    Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue);

    const privateSubnet1 = new CfnSubnet(this, "PrivateSubnet1", {
      cidrBlock: props.privateSubnet1CIDR,
      vpcId: vpc.ref,
      availabilityZone: cdk.Stack.of(this).availabilityZones[0],
    });
    overrideLogicalId(privateSubnet1, "PrivateSubnet1");
    Tags.of(privateSubnet1).add("Name", "cost-optimizer-vpc-private-subnet-1");
    Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue);

    const privateSubnet2 = new CfnSubnet(this, "PrivateSubnet2", {
      cidrBlock: props.privateSubnet2CIDR,
      vpcId: vpc.ref,
      availabilityZone: cdk.Stack.of(this).availabilityZones[1],
    });
    overrideLogicalId(privateSubnet2, "PrivateSubnet2");
    Tags.of(privateSubnet2).add("Name", "cost-optimizer-vpc-private-subnet-2");
    Tags.of(vpc).add(props.solutionTagKey, props.solutionTagValue);

    const intraVPCSecurityGroup = new CfnSecurityGroup(this, "IntraVPCSecurityGroup", {
      groupDescription: "Security group that allows inbound from the VPC and outbound to the Internet",
      vpcId: vpc.ref,
    });
    overrideLogicalId(intraVPCSecurityGroup, "IntraVPCSecurityGroup");
    addCfnNagSuppression(intraVPCSecurityGroup, {
      id: "W36",
      reason: "flagged as not having a Description, property is GroupDescription not Description",
    });
    addCfnNagSuppression(intraVPCSecurityGroup, {
      id: "W40",
      reason: "IpProtocol set to -1 (any) as ports are not known prior to running tests",
    });
    const intraVPCSGMetadata = intraVPCSecurityGroup.cfnOptions?.metadata;
    if (intraVPCSGMetadata) {
      intraVPCSGMetadata.guard = {
        SuppressedRules: ["SECURITY_GROUP_MISSING_EGRESS_RULE"],
      };
    }

    const publicRouteTable = new CfnRouteTable(this, "PublicRouteTable", {
      vpcId: vpc.ref,
    });
    overrideLogicalId(publicRouteTable, "PublicRouteTable");

    const mainRoutePrivateTable = new CfnRouteTable(this, "MainRoutePrivateTable", {
      vpcId: vpc.ref,
    });
    overrideLogicalId(mainRoutePrivateTable, "MainRoutePrivateTable");

    const internetGatewayAttachment = new CfnVPCGatewayAttachment(this, "InternetGatewayAttachment", {
      internetGatewayId: internetGateway.ref,
      vpcId: vpc.ref,
    });
    overrideLogicalId(internetGatewayAttachment, "InternetGatewayAttachment");

    const natGateway = new CfnNatGateway(this, "NatGateway", {
      allocationId: new CfnEIP(this, "NatGatewayEIP", {
        domain: "vpc",
      }).attrAllocationId,
      subnetId: publicSubnet.ref,
    });
    overrideLogicalId(natGateway, "NatGateway");

    const securityGroupEgress = new CfnSecurityGroupEgress(this, "SecurityGroupEgress", {
      groupId: intraVPCSecurityGroup.attrGroupId,
      ipProtocol: "-1",
      cidrIp: props.egressCIDR,
      description: "allow egress from cidr",
    });
    overrideLogicalId(securityGroupEgress, "SecurityGroupEgress");

    const publicRouteToInternet = new CfnRoute(this, "PublicRouteToInternet", {
      destinationCidrBlock: "0.0.0.0/0",
      routeTableId: publicRouteTable.ref,
      gatewayId: internetGateway.ref,
    });
    publicRouteToInternet.addDependency(internetGatewayAttachment);
    overrideLogicalId(publicRouteToInternet, "PublicRouteToInternet");

    const privateRouteToInternet = new CfnRoute(this, "PrivateRouteToInternet", {
      destinationCidrBlock: "0.0.0.0/0",
      routeTableId: mainRoutePrivateTable.ref,
      natGatewayId: natGateway.ref,
    });
    overrideLogicalId(privateRouteToInternet, "PrivateRouteToInternet");

    const publicSubnetRouteTableAssociation = new CfnSubnetRouteTableAssociation(
      this,
      "PublicSubnetRouteTableAssociation",
      {
        routeTableId: publicRouteTable.ref,
        subnetId: publicSubnet.attrSubnetId,
      },
    );
    overrideLogicalId(publicSubnetRouteTableAssociation, "PublicSubnetRouteTableAssociation");

    const privateSubnet1RouteTableAssociation = new CfnSubnetRouteTableAssociation(
      this,
      "PrivateSubnet1RouteTableAssociation",
      {
        routeTableId: mainRoutePrivateTable.ref,
        subnetId: privateSubnet1.attrSubnetId,
      },
    );
    overrideLogicalId(privateSubnet1RouteTableAssociation, "PrivateSubnet1RouteTableAssociation");

    const privateSubnet2RouteTableAssociation = new CfnSubnetRouteTableAssociation(
      this,
      "PrivateSubnet2RouteTableAssociation",
      {
        routeTableId: mainRoutePrivateTable.ref,
        subnetId: privateSubnet2.attrSubnetId,
      },
    );
    overrideLogicalId(privateSubnet2RouteTableAssociation, "PrivateSubnet2RouteTableAssociation");

    const accountCondition = {
      StringEquals: {
        "aws:PrincipalArn": [
          `arn:${cdk.Aws.PARTITION}:iam::${cdk.Aws.ACCOUNT_ID}:role/${props.ecsTaskRoleName}-${cdk.Aws.REGION}`,
        ],
      },
    };

    const s3EndPointPolicyDocument = new PolicyDocument({
      statements: [
        new PolicyStatement({
          actions: ["s3:PutObject", "s3:GetObject"],
          principals: [new AnyPrincipal()],
          resources: [
            cdk.Arn.format(
              {
                service: "s3",
                resource: `${props.costOptimizerBucketName}`,
                resourceName: "*",
                partition: cdk.Aws.PARTITION,
                region: "", // S3 ARNs do not use a region
                account: "",
              },
              cdk.Stack.of(this),
            ),
          ],

          conditions: {
            StringEquals: {
              ...accountCondition.StringEquals,
              "aws:SecureTransport": "true",
            },
          },
        }),
        new PolicyStatement({
          actions: ["s3:ListBucket"],
          principals: [new AnyPrincipal()],
          resources: [`arn:${cdk.Aws.PARTITION}:s3:::${props.costOptimizerBucketName}`],
          conditions: accountCondition,
        }),
      ],
    });

    const s3GatewayEndpoint = new CfnVPCEndpoint(this, "S3GatewayEndpoint", {
      routeTableIds: [mainRoutePrivateTable.ref],
      vpcId: vpc.ref,
      serviceName: `com.amazonaws.${cdk.Aws.REGION}.s3`,
      policyDocument: s3EndPointPolicyDocument,
    });
    overrideLogicalId(s3GatewayEndpoint, "S3GatewayEndpoint");

    const dynamoDBEndPointPolicyDocument = new PolicyDocument({
      statements: [
        new PolicyStatement({
          actions: ["dynamodb:Scan"],
          principals: [new AnyPrincipal()],
          resources: [
            cdk.Arn.format(
              {
                service: "dynamodb",
                resource: "table",
                resourceName: props.spokeAccountTableName,
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
          conditions: {
            StringEquals: {
              ...accountCondition.StringEquals,
              "aws:SecureTransport": "true",
            },
          },
        }),
        new PolicyStatement({
          actions: ["dynamodb:PutItem", "dynamodb:GetItem"],
          principals: [new AnyPrincipal()],
          resources: [
            cdk.Arn.format(
              {
                service: "dynamodb",
                resource: "table",
                resourceName: props.usageTable,
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
          conditions: {
            StringEquals: {
              ...accountCondition.StringEquals,
              "aws:SecureTransport": "true",
            },
          },
        }),
        new PolicyStatement({
          actions: ["dynamodb:BatchWriteItem"],
          principals: [new AnyPrincipal()],
          resources: [
            cdk.Arn.format(
              {
                service: "dynamodb",
                resource: "table",
                resourceName: props.userSessionTable,
                partition: cdk.Aws.PARTITION,
                region: cdk.Aws.REGION,
                account: cdk.Aws.ACCOUNT_ID,
              },
              cdk.Stack.of(this),
            ),
          ],
          conditions: {
            StringEquals: {
              ...accountCondition.StringEquals,
              "aws:SecureTransport": "true",
            },
          },
        }),
      ],
    });

    const dynamodbGatewayEndpoint = new CfnVPCEndpoint(this, "DynamoDBGatewayEndpoint", {
      routeTableIds: [mainRoutePrivateTable.ref],
      vpcId: vpc.ref,
      serviceName: `com.amazonaws.${cdk.Aws.REGION}.dynamodb`,
      policyDocument: dynamoDBEndPointPolicyDocument,
    });
    setCondition(dynamodbGatewayEndpoint, props.createDynamoDBEndpointCondition);
    overrideLogicalId(dynamodbGatewayEndpoint, "DynamoDBGatewayEndpoint");

    const flowLogGroup = new aws_logs.LogGroup(this, "FlowLogGroup", {});
    overrideLogicalId(flowLogGroup, "FlowLogGroup");
    addCfnNagSuppression(flowLogGroup, {
      id: "W84",
      reason: "CloudWatch logs are encrypted by the service.",
    });
    addCfnNagSuppression(flowLogGroup, {
      id: "W86",
      reason: "CloudWatch logs are set to never expire.",
    });

    const flowLogRole = new Role(this, "FlowLogRole", {
      assumedBy: new ServicePrincipal("vpc-flow-logs.amazonaws.com"),
    });
    overrideLogicalId(flowLogRole, "FlowLogRole");

    const flowLog = new cdk.aws_ec2.CfnFlowLog(this, "FlowLog", {
      deliverLogsPermissionArn: flowLogRole.roleArn,
      logGroupName: flowLogGroup.logGroupName,
      resourceId: vpc.ref,
      resourceType: "VPC",
      trafficType: "ALL",
    });
    overrideLogicalId(flowLog, "FlowLog");

    const flowLogsPolicyDocument = new PolicyDocument({
      statements: [
        new PolicyStatement({
          actions: ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups", "logs:DescribeLogStreams"],
          resources: [flowLogGroup.logGroupArn],
        }),
      ],
    });

    const flowLogsPolicy = new Policy(this, "FlowLogsPolicy", {
      policyName: "flowlogs-policy",
      document: flowLogsPolicyDocument,
    });
    flowLogsPolicy.attachToRole(flowLogRole);
    overrideLogicalId(flowLogsPolicy, "FlowLogsPolicy");

    this.vpc = vpc;
    this.internetGateway = internetGateway;
    this.publicSubnet = publicSubnet;
    this.privateSubnet1 = privateSubnet1;
    this.privateSubnet2 = privateSubnet2;
    this.intraVPCSecurityGroup = intraVPCSecurityGroup;
    this.dynamoDbEndpoint = dynamodbGatewayEndpoint;
  }
}
