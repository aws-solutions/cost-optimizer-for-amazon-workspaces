#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

usage() {
  echo "$0 <registry> <region>"
  echo "Example: $0 111111111111.dkr.ecr.us-east-1.amazonaws.com us-east-1"
}

main() {
  declare registry=$1 region=$2
  if [ -z "$registry" ] || [ -z "$region" ]; then usage && exit 1; fi

  aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$registry"
}

main "$@"
