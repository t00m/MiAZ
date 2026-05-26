#!/bin/bash
# Uninstall a system-wide (prefix=/usr) MiAZ installation.
#
# Prefers Meson's own uninstall when the original build dir is still present.
# If that build dir is gone (the previous failure mode: "cd builddir_system:
# No such file or directory"), it reconstructs the exact list of installed
# files with `meson introspect --installed` and removes just those paths.
#
# Run with sudo (or as root).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PREFIX=/usr
BUILD_DIR="$REPO_ROOT/builddir_system"

log() { echo "[uninstall] $*"; }
die() { echo "[uninstall] ERROR: $*" >&2; exit 1; }

# Use sudo only when we are not already root.
if [[ "$(id -u)" -eq 0 ]]; then SUDO=""; else SUDO="sudo"; fi

# 1) Authoritative path: Meson's own uninstall using the original manifest.
if [[ -f "$BUILD_DIR/meson-logs/install-log.txt" ]]; then
    log "Found build dir manifest; using Meson uninstall ($BUILD_DIR)"
    $SUDO ninja -C "$BUILD_DIR" uninstall
    log "Done."
    exit 0
fi

# 2) Fallback: the build dir is gone, so rebuild the install list from the
#    current source tree and remove exactly those paths.
log "No build dir manifest; reconstructing install list with 'meson introspect'"
command -v meson   >/dev/null || die "meson not found"
command -v python3 >/dev/null || die "python3 not found"

TMP_BUILD="$(mktemp -d)"
trap 'rm -rf "$TMP_BUILD"' EXIT

( cd "$REPO_ROOT" && meson setup "$TMP_BUILD" --prefix="$PREFIX" >/dev/null ) \
    || die "meson configuration failed (build dependencies missing?)"

mapfile -t PATHS < <(meson introspect "$TMP_BUILD" --installed \
    | python3 -c "import sys, json; [print(p) for p in json.load(sys.stdin).values()]")

[[ ${#PATHS[@]} -gt 0 ]] || die "introspection returned no installed paths"

log "Removing ${#PATHS[@]} installed entries under $PREFIX ..."
for p in "${PATHS[@]}"; do
    if [[ -e "$p" || -L "$p" ]]; then
        log "  rm -rf $p"
        $SUDO rm -rf "$p"
    fi
done

# Remove the app's dedicated data dir wholesale (it is MiAZ-only), so nothing
# lingers if a file was left out of the introspected list.
if [[ -d "$PREFIX/share/MiAZ" ]]; then
    $SUDO rm -rf "$PREFIX/share/MiAZ"
fi

# Best-effort cache refresh (mirrors the post-install step).
$SUDO glib-compile-schemas "$PREFIX/share/glib-2.0/schemas" 2>/dev/null || true
$SUDO gtk-update-icon-cache -qtf "$PREFIX/share/icons/hicolor" 2>/dev/null || true
$SUDO update-desktop-database -q "$PREFIX/share/applications" 2>/dev/null || true

log "Done."
