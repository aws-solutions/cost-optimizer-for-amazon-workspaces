#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

main() {
  # "$root_dir"/deployment/run-unit-tests.sh
  local root_dir=$(dirname "$(cd -P -- "$(dirname "$0")" && pwd -P)")
  local template_dir="$root_dir"/deployment
  local source_dir="$root_dir"/source
  local venv="$root_dir"/.venv

  [[ ! -d "$venv" ]] && python3 -m venv "$venv"
  source "$venv"/bin/activate
  unset AWS_PROFILE
  python3 -m pip install --upgrade pip setuptools wheel

  local requirements_files=(
    "$source_dir"/testing_requirements.txt
  )

  for requirements_file in ${requirements_files[@]}; do
    python3 -m pip install -r "$requirements_file"
  done

  local coverage_dir="$template_dir"/test/coverage-reports
  rm -rf "$coverage_dir"
  mkdir -p "$coverage_dir"

  [[ -a "$source_dir"/uuid_helper/cfnresponse.py ]] && rm "$source_dir"/uuid_helper/cfnresponse.py
  [[ -a "$source_dir"/account_registration_provider/cfnresponse.py ]] && rm "$source_dir"/account_registration_provider/cfnresponse.py
  ln -s "$source_dir"/lib/cfnresponse.py "$source_dir"/uuid_helper/cfnresponse.py
  ln -s "$source_dir"/lib/cfnresponse.py "$source_dir"/account_registration_provider/cfnresponse.py

  pushd "$source_dir"
  python3 -m coverage run -m pytest && \
    python3 -m coverage xml && \
    python3 -m coverage report || \
    true
  popd

  rm "$source_dir"/uuid_helper/cfnresponse.py
  rm "$source_dir"/account_registration_provider/cfnresponse.py

  # coverage reports generate with absolute path which would conflict with sonarqube
  sed -i -e "s,<source>"$source_dir"</source>,<source>source</source>,g" "$coverage_dir"/wco.coverage.xml

  deactivate
}

main "$@"
