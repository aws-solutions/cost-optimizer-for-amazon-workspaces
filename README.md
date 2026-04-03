*[🚀 Solution Landing Page](https://aws.amazon.com/solutions/implementations/cost-optimizer-for-amazon-workspaces/)** | **[🚧 Feature request](https://github.com/aws-solutions/cost-optimizer-for-amazon-workspaces/issues/new?assignees=&labels=feature-request%2C+enhancement&template=feature_request.md&title=)** | **[🐛 Bug Report](https://github.com/aws-solutions/cost-optimizer-for-amazon-workspaces/issues/new?assignees=&labels=bug%2C+triage&template=bug_report.md&title=)**

Note: If you want to use the solution without building from source, navigate to Solution Landing Page.

## Table of contents

- [Solution Overview](#solution-overview)
- [Architecture Diagram](#architecture-diagram)
- [Getting Started](#getting-started)
- [Customizing the Solution](#customizing-the-solution)
  - [Build](#build)
  - [Unit Test](#unit-test)
  - [Deploy](#deploy)
- [File Structure](#file-structure)
- [Collection of operational metrics](#collection-of-operational-metrics)
- [License](#license)

<a name="solution-overview"></a>
# Solution Overview
Amazon WorkSpaces, a fully managed, secure virtual desktop computing service on the AWS Cloud, eliminates the need for customers to procure, deploy, and manage complex virtual desktop environments. Amazon WorkSpaces offers the flexibility to pay hourly or monthly without any up-front commitment.

To help customers with unpredictable WorkSpace usage patterns monitor their Amazon WorkSpaces usage and optimize costs, AWS offers the Amazon WorkSpaces Cost Optimizer, a solution that analyzes all of your WorkSpace usage data and automatically converts the WorkSpace to the most cost-effective billing option (hourly or monthly) depending on the user's individual usage. This solution is easy to deploy and gives a choice to use either [AWS Cloudformation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) or [AWS CDKv2](https://docs.aws.amazon.com/cdk/v2/guide/home.html) to automatically provision and configure the necessary AWS services.

<a name="architecture-diagram"></a>
# Architecture Diagram
![alt Architecture Diagram](source/architecture_diagram.png)

<a name="getting-started"></a>
# Getting Started
For deployment flexability and backwards compatability, there are two ways of deploying this solution: via Cloudformation and via CDK. The simplest way to get started is via AWS Cloudformation's WebUI. The programatic way via CDK allows customization of input parameters. Feel free to choose either ways of deployment to fit your needs.

Deploy via the [CloudFormation Template for WorkSpaces Cost Optimizer](https://solutions-reference.s3.amazonaws.com/cost-optimizer-for-amazon-workspaces/latest/cost-optimizer-for-amazon-workspaces.template)

Deploy via [CDKv2](https://docs.aws.amazon.com/cdk/v2/guide/home.html) with [npm](https://docs.npmjs.com/):


[Preconfigure aws profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)
```
git clone git@github.com:aws-solutions/cost-optimizer-for-amazon-workspaces.git


cd source

npm install

# set your preconfigured aws profile in ~/.aws/credentials
export AWS_PROFILE=""
export DIST_OUTPUT_BUCKET=solutions

npm run bootstrap -- --profile ${AWS_PROFILE}

npm run deploy -- --profile ${AWS_PROFILE} --parameters CreateNewVPC=Yes
```


For the full solution overview visit [WorkSpaces Cost Optimizer on AWS](https://aws.amazon.com/solutions/implementations/cost-optimizer-for-amazon-workspaces/)

<a name="aws-solutions-constructs"></a><a name="customizing-the-solution"></a>
# Customizing the Solution

<a name="build"></a>
## Build

Clone the repository

```
git clone git@github.com:aws-solutions/cost-optimizer-for-amazon-workspaces.git
```

Create a distribution S3 bucket with the format `MY-BUCKET-<aws_region>`. The solution's cdk will expect the
source code to be located in this bucket. `<aws_region>` is where you are testing the customized solution.

Note: When you create a bucket, a randomized value unique to your environment is recommended for the bucket name.
As a best practice, enable the server side encryption and also block public access to the bucket.

```
export TEMPLATE_OUTPUT_BUCKET=<YOUR_TEMPLATE_BUCKET_NAME>
export DIST_OUTPUT_BUCKET=<YOUR_DIST_BUCKET_NAME>
export SOLUTION_NAME="cost-optimizer-for-amazon-workspaces"
export VERSION=<VERSION>
## NOTE THAT the region is appended to the DIST_BUCKET_NAME (DIST_BUCKET_NAME-REGION) when deployed, so creating a bucket with only Bucket_Name will not work.
```

Change the working directory to the deployment folder.

```
cd deployment
```

Run the build script.

```
chmod +x ./build-s3-dist.sh && ./build-s3-dist.sh $TEMPLATE_OUTPUT_BUCKET $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION
```

Upload the artifacts.

```
aws s3 cp ./dist/ s3://$BUCKET_NAME-[region]/cost-optimizer-for-amazon-workspaces/$VERSION --recursive
```

You should now have everything in place to run cdk or CloudFormation template(either from your bucket or from `./deployment/dist/`).

<a name="unit-test"></a>
## Unit Test
```
chmod +x "./run-unit-tests.sh" && "./run-unit-tests.sh"
```

<a name="deploy"></a>
## Deploy
Two methods of deploying: CDK or CloudFormation Template
1. CDK: Run as seen in getting started section and then deploy spoke in a separate aws account
```
AWS_PROFILE=""
AWS_PROFILE_SPOKE=""

# Note: running bootstrap is only required once, not needed for every subsequent deployment.
npm run bootstrap -- --profile ${AWS_PROFILE}

npm run deploy -- --profile ${AWS_PROFILE} --parameters CreateNewVPC=Yes

HUB_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE_SPOKE --query Account --output text)

npm run bootstrap -- --profile ${AWS_PROFILE_SPOKE} --parameter HubAccountId=$HUB_ACCOUNT_ID

npm run deploySpoke -- --profile ${AWS_PROFILE_SPOKE} --parameters HubAccountId=${HUB_ACCOUNT_ID}

```

2. Cloudformation: For backwards compatibility, generate CloudFormation templates into source/cdk.out/ directory. Get the link of the cost-optimizer-for-amazon-workspaces.template loaded to your Amazon S3 bucket. Deploy the Workspaces Cost Optimizer solution to your account by launching a new AWS CloudFormation stack using the link of the cost-optimizer-for-amazon-workspaces.template.
:
```
npm run synth

#  source/cdk.out/{cost-optimizer-for-amazon-workspaces.template.json, cost-optimizer-for-amazon-workspaces-spoke.template.json}
```



<a name="file-structure"></a>
# File structure

<pre>
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE.txt
├── NOTICE.txt
├── README.md
├── SECURITY.md
├── buildspec.yml
├── deployment
│   ├── build-open-source-dist.sh
│   ├── build-s3-dist.sh
│   ├── run-unit-tests.sh
│   └── upload-s3-dist.sh
└── source
    ├── Dockerfile
    ├── bin
    │   └── cost-optimizer-for-amazon-workspaces-solution.ts
    ├── cdk.json
    ├── lambda
    │   ├── account_registration_provider
    │   │   ├── __init__.py
    │   │   ├── __tests__
    │   │   │   ├── __init__.py
    │   │   │   ├── conftest.py
    │   │   │   └── test_account_registration_provider.py
    │   │   └── account_registration_provider.py
    │   ├── register_spoke_lambda
    │   │   ├── __init__.py
    │   │   ├── __tests__
    │   │   │   ├── __init__.py
    │   │   │   ├── conftest.py
    │   │   │   ├── test_dynamodb.py
    │   │   │   ├── test_register_spoke_accounts.py
    │   │   │   └── test_request_event.py
    │   │   ├── dynamodb_table.py
    │   │   ├── register_spoke_accounts.py
    │   │   └── request_event.py
    │   ├── utils
    │   │   ├── __tests__
    │   │   │   ├── __init__.py
    │   │   │   ├── conftest.py
    │   │   │   └── test_cfnresponse.py
    │   │   └── cfnresponse.py
    │   └── uuid_generator
    │       ├── __init__.py
    │       ├── __tests__
    │       │   ├── __init__.py
    │       │   ├── conftest.py
    │       │   └── test_uuid_generator.py
    │       └── uuid_generator.py
    ├── lib
    │   ├── cdk-helper
    │   │   ├── add-cfn-nag-suppression.ts
    │   │   ├── condition-aspect.ts
    │   │   ├── override-logical-id.ts
    │   │   └── set-condition.ts
    │   ├── components
    │   │   ├── dashboard-resources.ts
    │   │   ├── ecs-cluster-resources.ts
    │   │   ├── register-spoke-account-resources.ts
    │   │   ├── usage-report-bucket-resources.ts
    │   │   ├── uuid-resources.ts
    │   │   └── vpc-resources.ts
    │   ├── cost-optimizer-for-amazon-workspaces-hub-stack.ts
    │   └── cost-optimizer-for-amazon-workspaces-spoke-stack.ts
    ├── package.json
    ├── package-lock.json
    ├── poetry.lock
    ├── pyproject.toml
    ├── tsconfig.json
    └── workspaces_app
        ├── main.py
        ├── test_workspaces_app.py
        └── workspaces_app
            ├── __init__.py
            ├── __tests__
            │   ├── __init__.py
            │   ├── conftest.py
            │   ├── test_account_registry.py
            │   ├── test_directory_reader.py
            │   ├── test_metrics_helper.py
            │   ├── test_user_session.py
            │   ├── test_workspace_record.py
            │   └── test_workspaces_helper.py
            ├── account_registry.py
            ├── directory_reader.py
            ├── metrics_helper.py
            ├── user_session.py
            ├── workspace_record.py
            ├── workspaces_helper.py
            └── utils
                ├── __init__.py
                ├── __tests__
                │   ├── __init__.py
                │   ├── conftest.py
                │   ├── test_dashboard_metrics.py
                │   ├── test_date_utils.py
                │   ├── test_s3_utils.py
                │   ├── test_timer.py
                │   ├── test_usage_table_dao.py
                │   └── test_user_session_dao.py
                ├── dashboard_metrics.py
                ├── date_utils.py
                ├── decimal_encoder.py
                ├── s3_utils.py
                ├── solution_metrics.py
                ├── timer.py
                ├── usage_table_dao.py
                ├── user_session_dao.py
                └── workspace_utils.py
</pre>


################################################

<a name="collection-of-operational-metrics"></a>
# Collection of operational metrics

This solution collects anonymized operational metrics to help AWS improve the
quality of features of the solution. For more information, including how to disable
this capability, please see the
[Implementation Guide](https://docs.aws.amazon.com/solutions/latest/cost-optimizer-for-workspaces/anonymized-data-collection.html)

<a name="license"></a>
# License

See license
[here](https://github.com/aws-solutions/cost-optimizer-for-amazon-workspaces/blob/main/LICENSE.txt).
