#!/usr/bin/python3
# -*- coding: utf-8 -*-

import semver
current = open('data/docs/VERSION', 'r').read().strip()
print("Current version: %s" % current)
version = semver.VersionInfo.parse(current).bump_build()
print("Next build: %s" % version)
with open('data/docs/VERSION', 'w') as fv:
    fv.write(str(version).strip())
