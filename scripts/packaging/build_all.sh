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

# Remove the intermediate build/staging directories and the stray package files
# the individual build scripts drop in the repo root (and, for the native deb
# strategy, one directory above it). dist/ keeps the final packages, so this only
# clears build leftovers. Run before building (clean slate, no stale package gets
# copied) and after (clean tree). All targets are gitignored build artifacts.
clean_build_tree() {
    rm -rf \
        "$REPO_ROOT/builddir_deb" \
        "$REPO_ROOT/builddir_deb_staging" \
        "$REPO_ROOT/builddir_appimage" \
        "$REPO_ROOT/builddir_flatpak" \
        "$REPO_ROOT/AppDir" \
        "$REPO_ROOT/repo" \
        "$REPO_ROOT/squashfs-root"
    rm -f \
        "$REPO_ROOT"/miaz_*.deb \
        "$REPO_ROOT"/miaz-*.flatpak \
        "$REPO_ROOT"/MiAZ-*.AppImage \
        "$REPO_ROOT"/miaz-*.tar.gz
    # dpkg-buildpackage (native strategy) writes its outputs one level up.
    local parent
    parent="$(dirname "$REPO_ROOT")"
    rm -f \
        "$parent"/miaz_*.deb \
        "$parent"/miaz_*.buildinfo \
        "$parent"/miaz_*.changes \
        "$parent"/miaz_*.dsc \
        "$parent"/miaz_*.tar.*
}

