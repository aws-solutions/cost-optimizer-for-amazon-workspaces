# WorkSpaces Cost Optimizer
Amazon WorkSpaces, a fully managed, secure virtual desktop computing service on the
AWS Cloud, eliminates the need for customers to procure, deploy, and manage complex
virtual desktop environments. Amazon WorkSpaces provides a complete cloud-based
virtual desktop service, including compute, persistent storage, and applications.

For the full solution overview visit [WorkSpaces Cost Optimizer on AWS](https://aws.amazon.com/answers/account-management/workspaces-cost-optimizer)

## Build/Deploy
* Make a copy of the configuration file located at `config/config.js.example` and replace the values as appropriate
* Run `npm install` at the package root
* Run `gulp build` to zip Lambda function
* Run `gulp upload` to upload Lambda assets to S3
* If needed, change the S3 Bucket/Key for the Lambda functions in the CloudFormation Template to match new S3 location.

## CloudFormation Template
- cform/workspaces-cost-optimizer.template

## Solution Code
- src/child.py
- src/parent.py

***

Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.