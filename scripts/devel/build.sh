#!/bin/bash

reset
mkdir -p logs
rm -f logs/MiAZ-BUILD-*

# Increase version build numver
./scripts/devel/increase_meson_version.sh build

# Execute the script to get the app version
app_version=$(./scripts/devel/increase_meson_version.sh)

# Check if the app version was successfully retrieved
if [ -z "$app_version" ]; then
  echo "Error: Failed to retrieve the app version."
  exit 1
fi

# Generate a timestamp in the format YYYYmmdd_hhmm
timestamp=$(date +"%Y%m%d_%H%M")

# Create the log file name
log_file="logs/MiAZ-BUILD-${timestamp}-${app_version}.log"

# Create the log file (empty for now, but you can add content as needed)
echo "$log_file"

# Output the log file name for confirmation
./scripts/install/local/install_user.sh >> $log_file

# Execute the script to get the app version
installed=$(grep 'App installed successfully.' $log_file)

# Check if the app version was successfully retrieved
if [ -z "$installed" ]; then
  echo "Error during building: Check $log_file for more details"
  exit 1
fi

echo "$installed"

