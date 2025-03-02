#!/bin/bash

# Check if the meson.build file exists
if [ ! -f "meson.build" ]; then
  echo "Error: meson.build file not found in the current directory."
  exit 1
fi

# Extract the project name
PROJECT_NAME=$(grep -oP "project\s*\(\s*'\K[^']+" meson.build)

if [ -z "$PROJECT_NAME" ]; then
  echo "Error: Project name not found in meson.build."
  exit 1
fi

# Extract the version
VERSION=$(grep -oP "version\s*:\s*'\K[0-9]+\.[0-9]+\.[0-9]+(\+build\.[0-9]+)?" meson.build)

if [ -z "$VERSION" ]; then
  echo "Error: Version string not found in meson.build."
  exit 1
fi

# Print the results
echo "Project name in meson.build: $PROJECT_NAME"
echo "Version in meson.build: $VERSION"
