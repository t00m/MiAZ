#!/usr/bin/env bash
# File: install_deb.sh
# Author: Tomás Vírseda
# License: GPL v3
# Description: Install the latest MiAZ Debian package together with its runtime
#              dependencies on a Debian/Ubuntu system.
#
# It does two things:
#   1. Installs the runtime dependencies with apt.
#   2. Installs the most recent miaz_*.deb found in the repository with dpkg.
#
# Run it with a normal user; it calls sudo where root is needed.

set -euo pipefail

# Runtime dependencies, taken from the Depends field in debian/control.
DEPENDENCIES=(
    python3
    python3-gi
    python3-gi-cairo
    gir1.2-gtk-4.0
    gir1.2-adw-1
    libgtk-4-1
    libadwaita-1-0
    libpeas-2-0
    gir1.2-peas-2
    gir1.2-webkit-6.0
    poppler-utils
    tesseract-ocr
    tesseract-ocr-eng
)

# Repository root, two levels up from scripts/packaging/deb/.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Pick the most recently built miaz_*.deb. The build scripts drop the package
# in the repository root and/or in dist/, so look in both and sort by mtime.
DEB="$(find "$REPO_ROOT" "$REPO_ROOT/dist" -maxdepth 1 -name 'miaz_*.deb' \
        -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)"

if [[ -z "$DEB" ]]; then
    echo "No miaz_*.deb found in $REPO_ROOT or $REPO_ROOT/dist." >&2
    echo "Build it first: scripts/packaging/deb/create_deb.sh" >&2
    exit 1
fi

echo "==> Installing runtime dependencies"
sudo apt update
sudo apt install -y "${DEPENDENCIES[@]}"

echo "==> Installing $(basename "$DEB")"
# If a dependency is still missing, apt-get -f install fixes it after dpkg.
sudo dpkg -i "$DEB" || sudo apt-get -f install -y

echo
echo "MiAZ is installed. Run it with:"
echo
echo "    miaz"
echo
