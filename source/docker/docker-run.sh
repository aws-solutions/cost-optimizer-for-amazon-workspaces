#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

main() {
  AWS_ACCESS_KEY_ID=$(aws --profile wcoprofile configure get aws_access_key_id)
  AWS_SECRET_ACCESS_KEY=$(aws --profile wcoprofile configure get aws_secret_access_key)

  docker run \
    -e BucketName="$1" \
    -e LogLevel="INFO" \
    -e DryRun="Yes" \
    -e TestEndOfMonth="No" \
    -e SendAnonymousData="No" \
    -e SolutionVersion="v2.0" \
    -e SolutionID="SO0018" \
    -e ValueLimit="81" \
    -e StandardLimit="85" \
    -e PerformanceLimit="80" \
    -e PowerLimit="92" \
    -e PowerProLimit="78" \
    -e GraphicsG4dnLimit="334" \
    -e GraphicsProG4dnLimit="80" \
    -e UUID="abcdefghi" \
    -e AWS_DEFAULT_REGION="us-east-1" \
    -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    wco-container

}

main "$@"
