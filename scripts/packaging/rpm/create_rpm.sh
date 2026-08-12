#!/bin/bash
# Build an RPM package for MiAZ using rpmbuild + meson.
# Run from anywhere; the script locates the repo root automatically.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# ── helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[rpm] $*"; }
die()  { echo "[rpm] ERROR: $*" >&2; exit 1; }

require() {
    for cmd in "$@"; do
        command -v "$cmd" &>/dev/null || die "Required tool not found: $cmd"
    done
}

# ── source ───────────────────────────────────────────────────────────────────
# Everything below reads from the export, never from the working tree: the
# sources, the spec and the version all come from one commit. See
# ../lib/source_export.sh.
source "$SCRIPT_DIR/../lib/source_export.sh"
miaz_prepare_source "$REPO_ROOT" "rpm"

VERSION="$MIAZ_SRC_VERSION"
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"

# meson.build owns the full version, for example 0.1.50+build.13. RPM splits it:
# Version: is the release version, which is what the spec's %changelog names,
# and Release: carries the build counter, which is what that field is for.
# Keeping the counter in Version: made every build disagree with its own
# changelog (rpmlint: incoherent-version-in-changelog).
BASE_VERSION="${VERSION%%+*}"
if [[ "$VERSION" == *"+build."* ]]; then
    BUILD_COUNTER="${VERSION##*+build.}"
else
    BUILD_COUNTER="1"
fi
log "RPM Version: $BASE_VERSION, Release: $BUILD_COUNTER"

NAME="miaz"
# Source0 is %{name}-%{version}.tar.gz and %prep uses %autosetup, so the
# tarball and its prefix directory follow Version:, not the full version.
TARBALL="${NAME}-${BASE_VERSION}.tar.gz"
SPEC="$MIAZ_SRC_DIR/${NAME}.spec"

# ── preflight ────────────────────────────────────────────────────────────────
require git rpmbuild desktop-file-validate

[[ -f "$SPEC" ]] || die "Spec file not found in the exported source: $SPEC"

# ── rpmbuild tree ─────────────────────────────────────────────────────────────
RPMROOT="$HOME/rpmbuild"
mkdir -p "$RPMROOT"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# ── source tarball ────────────────────────────────────────────────────────────
# Packed from the export rather than straight out of git, so the tarball, the
# spec and the version provably come from the same tree. The export directory
# is renamed to what %autosetup expects as it is packed.
log "Creating source tarball $TARBALL ..."
SRC_PARENT="$(dirname "$MIAZ_SRC_DIR")"
SRC_NAME="$(basename "$MIAZ_SRC_DIR")"
tar -czf "$RPMROOT/SOURCES/$TARBALL" \
    --transform="s,^${SRC_NAME},${NAME}-${BASE_VERSION}," \
    -C "$SRC_PARENT" "$SRC_NAME"

cp "$SPEC" "$RPMROOT/SPECS/"

# Keep the spec version in sync with meson.build
sed -i "s/^Version:.*/Version:        $BASE_VERSION/" "$RPMROOT/SPECS/${NAME}.spec"
sed -i "s/^Release:.*/Release:        ${BUILD_COUNTER}%{?dist}/" "$RPMROOT/SPECS/${NAME}.spec"

# rpmlint compares the newest %changelog entry against Version-Release. The
# spec in the repository carries the release version with -1, written by
# sync_versions.sh, so the newest entry of this copy is given the release this
# build actually produces. The repository file is left alone: it is the release
# history, not a build artifact.
sed -i "0,/^\(\* .* - ${BASE_VERSION}\)-[0-9][0-9]*$/s//\1-${BUILD_COUNTER}/" \
    "$RPMROOT/SPECS/${NAME}.spec"

# ── build ─────────────────────────────────────────────────────────────────────
log "Running rpmbuild ..."
rpmbuild -ba "$RPMROOT/SPECS/${NAME}.spec"

# ── report ────────────────────────────────────────────────────────────────────
log "Done. Packages written to:"
find "$RPMROOT/RPMS" "$RPMROOT/SRPMS" -name "${NAME}-${BASE_VERSION}-${BUILD_COUNTER}*" | sort | while read -r pkg; do
    log "  $pkg"
done

log ""
log "Install with:"
log "  sudo rpm -Uhv \$(find $RPMROOT/RPMS -name '${NAME}-${BASE_VERSION}-${BUILD_COUNTER}*.rpm' | head -1)"
