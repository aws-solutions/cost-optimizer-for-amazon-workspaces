#!/bin/bash

# Create `dist` directory
echo "export initial_dir=`pwd`"
export initial_dir=`pwd`
export dist_dir="$initial_dir/deployment/dist"
echo "mkdir -p $dist_dir"
mkdir -p "$dist_dir"

# Create environment
echo "Creating virtualenv"
TMP="$dist_dir/tmp"
virtualenv "$TMP/env"
source "$TMP/env/bin/activate"

# Install dependencies
echo "Installing workspaces-cost-optimizer to virtual-environment"
pip install "./source" --target="$TMP/env/lib/python2.7/site-packages/"

# Run Tests
cd "./source"
python "./setup.py" test
cd "$initial_dir"

# Clean up virtual environment
pwd
echo "Cleaning up testing residual"
echo "rm -r $TMP"
rm -r "$TMP"
rm -rf source/workspaces_cost_optimizer.egg-info
find source/ -name "__pycache__" -type d -exec rm -rf {} +
find source/ -name ".eggs" -type d -exec rm -rf {} +
find source/ -name "*.pyc" -exec rm -rf {} +

cd "$initial_dir"
