#!/bin/bash

# Check if the meson.build file exists
if [ ! -f "meson.build" ]; then
  echo "Error: meson.build file not found in the current directory."
  exit 1
fi

# Extract the current version from meson.build
CURRENT_VERSION=$(grep -oP "version\s*:\s*'\K[0-9]+\.[0-9]+\.[0-9]+(\+build\.[0-9]+)?" meson.build)

# Check if the user provided a valid argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <major|minor|patch|build>"
  echo "Current version: $CURRENT_VERSION"
  exit 1
fi

if [ -z "$CURRENT_VERSION" ]; then
  echo "Error: Could not find a valid version string in meson.build."
  exit 1
fi

# Display the current version (including build version if it exists)
echo "Current version in meson.build: $CURRENT_VERSION"

# Split the version into main version and build version
IFS='+' read -r MAIN_VERSION BUILD_VERSION <<< "$CURRENT_VERSION"

# Split the main version into major, minor, and patch
IFS='.' read -r MAJOR MINOR PATCH <<< "$MAIN_VERSION"

# Initialize BUILD_NUMBER if it exists
if [ -n "$BUILD_VERSION" ]; then
  BUILD_NUMBER=$(echo "$BUILD_VERSION" | grep -oP 'build\.\K[0-9]+')
else
  BUILD_NUMBER=0
fi

# Increment the version based on the user's choice
case "$1" in
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    BUILD_NUMBER=0
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    BUILD_NUMBER=0
    ;;
  patch)
    PATCH=$((PATCH + 1))
    BUILD_NUMBER=0
    ;;
  build)
    BUILD_NUMBER=$((BUILD_NUMBER + 1))
    ;;
  *)
    echo "Error: Invalid argument. Use 'major', 'minor', 'patch', or 'build'."
    exit 1
    ;;
esac

# Construct the new version string
NEW_VERSION="$MAJOR.$MINOR.$PATCH"
if [ "$BUILD_NUMBER" -gt 0 ]; then
  NEW_VERSION="$NEW_VERSION+build.$BUILD_NUMBER"
fi

# Update the meson.build file with the new version
sed -i "s/version\s*:\s*'$CURRENT_VERSION'/version : '$NEW_VERSION'/" meson.build

# Print success message
echo "Version updated from $CURRENT_VERSION to $NEW_VERSION in meson.build."
