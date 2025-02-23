#!/usr/bin/python3

import semver

FILEPATH_VERSION = 'data/docs/VERSION'
current = open(FILEPATH_VERSION, 'r').read().strip()
print("Current version: %s" % current)
version = semver.VersionInfo.parse(current).bump_build()
print("Next build: %s" % version)
with open(FILEPATH_VERSION, 'w') as fv:
    fv.write(str(version).strip())
