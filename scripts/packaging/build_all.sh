#!/bin/bash
# Build RPM, DEB, Flatpak and AppImage packages for MiAZ and copy them to ./dist.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"

log()     { echo "[build_all] $*"; }
log_ok()  { echo "[build_all] OK: $*"; }
log_err() { echo "[build_all] FAILED: $*" >&2; }
die()     { echo "[build_all] ERROR: $*" >&2; exit 1; }

# True only when every given command is on PATH. Used to skip a package format
# whose toolchain is not installed, instead of attempting it and failing.
have() {
    local cmd
    for cmd in "$@"; do
        command -v "$cmd" &>/dev/null || return 1
    done
    return 0
}

VERSION=$(grep -m1 "version" "$REPO_ROOT/meson.build" \
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/" \
    | sed "s/+.*//")
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"
log "Version: $VERSION"

mkdir -p "$DIST_DIR"
# Wipe previous artifacts so dist/ only contains packages from this run.
log "Cleaning $DIST_DIR/ ..."
find "$DIST_DIR" -mindepth 1 -delete

ERRORS=0

# ── RPM ───────────────────────────────────────────────────────────────────────
log "--- Building RPM package ---"
if ! have rpmbuild; then
    log "rpmbuild not found, skipping RPM build."
elif "$SCRIPT_DIR/rpm/create_rpm.sh"; then
    FOUND=0
    while IFS= read -r pkg; do
        cp "$pkg" "$DIST_DIR/"
        log_ok "$(basename "$pkg") -> dist/"
        FOUND=1
    done < <(find "$HOME/rpmbuild/RPMS" "$HOME/rpmbuild/SRPMS" \
                  -name "miaz*${VERSION}*" 2>/dev/null | sort)
    [[ $FOUND -eq 1 ]] || log_err "RPM built but no output file found"
else
    log_err "RPM build failed"
    ERRORS=$(( ERRORS + 1 ))
fi

# ── DEB ───────────────────────────────────────────────────────────────────────
log "--- Building DEB package ---"
if ! have dpkg-buildpackage && ! have dpkg-deb; then
    log "dpkg-buildpackage and dpkg-deb not found, skipping DEB build."
elif "$SCRIPT_DIR/deb/create_deb.sh"; then
    FOUND=0
    # Manual strategy: output lands in repo root
    # Native strategy: output lands one level above repo root
    for search_dir in "$REPO_ROOT" "$(dirname "$REPO_ROOT")"; do
        while IFS= read -r pkg; do
            cp "$pkg" "$DIST_DIR/"
            log_ok "$(basename "$pkg") -> dist/"
            FOUND=1
        done < <(find "$search_dir" -maxdepth 1 -name "miaz_${VERSION}*.deb" 2>/dev/null | sort)
    done
    [[ $FOUND -eq 1 ]] || log_err "DEB built but no output file found"
else
    log_err "DEB build failed"
    ERRORS=$(( ERRORS + 1 ))
fi

# ── Flatpak ───────────────────────────────────────────────────────────────────
log "--- Building Flatpak package ---"
cd "$REPO_ROOT"
FLATPAK_BUNDLE="$REPO_ROOT/miaz-${VERSION}.flatpak"
if ! have flatpak flatpak-builder ostree; then
    log "flatpak, flatpak-builder or ostree not found, skipping Flatpak build."
elif "$SCRIPT_DIR/flatpak/create_flatpak.sh"; then
    # create_flatpak.sh builds and installs but does not produce a bundle file.
    # Export the build result into a local repo and create a distributable bundle.
    # flatpak build-export refuses to open a partially-initialised OSTree repo
    # (missing config/objects), so re-init it from scratch in that case.
    if [[ ! -f "$REPO_ROOT/repo/config" || ! -d "$REPO_ROOT/repo/objects" ]]; then
        log "Re-initialising OSTree repo at $REPO_ROOT/repo ..."
        rm -rf "$REPO_ROOT/repo"
        ostree --repo="$REPO_ROOT/repo" init --mode=archive-z2
    fi
    log "Exporting flatpak build to local repo..."
    flatpak build-export "$REPO_ROOT/repo" "$REPO_ROOT/builddir_flatpak"
    log "Creating bundle $(basename "$FLATPAK_BUNDLE") ..."
    flatpak build-bundle "$REPO_ROOT/repo" "$FLATPAK_BUNDLE" io.github.t00m.MiAZ
    cp "$FLATPAK_BUNDLE" "$DIST_DIR/"
    log_ok "$(basename "$FLATPAK_BUNDLE") -> dist/"
else
    log_err "Flatpak build failed"
    ERRORS=$(( ERRORS + 1 ))
fi

# ── AppImage ─────────────────────────────────────────────────────────────────
log "--- Building AppImage package ---"
if ! have meson ninja patchelf wget; then
    log "meson, ninja, patchelf or wget not found, skipping AppImage build."
elif "$SCRIPT_DIR/AppImage/build_appimage.sh"; then
    FOUND=0
    while IFS= read -r pkg; do
        cp "$pkg" "$DIST_DIR/"
        log_ok "$(basename "$pkg") -> dist/"
        FOUND=1
    done < <(find "$REPO_ROOT" -maxdepth 1 -name "MiAZ-${VERSION}*.AppImage" 2>/dev/null | sort)
    [[ $FOUND -eq 1 ]] || log_err "AppImage built but no output file found"
else
    log_err "AppImage build failed"
    ERRORS=$(( ERRORS + 1 ))
fi

# ── Install report ────────────────────────────────────────────────────────────
# Emit per-package install instructions for whatever made it into dist/.
write_install_report() {
    local report="$DIST_DIR/INSTALL.txt"
    local rpm deb flatpak appimage

    rpm=$(find "$DIST_DIR" -maxdepth 1 -name 'miaz-*.rpm' ! -name '*.src.rpm' -printf '%f\n' | sort | head -n1)
    deb=$(find "$DIST_DIR" -maxdepth 1 -name 'miaz_*.deb' -printf '%f\n' | sort | head -n1)
    flatpak=$(find "$DIST_DIR" -maxdepth 1 -name 'miaz-*.flatpak' -printf '%f\n' | sort | head -n1)
    appimage=$(find "$DIST_DIR" -maxdepth 1 -iname 'miaz-*.appimage' -printf '%f\n' | sort | head -n1)

    {
        echo "MiAZ ${VERSION}, installation instructions"
        echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
        echo
        echo "This file lists install commands for the packages produced in this"
        echo "directory. Run each command from inside dist/."
        echo

        if [[ -n "$rpm" ]]; then
            echo "RPM (${rpm})"
            echo "    Fedora / RHEL:   sudo dnf install ./${rpm}"
            echo "    openSUSE:        sudo zypper install ./${rpm}"
            echo "    Generic:         sudo rpm -i ${rpm}"
            echo "    Uninstall:       sudo rpm -e miaz"
            echo
        fi
        if [[ -n "$deb" ]]; then
            echo "DEB (${deb})"
            echo "    Debian / Ubuntu: sudo apt install ./${deb}"
            echo "    Generic:         sudo dpkg -i ${deb} && sudo apt-get -f install"
            echo "    Helper script:   scripts/packaging/deb/install_deb.sh"
            echo "                     (installs dependencies, then the latest .deb)"
            echo "    Run:             miaz"
            echo "    Uninstall:       sudo apt remove miaz"
            echo
        fi
        if [[ -n "$flatpak" ]]; then
            echo "Flatpak (${flatpak})"
            echo "    Install:         flatpak install --user ${flatpak}"
            echo "    Run:             flatpak run io.github.t00m.MiAZ"
            echo "    Uninstall:       flatpak uninstall --user io.github.t00m.MiAZ"
            echo
        fi
        if [[ -n "$appimage" ]]; then
            echo "AppImage (${appimage})"
            echo "    Make executable: chmod +x ${appimage}"
            echo "    Run:             ./${appimage}"
            echo "    Uninstall:       rm ${appimage}"
            echo
        fi
        if [[ -z "$rpm$deb$flatpak$appimage" ]]; then
            echo "No packages were produced in this run."
        fi
    } > "$report"
    log_ok "Wrote install report -> $(basename "$report")"
}
write_install_report

# ── Summary ───────────────────────────────────────────────────────────────────
log ""
log "Packages in $DIST_DIR/:"
ls -1 "$DIST_DIR/" | while read -r f; do log "  $f"; done

if [[ $ERRORS -gt 0 ]]; then
    die "$ERRORS package build(s) failed, see output above."
fi
log "All packages built successfully."
