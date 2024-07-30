#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

usage() {
  echo "$0 <image>"
  echo "Example: $0 wco-container"
}

main() {
  declare image=$1
  if [ -z "$image" ]; then usage && exit 1; fi
  local source_dir
  source_dir=$(dirname "$(cd -P -- "$(dirname "$0")" && pwd -P)")
  docker build --pull --no-cache -t "$image" "$source_dir"
}

main "$@"
