#!/bin/bash
# Build a portable, self-contained AppImage for MiAZ.
#
# The AppImage carries its whole stack: Python, PyGObject, GTK 4, libadwaita,
# libpeas 2, WebKitGTK 6.0, libsecret, poppler-utils, tesseract, and the glibc
# and dynamic linker they were built against. It needs from the host only a
# kernel, FUSE (or --appimage-extract-and-run), a display and the system CA
# certificates. test_appimage.sh checks it on Ubuntu 22.04, the system
# AppImageHub tests on.
#
# The stack comes from Ubuntu 26.04, so the build runs in a throwaway
# ubuntu:26.04 container (docker or podman) and your system is never touched.
# The work happens in build_in_container.sh; this script only starts the
# container and hands it the source tree.
#
# Output: MiAZ-<version>-x86_64.AppImage and its .zsync in the repository root.
#
# Environment:
#   CONTAINER_ENGINE  docker or podman (default: whichever is installed)
#   BASE_IMAGE        default ubuntu:26.04
#   OUTPUT_DIR        default: the repository root
#   CONTAINER_RUN_ARGS  extra arguments for "run", split on spaces (for example
#                     "--network host -e HTTPS_PROXY" behind a proxy)
#   MIAZ_WEBKIT_SANDBOX_FALLBACK=1  ship webkit-sandbox.hook (off by default;
#                     read the hook before turning it on)
#
# Run from anywhere; the script finds the repository root itself.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BASE_IMAGE="${BASE_IMAGE:-ubuntu:26.04}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT}"

log() { echo "[appimage] $*"; }
die() { echo "[appimage] ERROR: $*" >&2; exit 1; }

ENGINE="${CONTAINER_ENGINE:-}"
if [[ -z "$ENGINE" ]]; then
    if command -v podman >/dev/null 2>&1; then ENGINE=podman
    elif command -v docker >/dev/null 2>&1; then ENGINE=docker
    else die "neither podman nor docker is installed"; fi
fi
command -v "$ENGINE" >/dev/null 2>&1 || die "$ENGINE is not installed"

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

# The container runs as root. Rootless podman maps that root to you, so its
# files are already yours; docker's are root's, so the build hands them back.
OWNER=""
[[ "$ENGINE" == docker ]] && OWNER="$(id -u):$(id -g)"

# The source is mounted read only: the build copies it before touching it.
# :z relabels the mounts for SELinux hosts (Fedora, RHEL); others ignore it.
log "Building in $BASE_IMAGE with $ENGINE ..."
# shellcheck disable=SC2086  # CONTAINER_RUN_ARGS is split on purpose
"$ENGINE" run --rm ${CONTAINER_RUN_ARGS:-} \
    -e OUTPUT_OWNER="$OWNER" \
    -e MIAZ_WEBKIT_SANDBOX_FALLBACK="${MIAZ_WEBKIT_SANDBOX_FALLBACK:-0}" \
    -v "$REPO_ROOT":/src:ro,z \
    -v "$OUTPUT_DIR":/out:z \
    "$BASE_IMAGE" \
    bash /src/scripts/packaging/AppImage/build_in_container.sh /src /out

FOUND="$(ls -t "$OUTPUT_DIR"/MiAZ-*-x86_64.AppImage 2>/dev/null | head -n 1)"
[[ -n "$FOUND" ]] || die "no AppImage was produced, see the output above"
log "Done: $FOUND"
log "Smoke test on Ubuntu 22.04: $SCRIPT_DIR/test_appimage.sh $FOUND"
