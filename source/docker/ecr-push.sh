#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

usage() {
  echo "$0 <registry> <image> <tag>"
  echo "Example: $0 111111111111.dkr.ecr.us-east-1.amazonaws.com workspaces-cost-optimizer latest"
}

main() {
  declare registry=$1 image=$2 tag=$3
  if [ -z "$registry" ] || [ -z "$image" ] || [ -z "$tag" ]; then usage && exit 1; fi

  docker tag "$image":"$tag" "$registry"/"$image":"$tag"
  docker push "$registry"/"$image":"$tag"
}

main "$@"
