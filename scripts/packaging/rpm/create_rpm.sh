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

# ── version ──────────────────────────────────────────────────────────────────
VERSION=$(grep -m1 "version" "$REPO_ROOT/meson.build" \
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/")
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"
log "Version: $VERSION"

NAME="miaz"
TARBALL="${NAME}-${VERSION}.tar.gz"
SPEC="$REPO_ROOT/${NAME}.spec"

# ── preflight ────────────────────────────────────────────────────────────────
require git rpmbuild desktop-file-validate

[[ -f "$SPEC" ]] || die "Spec file not found: $SPEC"

cd "$REPO_ROOT"

# Warn if there are uncommitted changes (they won't be in the tarball)
if ! git diff --quiet HEAD 2>/dev/null; then
    log "WARNING: uncommitted changes exist and will NOT be included in the tarball."
fi

# ── source tarball ────────────────────────────────────────────────────────────
log "Creating source tarball $TARBALL ..."
git archive --format=tar.gz --prefix="${NAME}-${VERSION}/" HEAD \
    -o "$TARBALL"

# ── rpmbuild tree ─────────────────────────────────────────────────────────────
RPMROOT="$HOME/rpmbuild"
mkdir -p "$RPMROOT"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

cp "$TARBALL" "$RPMROOT/SOURCES/"
cp "$SPEC"    "$RPMROOT/SPECS/"

# Keep the spec version in sync with meson.build
sed -i "s/^Version:.*/Version:        $VERSION/" "$RPMROOT/SPECS/${NAME}.spec"

# ── build ─────────────────────────────────────────────────────────────────────
log "Running rpmbuild ..."
rpmbuild -ba "$RPMROOT/SPECS/${NAME}.spec"

# ── report ────────────────────────────────────────────────────────────────────
log "Done. Packages written to:"
find "$RPMROOT/RPMS" "$RPMROOT/SRPMS" -name "${NAME}*${VERSION}*" | sort | while read -r pkg; do
    log "  $pkg"
done

log ""
log "Install with:"
log "  sudo rpm -Uhv \$(find $RPMROOT/RPMS -name '${NAME}-${VERSION}*.rpm' | head -1)"
