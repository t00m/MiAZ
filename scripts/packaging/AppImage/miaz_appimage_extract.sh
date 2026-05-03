#!/bin/bash
# Extract the MiAZ AppImage to a local squashfs-root/ directory.
# Usage: ./miaz_appimage_extract.sh [path/to/MiAZ-*.AppImage]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ $# -ge 1 ]]; then
    APPIMAGE="$1"
else
    # Auto-detect the newest AppImage in the repo root
    APPIMAGE=$(find "$REPO_ROOT" -maxdepth 1 -name "MiAZ-*.AppImage" \
        | sort -V | tail -1)
fi

[[ -n "$APPIMAGE" && -f "$APPIMAGE" ]] \
    || { echo "ERROR: No MiAZ AppImage found. Pass the path as an argument." >&2; exit 1; }

echo "[appimage] Extracting: $APPIMAGE"
cd "$REPO_ROOT"
"$APPIMAGE" --appimage-extract
echo "[appimage] Done. Contents are in: $REPO_ROOT/squashfs-root/"
