#!/usr/bin/python3
# -*- coding: utf-8 -*-

import semver
current = open('MiAZ/data/docs/VERSION', 'r').read().strip()
print("Current version: %s" % current)
version = semver.VersionInfo.parse(current).bump_build()
print("Next build: %s" % version)
with open('MiAZ/data/docs/VERSION', 'w') as fv:
    fv.write(str(version).strip())
