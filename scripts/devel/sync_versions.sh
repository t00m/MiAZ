#!/bin/bash

# Propagate the version from meson.build (the single source of truth) to every
# packaging metadata file. Safe to run on every build.
#
# meson.build owns the version, including the +build.N counter. This script
# uses the base release version (build metadata stripped) because that is what
# the declarations and the release history should carry. The packaging scripts
# still append the full version to the built artifacts.
#
# Behaviour:
#   - pyproject.toml and miaz.spec 'Version:' are single fields. They are
#     overwritten with the base version, idempotently.
#   - debian/changelog, the spec %changelog and the AppStream <releases> list
#     are release histories. A new entry is prepended only when the base
#     version changed, so plain build-counter bumps touch nothing. The note is
#     a placeholder pointing to CHANGELOG.md; edit it before a real release.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

MAINTAINER="Tomás Vírseda <tomasvirseda@gmail.com>"
METAINFO="data/io.github.t00m.MiAZ.metainfo.xml.in"

# Full version from meson, for example 0.1.28+build.30
FULL="$(grep -m1 -oP "version\s*:\s*'\K[^']+" meson.build || true)"
# Base release version, build metadata stripped, for example 0.1.28
BASE="${FULL%%+*}"
if [ -z "$BASE" ]; then
    echo "ERROR: could not read version from meson.build" >&2
    exit 1
fi

echo "meson.build version : $FULL"
echo "release version     : $BASE"

changed=0

# pyproject.toml: the [project] version field
if ! grep -qE "^version = \"$BASE\"$" pyproject.toml; then
    sed -i -E "s/^version = \".*\"/version = \"$BASE\"/" pyproject.toml
    echo "updated pyproject.toml version -> $BASE"
    changed=1
fi

# miaz.spec: the Version field
if ! grep -qE "^Version:[[:space:]]+$BASE$" miaz.spec; then
    sed -i -E "s/^(Version:[[:space:]]+).*/\1$BASE/" miaz.spec
    echo "updated miaz.spec Version -> $BASE"
    changed=1
fi

# debian/changelog: prepend a stanza when the release version is new
deb_top="$(head -1 debian/changelog | grep -oP '\(\K[^)]+' | sed 's/-.*//' || true)"
if [ "$deb_top" != "$BASE" ]; then
    date_deb="$(date -R)"
    tmp="$(mktemp)"
    {
        echo "miaz ($BASE-1) unstable; urgency=medium"
        echo
        echo "  * New release. See CHANGELOG.md for details."
        echo
        echo " -- $MAINTAINER  $date_deb"
        echo
        cat debian/changelog
    } > "$tmp"
    mv "$tmp" debian/changelog
    echo "prepended debian/changelog stanza -> $BASE-1"
    changed=1
fi

# miaz.spec %changelog: prepend an entry when the release version is new
spec_top="$(grep -m1 '^\* ' miaz.spec | grep -oP '\- \K[0-9.]+' || true)"
if [ "$spec_top" != "$BASE" ]; then
    date_rpm="$(date '+%a %b %d %Y')"
    tmp="$(mktemp)"
    awk -v ver="$BASE" -v who="$MAINTAINER" -v d="$date_rpm" '
        /^%changelog$/ {
            print
            print "* " d " " who " - " ver "-1"
            print "- New release. See CHANGELOG.md for details."
            print ""
            next
        }
        { print }
    ' miaz.spec > "$tmp"
    mv "$tmp" miaz.spec
    echo "prepended miaz.spec %changelog entry -> $BASE-1"
    changed=1
fi

# metainfo: prepend a <release> when the release version is new
meta_top="$(grep -m1 '<release ' "$METAINFO" | grep -oP 'version="\K[^"]+' || true)"
if [ "$meta_top" != "$BASE" ]; then
    date_iso="$(date '+%Y-%m-%d')"
    tmp="$(mktemp)"
    awk -v ver="$BASE" -v d="$date_iso" '
        /<releases>/ {
            print
            print "    <release version=\"" ver "\" date=\"" d "\" urgency=\"medium\">"
            print "      <description>"
            print "        <p>See CHANGELOG.md for details.</p>"
            print "      </description>"
            print "    </release>"
            next
        }
        { print }
    ' "$METAINFO" > "$tmp"
    mv "$tmp" "$METAINFO"
    echo "prepended metainfo release -> $BASE"
    changed=1
fi

if [ "$changed" -eq 0 ]; then
    echo "All version files already match $BASE. Nothing to do."
fi
