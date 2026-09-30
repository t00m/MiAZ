#!/bin/bash
# Smoke test a MiAZ AppImage on a clean Ubuntu 22.04, the oldest system it
# targets and the one AppImageHub tests on. The container has no GTK, no
# libadwaita and no WebKit, so anything the AppImage takes from the host
# instead of carrying itself shows up here.
#
# It checks what AppImageHub checks first: the application starts and opens a
# window (the first-run assistant, since the container has no repository).
# The screenshot is written next to the AppImage.
#
# Usage: test_appimage.sh [path/to/MiAZ-*.AppImage]
# Environment: CONTAINER_ENGINE (docker or podman), TEST_IMAGE (ubuntu:22.04)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TEST_IMAGE="${TEST_IMAGE:-ubuntu:22.04}"

APPIMAGE="${1:-$(ls -t "$REPO_ROOT"/MiAZ-*-x86_64.AppImage 2>/dev/null | head -n 1)}"
[[ -f "$APPIMAGE" ]] || { echo "No AppImage given or found in $REPO_ROOT" >&2; exit 1; }
APPIMAGE="$(cd "$(dirname "$APPIMAGE")" && pwd)/$(basename "$APPIMAGE")"
NAME="$(basename "$APPIMAGE")"

ENGINE="${CONTAINER_ENGINE:-}"
if [[ -z "$ENGINE" ]]; then
    if command -v podman >/dev/null 2>&1; then ENGINE=podman
    elif command -v docker >/dev/null 2>&1; then ENGINE=docker
    else echo "neither podman nor docker is installed" >&2; exit 1; fi
fi

echo "[test] $NAME on $TEST_IMAGE"
"$ENGINE" run --rm \
    -v "$(dirname "$APPIMAGE")":/work:z \
    -e NAME="$NAME" \
    "$TEST_IMAGE" bash -euo pipefail -c '
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends xvfb x11-utils imagemagick >/dev/null
        # No FUSE in an unprivileged container
        export APPIMAGE_EXTRACT_AND_RUN=1 HOME=/tmp/home DISPLAY=:99
        mkdir -p "$HOME"
        cd /tmp

        echo "[test] miaz --help"
        "/work/$NAME" --help >/tmp/help.txt 2>&1 || { cat /tmp/help.txt; exit 1; }
        grep -q "usage: miaz" /tmp/help.txt || { cat /tmp/help.txt; exit 1; }

        echo "[test] GUI on Xvfb"
        Xvfb :99 -screen 0 800x600x24 >/dev/null 2>&1 &
        sleep 2
        "/work/$NAME" >/tmp/app.log 2>&1 &
        APP=$!
        WINDOW=""
        for i in $(seq 1 40); do
            sleep 1
            if ! kill -0 "$APP" 2>/dev/null; then
                echo "[test] FAIL: MiAZ exited after ${i}s without a window"
                tail -n 40 /tmp/app.log
                exit 1
            fi
            if xwininfo -tree -root | grep -qE "0x.*\": \("; then WINDOW=yes; break; fi
        done
        [ -n "$WINDOW" ] || { echo "[test] FAIL: no window after 40s"; tail -n 40 /tmp/app.log; exit 1; }
        sleep 3
        import -window root "/work/${NAME%.AppImage}-test.png" || true
        xwininfo -tree -root | grep -E "0x.*\": \(" | sed "s/^ */[test] window: /"
        kill "$APP" 2>/dev/null || true
        echo "[test] OK"
    '