VERSION_FULL=$(grep -m1 "version" "$REPO_ROOT/meson.build" \
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/")
[[ -n "$VERSION_FULL" ]] || die "Could not read version from meson.build"
# VERSION_FULL includes the build number (e.g. 0.1.30+build.21) and matches the
# RPM/DEB filenames. VERSION drops the +build.N suffix and matches the
# AppImage/Flatpak filenames. Using VERSION_FULL for the RPM/DEB copy avoids
# picking up stale build.N packages left in ~/rpmbuild from earlier runs.
VERSION="${VERSION_FULL%%+*}"
log "Version: $VERSION_FULL"

mkdir -p "$DIST_DIR"
# Wipe previous artifacts so dist/ only contains packages from this run.
log "Cleaning $DIST_DIR/ and previous build leftovers ..."
find "$DIST_DIR" -mindepth 1 -delete
clean_build_tree

# Per-format build logs, so a failed build points at its full output.
LOG_DIR="$DIST_DIR/logs"
mkdir -p "$LOG_DIR"

# Refresh the plugin external-libraries manifest so packages ship it in sync
# with each plugin's requirements.txt.
log "Collecting plugin requirements ..."
python3 "$REPO_ROOT/scripts/devel/collect_plugin_requirements.py" \
    || log_err "Could not collect plugin requirements"

FAILED=()

# ── RPM ───────────────────────────────────────────────────────────────────────
log "--- Building RPM package ---"
if ! have rpmbuild; then
    log "rpmbuild not found, skipping RPM build."
elif "$SCRIPT_DIR/rpm/create_rpm.sh" 2>&1 | tee "$LOG_DIR/rpm.log"; then
    FOUND=0
    while IFS= read -r pkg; do
        cp "$pkg" "$DIST_DIR/"
        log_ok "$(basename "$pkg") -> dist/"
        FOUND=1
    done < <(find "$HOME/rpmbuild/RPMS" "$HOME/rpmbuild/SRPMS" \
                  -name "miaz*${VERSION_FULL}*" 2>/dev/null | sort)
    [[ $FOUND -eq 1 ]] || { log_err "RPM built but no output file found"; FAILED+=("RPM"); }
else
    log_err "RPM build failed, see $LOG_DIR/rpm.log"
    FAILED+=("RPM")
fi

# ── DEB ───────────────────────────────────────────────────────────────────────
log "--- Building DEB package ---"
if ! have dpkg-buildpackage && ! have dpkg-deb; then
    log "dpkg-buildpackage and dpkg-deb not found, skipping DEB build."
elif "$SCRIPT_DIR/deb/create_deb.sh" 2>&1 | tee "$LOG_DIR/deb.log"; then
    FOUND=0
    # Manual strategy: output lands in repo root
    # Native strategy: output lands one level above repo root
    for search_dir in "$REPO_ROOT" "$(dirname "$REPO_ROOT")"; do
        while IFS= read -r pkg; do
            cp "$pkg" "$DIST_DIR/"
            log_ok "$(basename "$pkg") -> dist/"
            FOUND=1
        done < <(find "$search_dir" -maxdepth 1 -name "miaz_${VERSION_FULL}*.deb" 2>/dev/null | sort)
    done
    [[ $FOUND -eq 1 ]] || { log_err "DEB built but no output file found"; FAILED+=("DEB"); }
else
    log_err "DEB build failed, see $LOG_DIR/deb.log"
    FAILED+=("DEB")
fi

# ── Flatpak ───────────────────────────────────────────────────────────────────
# Flatpak packaging is deprecated on purpose (see
# docs/PACKAGING-FLATPAK-DEPRECATED.md): the sandbox cannot reach the host CLI
# tools that plugins need (ocrmypdf for OCR, scanimage for the scanner), so
# those features do not work in a Flatpak build. The build steps are kept below
# for reference; set MIAZ_ALLOW_FLATPAK=1 to force it, otherwise it is skipped.
log "--- Flatpak package (deprecated, skipped) ---"
cd "$REPO_ROOT"
FLATPAK_BUNDLE="$REPO_ROOT/miaz-${VERSION}.flatpak"
if [[ -z "${MIAZ_ALLOW_FLATPAK:-}" ]]; then
    log "Flatpak build is deprecated on purpose and skipped. Set MIAZ_ALLOW_FLATPAK=1 to force it."
elif ! have flatpak flatpak-builder ostree; then
    log "flatpak, flatpak-builder or ostree not found, skipping Flatpak build."
elif "$SCRIPT_DIR/flatpak/create_flatpak.sh" 2>&1 | tee "$LOG_DIR/flatpak.log"; then
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
    log_err "Flatpak build failed, see $LOG_DIR/flatpak.log"
    FAILED+=("Flatpak")
fi

# ── AppImage ─────────────────────────────────────────────────────────────────
log "--- Building AppImage package ---"
if ! have meson ninja patchelf wget; then
    log "meson, ninja, patchelf or wget not found, skipping AppImage build."
elif "$SCRIPT_DIR/AppImage/build_appimage.sh" 2>&1 | tee "$LOG_DIR/appimage.log"; then
    FOUND=0
    while IFS= read -r pkg; do
        cp "$pkg" "$DIST_DIR/"
        log_ok "$(basename "$pkg") -> dist/"
        FOUND=1
    done < <(find "$REPO_ROOT" -maxdepth 1 -name "MiAZ-${VERSION}*.AppImage" 2>/dev/null | sort)
    [[ $FOUND -eq 1 ]] || { log_err "AppImage built but no output file found"; FAILED+=("AppImage"); }
else
    log_err "AppImage build failed, see $LOG_DIR/appimage.log"
    FAILED+=("AppImage")
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

# ── Cleanup ───────────────────────────────────────────────────────────────────
# Packages are now in dist/; remove the build dirs and stray root-level copies.
log "Cleaning build tree ..."
clean_build_tree

# ── Summary ───────────────────────────────────────────────────────────────────
log ""
log "Packages in $DIST_DIR/:"
ls -1 "$DIST_DIR/" | while read -r f; do log "  $f"; done

if [[ ${#FAILED[@]} -gt 0 ]]; then
    log ""
    log_err "Failed package(s): ${FAILED[*]}"
    die "${#FAILED[@]} package build(s) failed (${FAILED[*]}), see output above."
fi
log "All packages built successfully."
