# WorkSpaces Cost Optimizer
Amazon WorkSpaces, a fully managed, secure virtual desktop computing service on the AWS Cloud, eliminates the need for customers to procure, deploy, and manage complex virtual desktop environments. Amazon WorkSpaces offers the flexibility to pay hourly or monthly without any up-front commitment.

To help customers with unpredictable WorkSpace usage patterns monitor their Amazon WorkSpaces usage and optimize costs, AWS offers the Amazon WorkSpaces Cost Optimizer, a solution that analyzes all of your WorkSpace usage data and automatically converts the WorkSpace to the most cost-effective billing option (hourly or monthly) depending on the user's individual usage. This solution is easy to deploy and uses AWS CloudFormation to automatically provision and configure the necessary AWS services.

## Getting Started
Deploy the [WorkSpaces Cost Optimizer CloudFormation Template](https://s3.amazonaws.com/solutions-reference/workspaces-cost-optimizer/latest/workspaces-cost-optimizer.template)

For the full solution overview visit [WorkSpaces Cost Optimizer on AWS](https://aws.amazon.com/answers/account-management/workspaces-cost-optimizer)

## Building from Source
Clone the repository

```
git clone git@github.com:awslabs/workspaces-cost-optimizer.git
```

Set the destination bucket name- this bucket should be in the region you're deploying the solution to.

```
export TEMPLATE_BUCKET_NAME=<YOUR_TEMPLATE_BUCKET_NAME>
export DIST_BUCKET_NAME=<YOUR_DIST_BUCKET_NAME>
export SOLUTION_NAME="workspaces-cost-optimizer"
export VERSION=<VERSION>
## NOTE THAT the region is appended to the DIST_BUCKET_NAME (DIST_BUCKET_NAME-REGION) when deployed, so creating a bucket with only Bucket_Name will not work.
```

Run the build script.

```
chmod +x ./build-s3-dist.sh && ./build-s3-dist.sh $TEMPLATE_OUTPUT_BUCKET $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION
```

Upload the artifacts.

```
aws s3 cp ./dist/ s3://$BUCKET_NAME-[region]/workspaces-cost-optimizer/$VERSION --recursive
```

You should now have everything in place to run the CloudFormation template (either from your bucket or from `./deployment/dist/`).

## Running Unit Tests
```
chmod +x "./run-unit-tests.sh" && "./run-unit-tests.sh"
```

***

-------------
## Optimization Engine

- source/engine/wco.py - depends on source/engine/lib/directory_reader.py
- source/engine/lib/directory_reader.py depends on workspaces_helper
- source/engine/lib/workspaces_helper.py depends on metrics_helper
- source/engine/lib/metrics_helper.py

## Helpers

- source/helpers/create-task.py

***

Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
