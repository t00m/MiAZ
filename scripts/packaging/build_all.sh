#!/bin/bash
# Build RPM, DEB, and Flatpak packages for MiAZ and copy them to ./dist.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"

log()     { echo "[build_all] $*"; }
log_ok()  { echo "[build_all] OK: $*"; }
log_err() { echo "[build_all] FAILED: $*" >&2; }
die()     { echo "[build_all] ERROR: $*" >&2; exit 1; }

VERSION=$(grep -m1 "version" "$REPO_ROOT/meson.build" \
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/")
[[ -n "$VERSION" ]] || die "Could not read version from meson.build"
log "Version: $VERSION"

mkdir -p "$DIST_DIR"

ERRORS=0

# ── RPM ───────────────────────────────────────────────────────────────────────
log "--- Building RPM package ---"
if "$SCRIPT_DIR/rpm/create_rpm.sh"; then
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
if "$SCRIPT_DIR/deb/create_deb.sh"; then
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
if "$SCRIPT_DIR/flatpak/create_flatpak.sh"; then
    # create_flatpak.sh builds and installs but does not produce a bundle file.
    # Export the build result into a local repo and create a distributable bundle.
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

# ── Summary ───────────────────────────────────────────────────────────────────
log ""
log "Packages in $DIST_DIR/:"
ls -1 "$DIST_DIR/" | while read -r f; do log "  $f"; done

if [[ $ERRORS -gt 0 ]]; then
    die "$ERRORS package build(s) failed — see output above."
fi
log "All packages built successfully."
