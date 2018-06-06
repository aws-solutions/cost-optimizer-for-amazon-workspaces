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
echo "export initial_dir=`pwd`"
export initial_dir=`pwd`
export dist_dir="$initial_dir/deployment/dist"
echo "mkdir -p $dist_dir"
mkdir -p "$dist_dir"

# Copy CFT & swap parameters
echo "cp -f workspaces-cost-optimizer.template $dist_dir"
cp -f "./deployment/workspaces-cost-optimizer.template" "$dist_dir"
echo "Updating code source bucket in template with $1"
replace="s/%%BUCKET_NAME%%/$1/g"
echo "sed -i '' -e $replace $dist_dir/workspaces-cost-optimizer.template"
sed -i '' -e $replace "$dist_dir/workspaces-cost-optimizer.template"
echo "Updating code version in template with $2"
replace="s/%%VERSION%%/$2/g"
echo "sed -i '' -e $replace $dist_dir/workspaces-cost-optimizer.template"
sed -i '' -e $replace "$dist_dir/workspaces-cost-optimizer.template"

# Build Lambda zip
echo "Building Lambda package"
TMP="$dist_dir/tmp"
virtualenv "$TMP/env"
source "$TMP/env/bin/activate"

echo "Installing workspaces-cost-optimizer to virtual-environment"
pip install "./source" --target="$TMP/env/lib/python2.7/site-packages/"

echo "Creating Lambda zip package"
cd "$TMP/env/lib/python2.7/site-packages/"
zip -q -r9 $dist_dir/workspaces-cost-optimizer.zip *
zip -q -d $dist_dir/workspaces-cost-optimizer.zip "pip*" "easy*" "setup*" "wheel*" "pkg_resources*"
cd $initial_dir
echo "Cleaning up Python virtual environment"
rm -r "$TMP"

# Change back to initial directory
echo "Completed building distribution"
cd $initial_dir
