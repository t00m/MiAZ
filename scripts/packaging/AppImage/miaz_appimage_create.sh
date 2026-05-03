#!/bin/bash
# Convenience wrapper — delegates to build_appimage.sh.
# Kept for backwards compatibility with any existing automation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/build_appimage.sh" "$@"
