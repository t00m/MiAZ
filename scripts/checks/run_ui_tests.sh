#!/bin/bash
# Run the UI tests: the real application, driven in process.
#
# They need a display and a repository, so they are not part of the main suite.
# This script gives them both, throws the repository away afterwards, and never
# touches your own ~/.MiAZ: HOME is pointed at a temporary directory before
# Python starts, which is the only moment early enough to matter.
#
# Usage:
#   scripts/checks/run_ui_tests.sh [pytest arguments]
#
#   --keep      leave the sandbox behind and print where it is
#   --headless  start a virtual display even when one is available
#   --shuffle   randomise the order instead of running in file order
#
# File order is the default on purpose. These tests drive one application for
# the whole run, so the order is part of what they are: tests/ui/test_ui_history
# records git history its later tests read back. Shuffling also triples the wall
# time, because repository switches and review-mode toggles stop batching:
# 23 minutes against 8. --shuffle is for the occasional check that a test is not
# quietly leaning on one that ran before it.
#
# With no display and no headless tool it says so and exits 2, rather than
# failing 40 tests for the same reason.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

log() { echo "[uitests] $*"; }
die() { echo "[uitests] ERROR: $*" >&2; exit 2; }

KEEP=0
FORCE_HEADLESS=0
SHUFFLE=0
PYTEST_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep)     KEEP=1; shift ;;
        --headless) FORCE_HEADLESS=1; shift ;;
        --shuffle)  SHUFFLE=1; shift ;;
        -h|--help)  sed -n '2,24p' "$0"; exit 0 ;;
        *)          PYTEST_ARGS+=("$1"); shift ;;
    esac
done

# ── display ──────────────────────────────────────────────────────────────────
XVFB_PID=""
cleanup() {
    [[ -n "$XVFB_PID" ]] && kill "$XVFB_PID" 2>/dev/null
    if [[ $KEEP -eq 1 ]]; then
        log "sandbox kept at $SANDBOX"
    else
        rm -rf "$SANDBOX"
    fi
}

have_display() {
    [[ -n "${WAYLAND_DISPLAY:-}" || -n "${DISPLAY:-}" ]]
}

if [[ $FORCE_HEADLESS -eq 1 ]] || ! have_display; then
    if command -v Xvfb >/dev/null; then
        log "starting Xvfb on :99"
        Xvfb :99 -screen 0 1280x1024x24 >/dev/null 2>&1 &
        XVFB_PID=$!
        sleep 1
        export DISPLAY=:99
        unset WAYLAND_DISPLAY
        export GDK_BACKEND=x11
    else
        die "no display and no Xvfb. Install xorg-x11-server-Xvfb (Fedora) or
  xvfb (Debian/Ubuntu), or run this from a desktop session."
    fi
fi

# ── sandbox ──────────────────────────────────────────────────────────────────
SANDBOX="$(mktemp -d -t miaz-ui-XXXXXXXX)"
trap cleanup EXIT

log "sandbox: $SANDBOX"
log "display: ${WAYLAND_DISPLAY:-${DISPLAY:-none}}"

# HOME decides where MiAZ.env puts everything, and it is read when that module
# is imported, so it has to be set before pytest starts rather than in a
# fixture. The repositories themselves are seeded by tests/ui/conftest.py.
cd "$REPO_ROOT"

# Resolve the user site directory while HOME is still the real one: pytest is
# often installed there, and moving HOME would hide it.
# CI runs a venv interpreter; a desktop run uses whatever python is on PATH.
PYTEST="${PYTEST:-python}"
USER_SITE="$("$PYTEST" -m site --user-site 2>/dev/null || true)"

# Run what the caller asked for, or everything when they asked for nothing.
# Appending tests/ui unconditionally made a named file run the whole directory.
TARGETS=()
for arg in "${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}"; do
    [[ "$arg" == tests/* || -e "$arg" ]] && TARGETS+=("$arg")
done
[[ ${#TARGETS[@]} -eq 0 ]] && PYTEST_ARGS=("tests/ui" "${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}")

# pytest-randomly shuffles as soon as it is installed, so file order has to be
# asked for rather than assumed. Harmless when the plugin is absent.
ORDER=(-p no:randomly)
[[ $SHUFFLE -eq 1 ]] && ORDER=()

HOME="$SANDBOX" \
MIAZ_UI_SANDBOX=1 \
PYTHONPATH="$REPO_ROOT${USER_SITE:+:$USER_SITE}" \
    "$PYTEST" -m pytest -p no:cacheprovider \
    "${ORDER[@]+"${ORDER[@]}"}" "${PYTEST_ARGS[@]}"
STATUS=$?

if [[ $STATUS -eq 0 ]]; then
    log "UI tests passed"
else
    log "UI tests failed (exit $STATUS)"
fi
exit $STATUS
