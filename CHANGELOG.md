# Change Log
 All notable changes to this project will be documented in this file.

 The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
 and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.8.2] - 2025-11
### Fixed
- Updated openssl to mitigate [CVE-2025-9232](https://avd.aquasec.com/nvd/cve-2025-9232) and [CVE-2025-9230](https://avd.aquasec.com/nvd/cve-2025-9230)
- Updated js-yaml to mitigate [CVE-2025-64718](https://avd.aquasec.com/nvd/cve-2025-64718)

## [2.8.1] - 2025-09
### Fixed
- Updated the base python image in the Dockerfile to address package vulnerabilities

## [2.8.0] - 2025-07
### Added
- Support for standby workspaces identification and management
- Maintenance mode billing support for AUTO_STOP workspaces
- Billable hours increment cap to prevent abnormal usage spikes
- WorkspaceType column in usage reports to distinguish PRIMARY/STANDBY workspaces

### Removed
- AppRegistry application resources and components
- Associated AppRegistry tags and configurations

### Fixed
- Updated urllib3 to mitigate [CVE-2025-50181](https://avd.aquasec.com/nvd/cve-2025-50181), [CVE-2025-50182](https://avd.aquasec.com/nvd/cve-2025-50182)
- Updated requests to mitigate [CVE-2024-47081 ](https://avd.aquasec.com/nvd/cve-2024-47081)

## [2.7.7] - 2025-05
### Updated
- Update base python image to mitigate [CVE-2024-56406](https://nvd.nist.gov/vuln/detail/CVE-2024-56406)
- Upgraded aws-cdk-lib to version 2.189.1


## [2.7.6] - 2025-04
### Added
- Updated AppRegistry implementation to use tag-based approach instead of CFN-based association.

### Fixed
- Update base python image to mitigate [CVE-2025-0395](https://nvd.nist.gov/vuln/detail/CVE-2025-0395), [CVE-2024-12133](https://nvd.nist.gov/vuln/detail/CVE-2024-12133), [CVE-2024-12243](https://nvd.nist.gov/vuln/detail/CVE-2024-12243)

## [2.7.5] - 2025-01
### Fixed
- Updated aws-lambda-powertools from version 2.39.1 to 3.4.1
- Improved handling of workspace termination logic

## [2.7.4] - 2024-11
### Fixed
- Upgrade cross-spawn to mitigate [CVE-2024-21538](https://nvd.nist.gov/vuln/detail/CVE-2024-21538)
- Migrated from pip to poetry

## [2.7.3] - 2024-10
### Fixed
- Update base python image to mitigate [CVE-2024-45490](https://security-tracker.debian.org/tracker/CVE-2024-45490), [CVE-2024-45491](https://security-tracker.debian.org/tracker/CVE-2024-45491), [CVE-2024-45492](https://security-tracker.debian.org/tracker/CVE-2024-45492), [CVE-2023-7104](https://security-tracker.debian.org/tracker/CVE-2023-7104)

## [2.7.2] - 2024-09
### Fixed
- Some user sesssions not appearing in session table due to batchWrite API limit being reached

## [2.7.1] - 2024-08
### Added
- Security.md file

### Fixed
- Workspace analysis failing when pervious data is recorded in database but empty.
- Workspace analysis failing when timestamps from user connected data doesn't exist in other metric data.
- Workspace only reporting 24 hour period
- Workspace not reporting tags
- Updated micromatch to mitigate [CVE-2024-4067](https://avd.aquasec.com/nvd/2024/cve-2024-4067).

## [2.7.0] - 2024-07
### Added
- Workspace performance metrics
- DynamoDB tables for workspace data and for individual user sessions
- Auto-updating container image for most recent patches up to next minor release
- Private subnets for Fargate container
- Powertools logging
- Operational insights CloudWatch dashboard
- Support for G4DN workspaces

### Fixed
- sts token expired after one hour

## [2.6.6] - 2024-07
### Fixed
- Updated the base python image in the Dockerfile used to mitigate [CVE-2023-50387](https://security-tracker.debian.org/tracker/CVE-2023-50387), [CVE-2023-5678](https://security-tracker.debian.org/tracker/CVE-2023-5678), [CVE-2024-0727](https://security-tracker.debian.org/tracker/CVE-2024-0727), [CVE-2023-6129](https://security-tracker.debian.org/tracker/CVE-2023-6129) and several low severity vulnerabilities
- Updated braces to mitigate [CVE-2024-4068](https://nvd.nist.gov/vuln/detail/CVE-2024-4068).
- Updated IDNA to mitigate [CVE-2024-3651](https://nvd.nist.gov/vuln/detail/CVE-2024-3651).
- Updated urllib3 to mitigate [CVE-2024-37891](https://nvd.nist.gov/vuln/detail/CVE-2024-37891).
- Updated setuptools to mitigate [CVE-2024-6345](https://nvd.nist.gov/vuln/detail/CVE-2024-6345).
- Updated requests to mitigate [CVE-2024-35195](https://nvd.nist.gov/vuln/detail/CVE-2024-35195).
- Updated Certifi to mitigate [CVE-2024-39689](https://nvd.nist.gov/vuln/detail/CVE-2024-39689).
- Updated boto3, botocore, s3transfer to resolve conflicting dependencies.

## [2.6.5] - 2024-02
### Fixed
- Updated the base python image in the Dockerfile used to mitigate [CVE-2023-47038](https://security-tracker.debian.org/tracker/CVE-2023-47038).
- Update pip to mitigate [CVE-2023-5752](https://nvd.nist.gov/vuln/detail/CVE-2023-5752).
- Add dependency to route to mitigate race condition between internet gateway and the route to the internet gateway.

## [2.6.4] - 2023-10
 ### Fixed
 - Updated @babel/traverse to mitigate [CVE-2023-45133](https://github.com/aws-solutions/cost-optimizer-for-amazon-workspaces/pull/61)
 - Updated urllib3 to mitigate [CVE-2023-45803](https://github.com/aws-solutions/cost-optimizer-for-amazon-workspaces/pull/59)
 - Updated the base python image in the Dockerfile used to fix the following CVEs: [CVE-2023-29491](https://nvd.nist.gov/vuln/detail/CVE-2023-29491), [CVE-2023-4911](https://nvd.nist.gov/vuln/detail/CVE-2023-4911), [CVE-2023-36054](https://nvd.nist.gov/vuln/detail/CVE-2023-36054), [CVE-2023-3446](https://nvd.nist.gov/vuln/detail/CVE-2023-3446), [CVE-2023-3817](https://nvd.nist.gov/vuln/detail/CVE-2023-3817).

## [2.6.3] - 2023-09
 ### Fixed
 - Added the bugfix to skip the processing of the workspaces in error state.
 - Updated all the package versions to resolve security vulnerabilities.
 - Patch Certifi vulnerability. Removal of e-Tugra root certificate [CVE-2023-37920](https://github.com/advisories/GHSA-xqr8-7jwr-rhp7)
 - Patch Requests vulnerability. Leaking Proxy-Authorization headers [CVE-2023-32681](https://nvd.nist.gov/vuln/detail/CVE-2023-32681)
 - Patch aws-cdk-lib vulnerability. EKS overly permissive trust policies [CVE-2023-35165](https://nvd.nist.gov/vuln/detail/CVE-2023-35165)
 - Patch ECR base image vulnerabilities, fixing the following: [CVE-2023-2650](https://nvd.nist.gov/vuln/detail/CVE-2023-2650) [CVE-2022-29458](https://nvd.nist.gov/vuln/detail/CVE-2022-29458) [CVE-2022-3821](https://nvd.nist.gov/vuln/detail/CVE-2022-3821) [CVE-2023-0465](https://nvd.nist.gov/vuln/detail/CVE-2023-0465) [CVE-2022-4415](https://nvd.nist.gov/vuln/detail/CVE-2022-4415) [CVE-2023-0464](https://nvd.nist.gov/vuln/detail/CVE-2023-0464) [CVE-2023-0466](https://nvd.nist.gov/vuln/detail/CVE-2023-0466)
 - Updated the docker base image to the python 3.11.
 - Updated all the lambda runtimes to python 3.11.

## [2.6.2] - 2023-04
 ### Fixed
 - Changed the Object Ownership for logging bucket from 'Object writer' to 'Bucket owner enforced' to mitigate the impact caused by new S3 default settings.
 - Updated S3 bucket policy to support access logging.

## [2.6.1] - 2023-04
 ### Added
 - Added support to block customer misconfiguration for 'Terminate Unused Workspaces' feature. The feature will terminate workspaces only on the last day of the month to avoid accidental termination due to misconfiguration.

## [2.6.0] - 2023-03
 ### Added
 - Updated the solution to use CDK V2 to generate CloudFormation templates and support CDK deployments.
 - Updated the 'Terminate Workspace' feature to accept user input for number of months to check for before terminating unused workspaces.
 - Added a retention policy of 365 days to ECS logs to optimize the costs.

### Removed
- The CFN templates from the deployment folder as we are using CDK V2 to generate templates.

## [2.5.1] - 2023-01
 ### Fixed
 - Fixed vulnerabilities py [CVE-2022-42969](https://nvd.nist.gov/vuln/detail/CVE-2022-42969), pytest, requests, certifi [CVE-2022-23491](https://nvd.nist.gov/vuln/detail/CVE-2022-23491)

 ## [2.5] - 2022-08
 ### Added
 - Added support for AWS Organizations
 - Added VPC Endpoints for S3 and DynamoDB

 ## [2.4.1] - 2021-10
 - Fixed the bug to get all the workspaces in a directory

 ## [2.4] - 2021-09
 ### Fixed
 - Fixed the bug to correctly calculate billable hours if user disconnects workspace within autostop timeout

 ### Added
 - Feature to terminate unused workspaces
 - Generate aggregated reports
 - Feature to specify AWS Regions to monitor
 - Support for Gov cloud partition

 ## [2.3] - 2021-06
 ### Fixed
 - Fixed the bug to catch InvalidResourceException during the modify_workspace API Call
 - Fixed the bug to catch the Timeout error when sending solution metrics

 ### Added
 - Feature to support using existing VPC for ECS task
 - Calculate ADMIN_MAINTENANCE hours and add it to final billable hours
 - Added new columns to the daily report
 - Improved the accuracy to calculate billable hours

 ## [2.2.1] - 2020-04-22
 ### Fixed
 - Removed the the api call for describe_workspace_bundles to address the throttling issue
 - Changed the metric to calculate billable hours from "Stopped" to "UserConnected"

 ## [2.2.0] - 2019-11-12
 ### Added
- Made tagging case insensitive
- Removed duplicate handler in CF
