#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

main() {
  # "$root_dir"/deployment/run-unit-tests.sh
  local root_dir
  root_dir=$(dirname "$(cd -P -- "$(dirname "$0")" && pwd -P)")
  local template_dir="$root_dir"/deployment
  local source_dir="$root_dir"/source

  echo "Installing python packages including development dependencies"
  cd "$source_dir"

  # Use poetry directly if it's in the path, otherwise use POETRY_HOME
  if command -v poetry &> /dev/null; then
    POETRY_CMD="poetry"
  else
    POETRY_CMD="$POETRY_HOME/bin/poetry"
  fi

  $POETRY_CMD install --with dev

  local coverage_dir="$template_dir"/test/coverage-reports
  rm -rf "$coverage_dir"
  mkdir -p "$coverage_dir"

  [[ -a "$source_dir"/lambda/uuid_generator/cfnresponse.py ]] && rm "$source_dir"/lambda/uuid_generator/cfnresponse.py
  [[ -a "$source_dir"/lambda/account_registration_provider/cfnresponse.py ]] && rm "$source_dir"/lambda/account_registration_provider/cfnresponse.py
  ln -s "$source_dir"/lambda/utils/cfnresponse.py "$source_dir"/lambda/uuid_generator/cfnresponse.py
  ln -s "$source_dir"/lambda/utils/cfnresponse.py "$source_dir"/lambda/account_registration_provider/cfnresponse.py

  pushd "$source_dir"
  $POETRY_CMD run python -m coverage run -m pytest && \
    $POETRY_CMD run python -m coverage xml && \
    $POETRY_CMD run python -m coverage report || \
    true
  popd

  rm "$source_dir"/lambda/uuid_generator/cfnresponse.py
  rm "$source_dir"/lambda/account_registration_provider/cfnresponse.py

  # coverage reports generate with absolute path which would conflict with sonarqube
  sed -i -e "s,<source>$source_dir</source>,<source>source</source>,g" "$coverage_dir"/wco.coverage.xml

  # Run the cdk snapshot test

  cd "$source_dir"
  npm install
  npm run test
}

main "$@"
