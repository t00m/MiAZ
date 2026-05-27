#!/bin/sh
# Update the .pot template and merge it into every .po file.
#
# Wraps the Meson targets miaz-pot and miaz-update-po, then reports the
# completion ratio for every language present under po/.
#
# Override the build directory with MIAZ_BUILDDIR if needed:
#   MIAZ_BUILDDIR=builddir_user ./scripts/i18n/update_translations.sh

set -e

BUILDDIR="${MIAZ_BUILDDIR:-builddir_user}"

if [ ! -d "$BUILDDIR" ]; then
    echo "Build directory '$BUILDDIR' not found." >&2
    echo "Run: meson setup $BUILDDIR --prefix=\"\$HOME/.local\"" >&2
    exit 1
fi

echo "==> Extracting strings to po/miaz.pot"
meson compile -C "$BUILDDIR" miaz-pot

echo "==> Merging template into existing .po files"
meson compile -C "$BUILDDIR" miaz-update-po

echo "==> Translation status:"
for po in po/*.po; do
    [ -f "$po" ] || continue
    lang=$(basename "$po" .po)
    printf "  %-10s " "$lang"
    msgfmt --statistics -o /dev/null "$po" 2>&1
done
