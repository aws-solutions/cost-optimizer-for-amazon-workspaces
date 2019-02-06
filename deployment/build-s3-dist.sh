#!/bin/bash

# This script should be run from the repo's root directory
# ./deployment/build-s3-dist.sh source-bucket-base-name
# source-bucket-base-name should be the base name for the S3 bucket location where the template will source the Lambda code from.
# The template will append '-[region_name]' to this bucket name.
# For example: ./deployment/build-s3-dist.sh solutions
# The template will then expect the source code to be located in the solutions-[region_name] bucket

# Check to see if input has been provided:
if [ -z "$2" ]; then
    echo "Please provide the base source bucket name and version number where the lambda code will eventually reside.\nFor example: ./build-s3-dist.sh solutions v1.0"
    exit 1
fi

# Create `dist` directory
echo "Starting to build distribution"
export initial_dir=`pwd`
export dist_dir="$initial_dir/deployment/dist"
mkdir -p "$dist_dir"

# Copy CFT & swap parameters
cp -f "./deployment/workspaces-cost-optimizer.template" "$dist_dir"
echo "Updating code source bucket in template with $1"
replace="s/%%BUCKET_NAME%%/$1/g"
sed -i '' -e $replace "$dist_dir/workspaces-cost-optimizer.template"
echo "Updating code version in template with $2"
replace="s/%%VERSION%%/$2/g"
sed -i '' -e $replace "$dist_dir/workspaces-cost-optimizer.template"


# Build Lambda zip
echo "Building Lambda package"

zip -q -r9 $dist_dir/workspaces-cost-optimizer.zip source/*
zip -q -d  $dist_dir/workspaces-cost-optimizer.zip *fargate-schedule.py
echo "Completed building distribution"
cd $initial_dir
