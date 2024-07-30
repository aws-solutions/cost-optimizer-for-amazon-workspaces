#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
[[ "$TRACE" ]] && set -x
set -eo pipefail

header() {
  declare text=$1
  echo "------------------------------------------------------------------------------"
  echo "$text"
  echo "------------------------------------------------------------------------------"
}

usage() {
  echo "Please provide the base template-bucket, source-bucket-base-name, trademark-approved-solution-name and version"
  echo "For example: ./deployment/build-s3-dist.sh solutions solutions-code trademarked-solution-name v2.2"
}

pack_lambda() {
  # Pack source_dir/package_name into build_dist_dir/package_name.zip with included files
  local source_dir=$1; shift
  local package_name=$1; shift
  local build_dist_dir=$1; shift
  local includes=( "$@" )

  local package_temp_dir="$build_dist_dir"/"$package_name"
  [[ -d "$package_temp_dir" ]] && rm -r "$package_temp_dir"
  mkdir -p "$package_temp_dir"

  cp -r "$source_dir"/"$package_name" "$package_temp_dir"
  for include_file in "${includes[@]}"; do
    cp "$include_file" "$package_temp_dir"
  done

  pip install -r "$source_dir"/requirements.txt -t "$package_temp_dir"

  pushd "$package_temp_dir"
  local exclude_dirs=("__pycache__" "__tests__")
  for exclude_dir in "${exclude_dirs[@]}"; do
    find . -type d -name "$exclude_dir" -print0 | xargs -0 rm -rf
  done

  echo "Packed lambda $package_name contents:"
  ls -AlR
  zip -q -r9 "$build_dist_dir"/"$package_name".zip .

  popd
  rm -r "$package_temp_dir"
}

# ./deployment/build-s3-dist.sh source-bucket-base-name trademarked-solution-name version-code
#
# Parameters:
#  - template-bucket: Name for the S3 bucket location where the templates are found
#  - source-bucket-base-name: Name for the S3 bucket location where the Lambda source
#    code is deployed. The template will append '-[region_name]' to this bucket name.
#  - trademarked-solution-name: name of the solution for consistency
#  - version-code: version of the package
#
#    For example: ./deployment/build-s3-dist.sh template-bucket source-bucket-base-name my-solution v2.2
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
main() {
  declare template_bucket=$1 source_bucket=$2 solution=$3 version=$4
  if [ -z "$template_bucket" ] || [ -z "$source_bucket" ] || [ -z "$solution" ] || [ -z "$version" ]; then
    usage
    exit 1
  fi

  echo "template bucket = $template_bucket"
  echo "source bucket = $source_bucket"
  echo "solution = $solution"
  echo "version = $version"

  local root_dir
  root_dir=$(dirname "$(cd -P -- "$(dirname "$0")" && pwd -P)")
  local template_dir="$root_dir"/deployment
  local source_dir="$root_dir"/source

  local template_dist_dir="$template_dir"/global-s3-assets
  local build_dist_dir="$template_dir"/regional-s3-assets

  local wco_folder="$template_dir"/ecr/workspaces-cost-optimizer

  header "[Init] Clean old dist and template folders"

  local clean_directories=("$template_dist_dir" "$build_dist_dir" "$wco_folder")
  for dir in "${clean_directories[@]}"; do
    rm -rf "$dir"
    mkdir -p "$dir"
  done

  header "[Packing] Templates"

  echo "Updating tokens in template with token values"
  echo "PUBLIC_ECR_REGISTRY = $PUBLIC_ECR_REGISTRY"
  echo "PUBLIC_ECR_TAG = $PUBLIC_ECR_TAG"
  echo "Setting env variables"
  export SOLUTION_VERSION=$version SOLUTION_NAME=$solution DIST_OUTPUT_BUCKET=$source_bucket SOLUTION_TRADEMARKEDNAME=$solution

  local replace_regexes=(
    "s/%TEMPLATE_BUCKET_NAME%/$template_bucket/g"
    "s/%DIST_BUCKET_NAME%/$source_bucket/g"
    "s/%SOLUTION_NAME%/$solution/g"
    "s/%VERSION%/$version/g"
    "s|PUBLIC_ECR_REGISTRY|$PUBLIC_ECR_REGISTRY|g"
    "s/PUBLIC_ECR_TAG/$PUBLIC_ECR_TAG/g"
  )
  replace_args=()
  for regex in "${replace_regexes[@]}"; do
    replace_args=(-e "$regex" "${replace_args[@]}")
  done

  cd "$source_dir"
  npm install
  npx cdk synth cost-optimizer-for-amazon-workspaces >> "$template_dir"/cost-optimizer-for-amazon-workspaces.template
  npx cdk synth cost-optimizer-for-amazon-workspaces-spoke >> "$template_dir"/cost-optimizer-for-amazon-workspaces-spoke.template
  templates=(cost-optimizer-for-amazon-workspaces.template cost-optimizer-for-amazon-workspaces-spoke.template)

  for template in "${templates[@]}"; do
    sed "${replace_args[@]}" "$template_dir"/"$template" > "$template_dist_dir"/"$template"
    rm  "$template_dir"/"$template"
  done


  header "[Packing] lambda code"

  pack_lambda "$source_dir"/lambda uuid_generator "$build_dist_dir" "$source_dir"/lambda/utils/cfnresponse.py
  pack_lambda "$source_dir"/lambda account_registration_provider "$build_dist_dir" "$source_dir"/lambda/utils/cfnresponse.py
  pack_lambda "$source_dir"/lambda register_spoke_lambda "$build_dist_dir"

  header "[Copying] Dockerfile and code artifacts to deployment/ecr folder"

  cp "$source_dir"/Dockerfile "$wco_folder"
  cp "$source_dir"/.dockerignore "$wco_folder"
  cp -r "$source_dir"/workspaces_app "$wco_folder"
  cp -r "$source_dir"/docker "$wco_folder"
}

main "$@"
