#!/bin/bash
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned 
# 
# This script should be run from the repo's home directory 
# 
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
# 
# Check to see if input has been provided: 
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then 
    echo "Please provide the base template-bucket, source-bucket-base-name, trademark-approved-solution-name and version" 
    echo "For example: ./deployment/build-s3-dist.sh solutions solutions-code trademarked-solution-name v2.2" 
    exit 1 
fi 

echo "template bucket = $1"
echo "source bucket = $2"
echo "solution = $3"
echo "version = $4"

# Get reference for all important folders 
template_dir="$PWD" 
source_dir="$template_dir/../source"

# There are now TWO dist directories
template_dist_dir="$template_dir/global-s3-assets" 
build_dist_dir="$template_dir/regional-s3-assets" 

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old dist and template folders"
echo "------------------------------------------------------------------------------"

echo "rm -rf $template_dist_dir" 
rm -rf $template_dist_dir 
echo "mkdir -p $template_dist_dir" 
mkdir -p $template_dist_dir 

echo "rm -rf $build_dist_dir" 
rm -rf $build_dist_dir 
echo "mkdir -p $build_dist_dir" 
mkdir -p $build_dist_dir 

echo "------------------------------------------------------------------------------"
echo "[Packing] Template"
echo "------------------------------------------------------------------------------"

# Replace tokens with parameter values and write to template directory
echo "Updating tokens in template with token values"

TEMPLATE="workspaces-cost-optimizer.template"
SUB1="s/%TEMPLATE_BUCKET_NAME%/$1/g"
SUB2="s/%DIST_BUCKET_NAME%/$2/g"
SUB3="s/%SOLUTION_NAME%/$3/g"
SUB4="s/%VERSION%/$4/g"

sed -e $SUB1 -e $SUB2 -e $SUB3 -e $SUB4 ./$TEMPLATE > $template_dist_dir/$TEMPLATE

# Build Lambda zip
echo "------------------------------------------------------------------------------"
echo "[Packing] lambda code"
echo "------------------------------------------------------------------------------"

cd $source_dir
# install third party library for python 3.8, 3.7 used botocore.vendor.requests
pip3 install -r ../source/requirements.txt -t .
ls -alt
zip -q -r9 $build_dist_dir/workspaces-cost-optimizer.zip .
echo "Completed building distribution"
cd $template_dir
