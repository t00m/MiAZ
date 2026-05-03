#!/bin/bash
# Build a self-contained AppImage for MiAZ.
# Run from anywhere; the script locates the repo root automatically.
#
# Requires: meson, ninja, linuxdeploy-x86_64.AppImage (downloaded if missing)
# Optional: ARCH env var (defaults to x86_64)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

ARCH="${ARCH:-x86_64}"
LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${ARCH}.AppImage"
LINUXDEPLOY="$REPO_ROOT/linuxdeploy-${ARCH}.AppImage"

# ── helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[appimage] $*"; }
die()  { echo "[appimage] ERROR: $*" >&2; exit 1; }

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

OUTPUT="$REPO_ROOT/MiAZ-${VERSION}-${ARCH}.AppImage"

# ── preflight ────────────────────────────────────────────────────────────────
require meson ninja

# Download linuxdeploy if not present
if [[ ! -x "$LINUXDEPLOY" ]]; then
    log "linuxdeploy not found — downloading from GitHub ..."
    require wget
    wget -c --show-progress "$LINUXDEPLOY_URL" -O "$LINUXDEPLOY"
    chmod +x "$LINUXDEPLOY"
fi

# Download linuxdeploy-plugin-gtk if not already in AppDir/apprun-hooks
GTK_HOOK="$REPO_ROOT/AppDir/apprun-hooks/linuxdeploy-plugin-gtk.sh"
if [[ ! -f "$GTK_HOOK" ]]; then
    log "Downloading linuxdeploy-plugin-gtk ..."
    require wget
    mkdir -p "$REPO_ROOT/AppDir/apprun-hooks"
    wget -c "https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh" \
        -O "$GTK_HOOK"
    chmod +x "$GTK_HOOK"
fi

cd "$REPO_ROOT"

# ── meson install into AppDir ─────────────────────────────────────────────────
log "Installing into AppDir via meson (DESTDIR) ..."
rm -rf builddir_appimage
meson setup builddir_appimage --prefix=/usr -Dprofile=release --wipe
ninja -C builddir_appimage
DESTDIR="$REPO_ROOT/AppDir" ninja -C builddir_appimage install

# Ensure AppRun is executable (linuxdeploy will create its own if absent,
# but we provide a custom one that sets PYTHONPATH correctly)
[[ -x "$REPO_ROOT/AppDir/AppRun" ]] || die "AppDir/AppRun missing or not executable"

# ── linuxdeploy ───────────────────────────────────────────────────────────────
log "Running linuxdeploy to bundle libraries and produce AppImage ..."

export ARCH
export VERSION
export DEPLOY_GTK_VERSION=4
export OUTPUT="$OUTPUT"

# linuxdeploy's bundled strip (old binutils) cannot handle the SHT_RELR
# section type (0x13, .relr.dyn) used by modern Fedora/Ubuntu toolchains.
# Fix: override the strip binary with the system one (binutils 2.32+
# understands SHT_RELR). DISABLE_STRIP=1 is kept as belt-and-suspenders
# for linuxdeploy versions that support it.
SYSTEM_STRIP="$(command -v strip 2>/dev/null || true)"
if [[ -n "$SYSTEM_STRIP" ]]; then
    export STRIP="$SYSTEM_STRIP"
    log "Using system strip: $SYSTEM_STRIP ($(strip --version 2>&1 | head -1))"
else
    export DISABLE_STRIP=1
    log "WARNING: system strip not found; stripping disabled entirely."
fi
export DISABLE_STRIP=1

"$LINUXDEPLOY" \
    --appdir "$REPO_ROOT/AppDir" \
    --plugin gtk \
    --desktop-file "$REPO_ROOT/data/io.github.t00m.MiAZ.desktop" \
    --icon-file    "$REPO_ROOT/data/io.github.t00m.MiAZ-icon.svg" \
    --output appimage

# ── report ────────────────────────────────────────────────────────────────────
if [[ -f "$OUTPUT" ]]; then
    log "Done: $OUTPUT"
    log "Run with: $OUTPUT"
else
    # linuxdeploy may use a slightly different name; find it
    FOUND=$(find "$REPO_ROOT" -maxdepth 1 -name "MiAZ*${ARCH}.AppImage" | head -1)
    if [[ -n "$FOUND" ]]; then
        log "Done: $FOUND"
    else
        die "AppImage not found after build — check linuxdeploy output above."
    fi
fi
