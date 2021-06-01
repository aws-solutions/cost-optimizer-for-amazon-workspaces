# Change Log
 All notable changes to this project will be documented in this file.
 
 The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
 and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
 
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


