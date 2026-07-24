#!/bin/bash
# Remove a user-space MiAZ install (meson --prefix=~/.local) and refresh the
# caches that still reference it, so a leftover user install no longer shadows a
# system package (deb/rpm) on PATH.
#
# This removes the installed app files only. It does NOT touch ~/.MiAZ, which
# holds your repositories and configuration.
set -u

PREFIX="$HOME/.local"
DATADIR="${XDG_DATA_HOME:-$HOME/.local/share}"
ICON_DIR="$DATADIR/icons/hicolor"
SCHEMA_DIR="$DATADIR/glib-2.0/schemas"
APP_DIR="$DATADIR/applications"

# Remove every file the user install placed. This is done by path, not via
# `ninja uninstall`, so it also works when the meson build dir is gone, and it
# clears the plugins directory that ninja leaves behind (it holds files ninja
# did not install). All targets are MiAZ-specific.
echo "Removing user-installed MiAZ files ..."
rm -f  "$PREFIX/bin/miaz"
rm -rf "$DATADIR/MiAZ"
rm -f  "$APP_DIR/io.github.t00m.MiAZ.desktop"
rm -f  "$SCHEMA_DIR/io.github.t00m.MiAZ.gschema.xml"
rm -f  "$DATADIR/metainfo/io.github.t00m.MiAZ.metainfo.xml"
[ -d "$DATADIR/icons" ] && find "$DATADIR/icons" -name 'io.github.t00m.MiAZ*.svg' -delete 2>/dev/null
[ -d "$DATADIR/locale" ] && find "$DATADIR/locale" -name 'miaz.mo' -delete 2>/dev/null

# Regenerate the binary caches so they no longer point at MiAZ. Without this,
# icon-theme.cache, gschemas.compiled and the desktop database keep stale MiAZ
# entries even after the files are gone.
echo "Refreshing caches ..."
if command -v gtk-update-icon-cache >/dev/null 2>&1 && [ -d "$ICON_DIR" ]; then
    gtk-update-icon-cache -f -t "$ICON_DIR" >/dev/null 2>&1 || true
fi
if command -v glib-compile-schemas >/dev/null 2>&1 && [ -d "$SCHEMA_DIR" ]; then
    glib-compile-schemas "$SCHEMA_DIR" >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1 && [ -d "$APP_DIR" ]; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "Done. Your repositories and config in ~/.MiAZ were left untouched."
echo "miaz now resolves to: $(command -v miaz || echo '(not on PATH)')"
