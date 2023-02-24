**[🚀 Solution Landing Page](https://aws.amazon.com/solutions/implementations/amazon-workspaces-cost-optimizer/)** | **[🚧 Feature request](https://github.com/awslabs/<insert-solution-repo-name>/issues/new?assignees=&labels=feature-request%2C+enhancement&template=feature_request.md&title=)** | **[🐛 Bug Report](https://github.com/awslabs/<insert-solution-repo-name>/issues/new?assignees=&labels=bug%2C+triage&template=bug_report.md&title=)**

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

To help customers with unpredictable WorkSpace usage patterns monitor their Amazon WorkSpaces usage and optimize costs, AWS offers the Amazon WorkSpaces Cost Optimizer, a solution that analyzes all of your WorkSpace usage data and automatically converts the WorkSpace to the most cost-effective billing option (hourly or monthly) depending on the user's individual usage. This solution is easy to deploy and uses AWS CloudFormation to automatically provision and configure the necessary AWS services.

<a name="architecture-diagram"></a>
# Architecture Diagram
![alt Architecture Diagram](source/architecture_diagram.png)

<a name="getting-started"></a>
# Getting Started

Deploy the [WorkSpaces Cost Optimizer CloudFormation Template](https://s3.amazonaws.com/solutions-reference/workspaces-cost-optimizer/latest/workspaces-cost-optimizer.template)

For the full solution overview visit [WorkSpaces Cost Optimizer on AWS](https://aws.amazon.com/solutions/implementations/amazon-workspaces-cost-optimizer/)

<a name="aws-solutions-constructs"></a><a name="customizing-the-solution"></a>
# Customizing the Solution

<a name="build"></a>
## Build

Clone the repository

```
git clone git@github.com:awslabs/workspaces-cost-optimizer.git
```

Create a distribution S3 bucket with the format `MY-BUCKET-<aws_region>`. The solution's CloudFormation template will expect the 
source code to be located in this bucket. `<aws_region>` is where you are testing the customized solution.

Note: When you create a bucket, a randomized value unique to your environment is recommended for the bucket name. 
As a best practice, enable the server side encryption and also block public access to the bucket.

```
export TEMPLATE_OUTPUT_BUCKET=<YOUR_TEMPLATE_BUCKET_NAME>
export DIST_OUTPUT_BUCKET=<YOUR_DIST_BUCKET_NAME>
export SOLUTION_NAME="workspaces-cost-optimizer"
export VERSION=<VERSION>
## NOTE THAT the region is appended to the DIST_BUCKET_NAME (DIST_BUCKET_NAME-REGION) when deployed, so creating a bucket with only Bucket_Name will not work.
```

Change the working directory to the deployment folder

```
cd deployment
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

<a name="unit-test"></a>
## Unit Test
```
chmod +x "./run-unit-tests.sh" && "./run-unit-tests.sh"
```

<a name="deploy"></a>
## Deploy
Get the link of the `workspaces-cost-optimizer.template` loaded to your Amazon S3 bucket.

Deploy the Workspaces Cost Optimizer solution to your account by launching a new AWS CloudFormation stack using the link of the `workspaces-cost-optimizer.template`.

<a name="file-structure"></a>
# File structure

<pre>
|-deployment/
  |-build-s3-dist.sh
  |-run-unit-tests.sh
  |-workspaces-cost-optimizer.template
  |-workspaces-cost-optimizer-spoke.template
|-source/
  |-account_registration_provider/
    |__tests__/
      |__init__.py
      |-conftest.py
      |-test_account_registration_provider.py
    |__init__.py
    |-account_registration_provider.py
  |-docker/
    |-docker-build.sh
    |-docker-clean.sh
    |-docker-run.sh
  |-lib/
    |__tests__/
      |__init__.py
      |-conftest.py
      |-test_cfnresponse.py
    |-cfnresponse.py
  |-register_spoke_lambda/
    |__tests__/
      |__init__.py
      |-conftest.py
      |-test_dynamodb.py
      |-test_register_spoke_accounts.py
      |-test_request_event.py
    |__init__.py
    |-dynamo_table.py
    |-register_spoke_accounts.py
    |-request_event.py
  |-uuid_helper/
    |__tests__/
      |__init__.py
      |-conftest.py
      |-test_uuid_helper.py
    |__init__.py
    |-uuid_helper.py
  |-workspaces_app/
    |-workspaces_app/
      |__tests__/
        |__init__.py
        |-conftest.py
        |-test_account_registry.py
        |-test_directory_reader.py
        |-test_metrics_helper.py
        |-test_workspaces_helper.py
      |-utils/
        |__tests__/
          |__init__.py
          |-conftest.py
          |-test_s3_utils.py
          |-test_timer.py
        |__init__.py
        |-decimal_encoder.py
        |-s3_utils.py
        |-solutions_metrics.py
        |-timer.py
      |-directory_reader.py
      |-metrics_helper.py
      |-workspaces_helper.py
    |-main.py
  |-requirements.txt
  |-testing_requirements.txt
  |-architecture_diagram.png
  |-Dockerfile
|-.gitignore
|-buildspec.yml
|-CHANGELOG.md
|-CODE_OF_CONDUCT.md
|-CONTRIBUTING.md
|-LICENSE.txt
|-NOTICE.txt
|-README.md
|-sonar-project.properties
</pre>


################################################

<a name="collection-of-operational-metrics"></a>
# Collection of operational metrics

This solution collects anonymous operational metrics to help AWS improve the
quality of features of the solution. For more information, including how to disable
this capability, please see the
[Implementation Guide](https://docs.aws.amazon.com/solutions/latest/aws-security-hub-automated-response-and-remediation/collection-of-operational-metrics.html)

<a name="license"></a>
# License

See license
[here](https://github.com/awslabs/%3Cinsert-solution-repo-name%3E/blob/master/LICENSE.txt).
