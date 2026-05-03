#!/bin/bash
# Build a .deb package for MiAZ.
#
# Strategy A (Debian/Ubuntu): uses dpkg-buildpackage + debhelper + meson.
# Strategy B (Fedora/other): uses meson DESTDIR install + dpkg-deb directly.
#   Requires only: meson, ninja, dpkg-deb (from the 'dpkg' package on Fedora).
#
# Run from anywhere; the script locates the repo root automatically.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# ── helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[deb] $*"; }
die()  { echo "[deb] ERROR: $*" >&2; exit 1; }

require() {
    for cmd in "$@"; do
        command -v "$cmd" &>/dev/null || die "Required tool not found: $cmd"
    done
}

# ── version ──────────────────────────────────────────────────────────────────
VERSION=$(grep -m1 "version" "$REPO_ROOT/meson.build" \
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/")
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"
log "Version: $VERSION"

DEB_VERSION="${VERSION}-1"
ARCH="all"
OUTPUT_NAME="miaz_${DEB_VERSION}_${ARCH}.deb"

# ── pick strategy ─────────────────────────────────────────────────────────────
if command -v dpkg-buildpackage &>/dev/null && command -v dh &>/dev/null; then
    STRATEGY="native"
    log "Strategy: dpkg-buildpackage (native Debian/Ubuntu toolchain)"
elif command -v dpkg-deb &>/dev/null; then
    STRATEGY="manual"
    log "Strategy: meson DESTDIR install + dpkg-deb (cross-distro)"
else
    die "Neither dpkg-buildpackage nor dpkg-deb found.
  On Fedora:  sudo dnf install dpkg
  On Debian:  sudo apt install dpkg-dev debhelper dh-meson"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Strategy A — native dpkg-buildpackage
# ─────────────────────────────────────────────────────────────────────────────
build_native() {
    require dpkg-buildpackage dh meson ninja desktop-file-validate

    [[ -d "$REPO_ROOT/debian" ]] || die "debian/ directory not found under $REPO_ROOT"

    # Keep debian/changelog version in sync
    DEB_CHANGELOG="$REPO_ROOT/debian/changelog"
    DEB_CUR_VER=$(head -1 "$DEB_CHANGELOG" | sed 's/.*(\(.*\)).*/\1/' | cut -d- -f1)
    if [[ "$DEB_CUR_VER" != "$VERSION" ]]; then
        log "Updating debian/changelog: $DEB_CUR_VER -> $VERSION"
        DEBFULLNAME="${DEBFULLNAME:-Tomás Vírseda}" \
        DEBEMAIL="${DEBEMAIL:-tomasvirseda@gmail.com}" \
        dch --newversion "$DEB_VERSION" --distribution unstable \
            "Update to ${VERSION}" 2>/dev/null \
            || log "WARNING: dch not available — update debian/changelog manually if needed."
    fi

    cd "$REPO_ROOT"
    dpkg-buildpackage -us -uc -b

    PARENT_DIR="$(dirname "$REPO_ROOT")"
    log "Done. Package(s) in $PARENT_DIR/:"
    find "$PARENT_DIR" -maxdepth 1 -name "miaz_${VERSION}*.deb" | sort | while read -r pkg; do
        log "  $pkg"
    done
    log ""
    log "Install with:"
    log "  sudo dpkg -i \$(find $PARENT_DIR -maxdepth 1 -name 'miaz_${VERSION}*.deb' | head -1)"
    log "  sudo apt-get install -f   # resolve any missing dependencies"
}

# ─────────────────────────────────────────────────────────────────────────────
# Strategy B — meson DESTDIR + dpkg-deb
# ─────────────────────────────────────────────────────────────────────────────
build_manual() {
    require meson ninja dpkg-deb

    STAGING="$REPO_ROOT/builddir_deb_staging"
    OUTPUT="$REPO_ROOT/$OUTPUT_NAME"

    log "Installing into staging dir: $STAGING"
    rm -rf "$STAGING" "$REPO_ROOT/builddir_deb"
    meson setup "$REPO_ROOT/builddir_deb" --prefix=/usr -Dprofile=release --wipe
    ninja -C "$REPO_ROOT/builddir_deb"
    DESTDIR="$STAGING" ninja -C "$REPO_ROOT/builddir_deb" install

    # Compute installed size in KB
    INSTALLED_KB=$(du -sk "$STAGING" | cut -f1)

    # Write DEBIAN/control
    mkdir -p "$STAGING/DEBIAN"
    cat > "$STAGING/DEBIAN/control" <<EOF
Package: miaz
Version: $DEB_VERSION
Architecture: $ARCH
Maintainer: Tomás Vírseda <tomasvirseda@gmail.com>
Installed-Size: $INSTALLED_KB
Depends: python3 (>= 3.9), python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, gir1.2-adw-1
Section: utils
Priority: optional
Homepage: https://github.com/t00m/MiAZ
Description: Personal Document Organizer
 MiAZ is a GTK4/Libadwaita desktop application that organises personal
 documents by enforcing a strict 7-field filename convention:
 {date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
 .
 The directory is the database — no external database required.
EOF

    # Write md5sums
    log "Computing md5sums ..."
    (cd "$STAGING" && find usr -type f | sort | xargs md5sum) \
        > "$STAGING/DEBIAN/md5sums"

    # Write postinst / postrm scripts for GSettings schema and icon cache
    cat > "$STAGING/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
glib-compile-schemas /usr/share/glib-2.0/schemas/ || true
update-desktop-database || true
EOF
    chmod 0755 "$STAGING/DEBIAN/postinst"

    cat > "$STAGING/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
glib-compile-schemas /usr/share/glib-2.0/schemas/ || true
update-desktop-database || true
EOF
    chmod 0755 "$STAGING/DEBIAN/postrm"

    # Build the .deb
    log "Building $OUTPUT_NAME ..."
    dpkg-deb --root-owner-group --build "$STAGING" "$OUTPUT"

    rm -rf "$STAGING" "$REPO_ROOT/builddir_deb"

    log "Done: $OUTPUT"
    log ""
    log "Install with:"
    log "  sudo dpkg -i $OUTPUT"
    log "  sudo apt-get install -f   # resolve any missing dependencies"
}

# ── dispatch ──────────────────────────────────────────────────────────────────
case "$STRATEGY" in
    native) build_native ;;
    manual) build_manual ;;
esac
