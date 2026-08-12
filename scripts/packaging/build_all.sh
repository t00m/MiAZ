#!/bin/bash
# Build RPM, DEB, Flatpak and AppImage packages for MiAZ and copy them to ./dist.
#
# Every format is built from one export of one commit, so the packages of a run
# always carry the same version and the same files.
#
# Usage:
#   build_all.sh                 build the current commit (HEAD)
#   build_all.sh --pushed        fetch, then build the last commit pushed to the
#                                branch this one tracks
#   build_all.sh --ref REF       build any tag, branch or SHA
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

# ── arguments ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pushed)  export MIAZ_BUILD_REF="pushed"; shift ;;
        --ref)     export MIAZ_BUILD_REF="$2"; shift 2 ;;
        -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
        *)         die "Unknown option: $1" ;;
    esac
done

# ── one export for every format ──────────────────────────────────────────────
# The individual build scripts each export their own commit when run alone.
# Here they are handed one shared export instead, which is what guarantees that
# the .rpm and the .deb of a single run come from the same tree.
source "$SCRIPT_DIR/lib/source_export.sh"
miaz_prepare_source "$REPO_ROOT" "build_all"
export MIAZ_SOURCE_DIR="$MIAZ_SRC_DIR"
export MIAZ_SOURCE_COMMIT="$MIAZ_SRC_COMMIT"

VERSION_FULL="$MIAZ_SRC_VERSION"
[[ -n "$VERSION_FULL" ]] || die "Could not read version from meson.build"
# VERSION_FULL includes the build counter (e.g. 0.1.50+build.12) and matches the
# DEB filename. VERSION drops the suffix and matches the AppImage and Flatpak
# filenames. The rpm splits the two, so its artifacts are matched by
# VERSION-BUILD_COUNTER: matching on the version alone would copy every release
# of it left in ~/rpmbuild from earlier runs, newest or not.
VERSION="${VERSION_FULL%%+*}"
if [[ "$VERSION_FULL" == *"+build."* ]]; then
    BUILD_COUNTER="${VERSION_FULL##*+build.}"
else
    BUILD_COUNTER="1"
fi
log "Version: $VERSION_FULL"

mkdir -p "$DIST_DIR"
# Wipe previous artifacts so dist/ only contains packages from this run.
log "Cleaning $DIST_DIR/ and previous build leftovers ..."
find "$DIST_DIR" -mindepth 1 -delete
clean_build_tree

# Per-format build logs, so a failed build points at its full output.
LOG_DIR="$DIST_DIR/logs"
mkdir -p "$LOG_DIR"

# The plugin requirements manifest used to be refreshed here. It is no longer
# installed into the packages (nothing reads it; the app collects requirements
# from each plugin's own requirements.txt), and a build must not write into the
# working tree. Run scripts/devel/collect_plugin_requirements.py by hand if you
# want the local copy refreshed.

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
                  -name "miaz-${VERSION}-${BUILD_COUNTER}.*" 2>/dev/null | sort)
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

# ── Verification ──────────────────────────────────────────────────────────────
# Built is not the same as correct. --no-container keeps this to a few seconds;
# run scripts/checks/verify_packages.sh by hand before a release to add lintian
# and the dependency resolution against Debian and Ubuntu.
log ""
log "Verifying packages ..."
"$REPO_ROOT/scripts/checks/verify_packages.sh" --no-container "$DIST_DIR" \
    || die "Package verification failed, see output above."

log "All packages built successfully."
