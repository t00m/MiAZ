#!/bin/bash
# Build the local flatpak from the working tree and install it for the user.
#
# --disable-cache forces every module to be re-read and rebuilt from sources.
# Without it, flatpak-builder's cache (.flatpak-builder/cache/) may decide the
# `miaz` module hasn't changed and skip the rebuild, leaving the installed
# flatpak with the previous code even though the working tree has new edits.
# The SDK/runtime download cache is independent and is *not* invalidated, so
# this only re-runs our own module builds.
set -euo pipefail

flatpak-builder \
    --force-clean \
    --disable-cache \
    --user --install \
    builddir_flatpak flatpak/io.github.t00m.MiAZ.local.json

echo "----"
echo "To run MiAZ app execute:"
echo " ./scripts/execution/linux/flatpak/exec_flatpak_miaz.sh" 
echo "----"

