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

# ── source ───────────────────────────────────────────────────────────────────
# Everything below reads from the export, never from the working tree: the
# sources, debian/ and the version all come from one commit, the same one the
# .rpm is built from. See ../lib/source_export.sh.
source "$SCRIPT_DIR/../lib/source_export.sh"
miaz_prepare_source "$REPO_ROOT" "deb"

VERSION="$MIAZ_SRC_VERSION"
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"

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
# Strategy A: native dpkg-buildpackage
# ─────────────────────────────────────────────────────────────────────────────
build_native() {
    require dpkg-buildpackage dh meson ninja desktop-file-validate

    [[ -d "$MIAZ_SRC_DIR/debian" ]] || die "debian/ directory not found in the exported source"

    # Keep debian/changelog version in sync. This edits the export, not the
    # repository: the working tree is never written to by a build.
    DEB_CHANGELOG="$MIAZ_SRC_DIR/debian/changelog"
    DEB_CUR_VER=$(head -1 "$DEB_CHANGELOG" | sed 's/.*(\(.*\)).*/\1/' | cut -d- -f1)
    if [[ "$DEB_CUR_VER" != "$VERSION" ]]; then
        log "Updating debian/changelog in the export: $DEB_CUR_VER -> $VERSION"
        ( cd "$MIAZ_SRC_DIR" && \
          DEBFULLNAME="${DEBFULLNAME:-Tomás Vírseda}" \
          DEBEMAIL="${DEBEMAIL:-tomasvirseda@gmail.com}" \
          dch --newversion "$DEB_VERSION" --distribution unstable \
              "Update to ${VERSION}" 2>/dev/null ) \
            || log "WARNING: dch not available. debian/changelog keeps version $DEB_CUR_VER."
    fi

    cd "$MIAZ_SRC_DIR"
    dpkg-buildpackage -us -uc -b

    # dpkg-buildpackage writes next to the source tree, which is the export.
    # Move the result where the manual strategy puts it, so callers find the
    # package in one place whichever strategy ran.
    local built
    built=$(find "$(dirname "$MIAZ_SRC_DIR")" -maxdepth 1 -name "miaz_${VERSION}*.deb" | sort | head -1)
    [[ -n "$built" ]] || die "dpkg-buildpackage produced no .deb"
    mv "$built" "$REPO_ROOT/$OUTPUT_NAME"

    log "Done: $REPO_ROOT/$OUTPUT_NAME"
    log ""
    log "Install with:"
    log "  sudo dpkg -i $REPO_ROOT/$OUTPUT_NAME"
    log "  sudo apt-get install -f   # resolve any missing dependencies"
}

# ─────────────────────────────────────────────────────────────────────────────
# Strategy B: meson DESTDIR + dpkg-deb
# ─────────────────────────────────────────────────────────────────────────────
build_manual() {
    require meson ninja dpkg-deb

    # Build and stage inside the export, so nothing here can pick a file up
    # from the working tree and no build directory is left in the repository.
    STAGING="$MIAZ_SRC_DIR/_staging"
    BUILDDIR="$MIAZ_SRC_DIR/_build"
    OUTPUT="$REPO_ROOT/$OUTPUT_NAME"

    log "Installing into staging dir: $STAGING"
    rm -rf "$STAGING" "$BUILDDIR"
    meson setup "$BUILDDIR" "$MIAZ_SRC_DIR" --prefix=/usr -Dprofile=release
    ninja -C "$BUILDDIR"
    DESTDIR="$STAGING" ninja -C "$BUILDDIR" install

    # debhelper does this in the native build. Strategy B uses plain dpkg-deb,
    # so the two files Policy requires (12.5 copyright, 12.7 changelog) have to
    # be installed by hand. Both have to land before the installed size and the
    # md5sums are computed, otherwise they are missing from both.
    DOCDIR="$STAGING/usr/share/doc/miaz"
    mkdir -p "$DOCDIR"
    install -m 0644 "$MIAZ_SRC_DIR/debian/copyright" "$DOCDIR/copyright"
    gzip -9nc "$MIAZ_SRC_DIR/debian/changelog" > "$DOCDIR/changelog.Debian.gz"
    chmod 0644 "$DOCDIR/changelog.Debian.gz"

    # install_subdir copies the source directories as they are, so a working
    # tree that has been run from carries its __pycache__ into the package. The
    # bytecode is built by the host interpreter and is useless on the target
    # anyway. Pruning happens before the size and the md5sums are computed.
    find "$STAGING" -type d -name '__pycache__' -prune -exec rm -rf {} +
    find "$STAGING" -type f -name '*.pyc' -delete

    # Compute installed size in KB
    INSTALLED_KB=$(du -sk "$STAGING" | cut -f1)

    # Write DEBIAN/control
    mkdir -p "$STAGING/DEBIAN"

    # Derive runtime dependencies from debian/control, the single source of
    # truth, so this cross-distro strategy stays in sync with the native
    # dpkg-buildpackage build. dpkg-deb does not expand ${misc:Depends}, so it
    # is dropped. Without this the .deb shipped an incomplete Depends line and
    # the app failed to start on a clean Ubuntu (missing gir1.2-peas-2,
    # gir1.2-webkit-6.0, and others).
    control_field() {
        python3 - "$MIAZ_SRC_DIR/debian/control" "$1" <<'PYEOF'
import re, sys
path, name = sys.argv[1], sys.argv[2]
text = open(path).read()
m = re.search(rf'^{name}:(.*?)(?=^\S+:|\Z)', text, re.M | re.S)
if m:
    parts = [d.strip() for d in m.group(1).replace('\n', ' ').split(',')]
    print(', '.join(d for d in parts if d and 'misc:Depends' not in d))
PYEOF
    }
    MIAZ_DEPENDS="$(control_field Depends)"
    MIAZ_RECOMMENDS="$(control_field Recommends)"
    [ -n "$MIAZ_DEPENDS" ] || die "Could not derive Depends from debian/control"

    {
        echo "Package: miaz"
        echo "Version: $DEB_VERSION"
        echo "Architecture: $ARCH"
        echo "Maintainer: Tomás Vírseda <tomasvirseda@gmail.com>"
        echo "Installed-Size: $INSTALLED_KB"
        echo "Depends: $MIAZ_DEPENDS"
        [ -n "$MIAZ_RECOMMENDS" ] && echo "Recommends: $MIAZ_RECOMMENDS"
        echo "Section: utils"
        echo "Priority: optional"
        echo "Homepage: https://github.com/t00m/MiAZ"
        echo "Description: Personal Document Organizer"
        echo " MiAZ is a GTK4/Libadwaita desktop application that organises personal"
        echo " documents by enforcing a strict 7-field filename convention:"
        echo " {date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}"
        echo " ."
        echo " The directory is the database, no external database required."
    } > "$STAGING/DEBIAN/control"

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

    # The staging and build directories live inside the export, which its owner
    # removes, so there is nothing to clean up in the repository.
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
