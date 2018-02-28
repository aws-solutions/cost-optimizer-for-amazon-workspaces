#!/bin/bash

# Cache starting location
echo "export initial_dir=`pwd`"
export dist_dir="$initial_dir/deployment/dist"

# Create environment
echo "Creating virtualenv"
TMP="$dist_dir/tmp"
virtualenv "$TMP/env"
source "$TMP/env/bin/activate"

# Install dependencies
echo "Installing workspaces-cost-optimizer to virtual-environment"
pip install "./source" --target="$TMP/env/lib/python2.7/site-packages/"

# Run Tests
echo "python -m unittest discover"
python -m unittest discover

# Clean up virtual environment
echo "rm -r $TMP"
rm -r "$TMP"

cd "$initial_dir"