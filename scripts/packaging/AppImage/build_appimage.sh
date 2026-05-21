#!/bin/bash
# Build a portable AppImage for MiAZ.
#
# MiAZ is a Python/PyGObject app, so this AppImage does NOT bundle the
# GTK stack. It relies on the host providing:
#   - Python 3.9+
#   - PyGObject (gi) matching the host's GLib
#   - GTK 4.6+
#   - libadwaita 1.6+
#
# Why not bundle GTK? linuxdeploy-plugin-gtk bundles libglib/libgobject
# but not the newer libgirepository-2.0 split (GLib 2.80+). On hosts
# that ship PyGObject built against girepository-2.0 (Fedora 40+,
# Ubuntu 24.10+), the bundled stack and the system PyGObject load
# incompatible copies of GLib into the same process and crash on
# `import gi`. Shipping a self-contained Python+GTK stack would require
# switching to python-appimage or a similar relocatable interpreter.
#
# Run from anywhere; the script locates the repo root automatically.
# Optional: ARCH env var (defaults to x86_64)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

ARCH="${ARCH:-x86_64}"
LINUXDEPLOY_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${ARCH}.AppImage"
LINUXDEPLOY_DIR="$REPO_ROOT"
LINUXDEPLOY="$LINUXDEPLOY_DIR/linuxdeploy-${ARCH}.AppImage"
LINUXDEPLOY_EXTRACTED="$LINUXDEPLOY_DIR/linuxdeploy-${ARCH}.AppDir"

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
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/" \
    | sed "s/+.*//")
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"
log "Version: $VERSION"

OUTPUT="$REPO_ROOT/MiAZ-${VERSION}-${ARCH}.AppImage"

# ── preflight ────────────────────────────────────────────────────────────────
# patchelf is used by linuxdeploy to fix RPATHs of any binaries it does
# bundle (currently none, since we skip the gtk plugin).
require meson ninja patchelf

# Download linuxdeploy if not present
if [[ ! -x "$LINUXDEPLOY" ]]; then
    log "linuxdeploy not found, downloading from GitHub ..."
    require wget
    wget -c --show-progress "$LINUXDEPLOY_URL" -O "$LINUXDEPLOY"
    chmod +x "$LINUXDEPLOY"
fi

cd "$REPO_ROOT"

# ── always build from fresh sources ───────────────────────────────────────────
# Wipe every artefact derived from MiAZ source code. Only the linuxdeploy
# tool itself (binary + extracted/patched copy) is intentionally cached,
# since it is not MiAZ code and re-downloading/re-extracting it on every
# build would be slow and noisy.
log "Wiping previous build artefacts (AppDir, builddir, AppImage output) ..."
rm -rf builddir_appimage AppDir
rm -f "$OUTPUT" "$REPO_ROOT/MiAZ-${ARCH}.AppImage"

# Stale __pycache__ directories in the working tree would be copied into
# AppDir by `install_subdir`, shipping orphan .pyc files for sources that
# may no longer exist. Strip them from the source tree before installing.
log "Removing stale __pycache__ from source tree ..."
find "$REPO_ROOT/MiAZ" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── meson install into AppDir ─────────────────────────────────────────────────
log "Installing into AppDir via meson (DESTDIR) ..."
meson setup builddir_appimage --prefix=/usr -Dprofile=release --wipe
ninja -C builddir_appimage
DESTDIR="$REPO_ROOT/AppDir" ninja -C builddir_appimage install

# Defensive sweep: drop any __pycache__/.pyc that survived the install step
# (e.g. created during a meson configure-time tool run).
find "$REPO_ROOT/AppDir" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$REPO_ROOT/AppDir" -type f -name '*.pyc' -delete 2>/dev/null || true

# Rewrite the launcher's hardcoded sys.path entry so the bundled MiAZ
# always wins over any system install. meson substitutes @pkgdatadir@
# with /usr/share/MiAZ (because the AppImage is configured with
# --prefix=/usr), which means a leftover host install at /usr/share/MiAZ
# shadows the bundle and the AppImage reports the host's MiAZ version.
# The replacement resolves the package directory from __file__ so it
# always points at AppDir/usr/share/MiAZ when run from inside the
# AppImage mount, regardless of where the AppImage is launched from.
MIAZ_LAUNCHER="$REPO_ROOT/AppDir/usr/bin/miaz"
[[ -f "$MIAZ_LAUNCHER" ]] || die "miaz launcher missing at $MIAZ_LAUNCHER"
log "Patching miaz launcher to use AppDir-relative sys.path entry ..."
sed -i \
  "s|sys\.path\.insert(1, '/usr/share/MiAZ')|sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'share', 'MiAZ'))|" \
  "$MIAZ_LAUNCHER"
grep -q "os.path.realpath(__file__)" "$MIAZ_LAUNCHER" \
    || die "sed patch on $MIAZ_LAUNCHER did not apply, check meson output"

# Copy the canonical AppRun from the packaging scripts directory.
# The meson DESTDIR install does not create AppRun; it lives in the repo
# at scripts/packaging/AppImage/AppRun and is copied here each build.
APPRUN_SRC="$SCRIPT_DIR/AppRun"
[[ -f "$APPRUN_SRC" ]] || die "AppRun source not found at $APPRUN_SRC"
cp "$APPRUN_SRC" "$REPO_ROOT/AppDir/AppRun"
chmod +x "$REPO_ROOT/AppDir/AppRun"
log "AppRun installed to AppDir/AppRun"

[[ -x "$REPO_ROOT/AppDir/AppRun" ]] || die "AppDir/AppRun missing or not executable"

# ── linuxdeploy ───────────────────────────────────────────────────────────────
log "Running linuxdeploy to validate AppDir and produce AppImage ..."

export ARCH
export VERSION
export OUTPUT="$OUTPUT"
export DISABLE_STRIP=1
export NO_STRIP=1

# linuxdeploy's bundled `strip` is an old binutils that cannot handle the
# SHT_RELR section type (0x13, .relr.dyn) used by modern Fedora/Ubuntu
# toolchains. The STRIP / DISABLE_STRIP env vars are ignored by the
# `continuous` build, so the only reliable fix is to extract the AppImage,
# replace its bundled strip with a no-op stub, and run the extracted AppRun.
if [[ ! -x "$LINUXDEPLOY_EXTRACTED/AppRun" ]]; then
    log "Extracting linuxdeploy AppImage to patch its bundled strip ..."
    rm -rf "$LINUXDEPLOY_EXTRACTED" "$LINUXDEPLOY_DIR/squashfs-root"
    ( cd "$LINUXDEPLOY_DIR" && "$LINUXDEPLOY" --appimage-extract >/dev/null )
    mv "$LINUXDEPLOY_DIR/squashfs-root" "$LINUXDEPLOY_EXTRACTED"
fi

STRIP_STUB="$LINUXDEPLOY_EXTRACTED/usr/bin/strip"
if [[ ! -f "$STRIP_STUB.orig" ]]; then
    log "Replacing bundled strip with no-op stub (preserves .orig backup)."
    mv "$STRIP_STUB" "$STRIP_STUB.orig"
    cat > "$STRIP_STUB" <<'EOF'
#!/bin/sh
# No-op stub: bundled strip aborts on SHT_RELR (.relr.dyn) sections
# emitted by modern toolchains. Skipping strip is harmless.
exit 0
EOF
    chmod +x "$STRIP_STUB"
fi

"$LINUXDEPLOY_EXTRACTED/AppRun" \
    --appdir "$REPO_ROOT/AppDir" \
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
        die "AppImage not found after build, check linuxdeploy output above."
    fi
fi
