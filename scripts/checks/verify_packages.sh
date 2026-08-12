#!/bin/bash
# Verify the .rpm and .deb packages without installing them on a target system.
#
# Three layers:
#   1. Structural  metadata, payload, desktop file, metainfo, schema, symlinks.
#                  Runs natively, needs no container.
#   2. Policy      rpmlint natively; lintian natively if present, in a container
#                  otherwise.
#   3. Resolution  'apt-get install --simulate' against a real archive, in a
#                  throwaway container. This is the only way to prove that the
#                  Depends names exist in the target release.
#
# Usage:
#   scripts/checks/verify_packages.sh [OPTIONS] [DIR]
#
#   DIR                Directory holding the packages (default: <repo>/dist)
#   --rpm FILE         Check this rpm instead of the newest one in DIR
#   --deb FILE         Check this deb instead of the newest one in DIR
#   --no-container     Skip everything that needs podman or docker
#   --images "A B"     Images for the resolution layer
#                      (default: debian:stable-slim ubuntu:24.04)
#
# Exit status is 1 when any check fails. Warnings do not fail the run.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

log()  { echo "[pkgcheck] $*"; }
die()  { echo "[pkgcheck] ERROR: $*" >&2; exit 2; }

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
SKIP_COUNT=0

pass() { printf '  PASS  %s\n' "$*"; PASS_COUNT=$((PASS_COUNT + 1)); }
warn() { printf '  WARN  %s\n' "$*"; WARN_COUNT=$((WARN_COUNT + 1)); }
skip() { printf '  SKIP  %s\n' "$*"; SKIP_COUNT=$((SKIP_COUNT + 1)); }
fail() { printf '  FAIL  %s\n' "$*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Print at most $2 lines of $1, indented, so a check that fails says why.
detail() {
    local text="$1" limit="${2:-10}"
    [[ -z "$text" ]] && return 0
    echo "$text" | head -"$limit" | sed 's/^/        /'
}

section() { printf '\n== %s ==\n' "$*"; }

have() { command -v "$1" &>/dev/null; }

# ── arguments ────────────────────────────────────────────────────────────────
PKG_DIR="$REPO_ROOT/dist"
RPM_FILE=""
DEB_FILE=""
USE_CONTAINER=1
IMAGES="debian:stable-slim ubuntu:24.04"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rpm)          RPM_FILE="$2"; shift 2 ;;
        --deb)          DEB_FILE="$2"; shift 2 ;;
        --no-container) USE_CONTAINER=0; shift ;;
        --images)       IMAGES="$2"; shift 2 ;;
        -h|--help)      sed -n '2,26p' "$0"; exit 0 ;;
        -*)             die "Unknown option: $1" ;;
        *)              PKG_DIR="$1"; shift ;;
    esac
done

# Newest match for $1, dropping anything matching $2. The source rpm is built
# alongside the binary one and is newer as often as not, so it has to go before
# the head, not after it.
newest() { ls -t "$PKG_DIR"/$1 2>/dev/null | grep -Ev "${2:-^$}" | head -1; }

[[ -n "$RPM_FILE" ]] || RPM_FILE="$(newest '*.rpm' '\.src\.rpm$')"
[[ -n "$DEB_FILE" ]] || DEB_FILE="$(newest '*.deb')"

[[ -n "$RPM_FILE$DEB_FILE" ]] || die "No .rpm or .deb found in $PKG_DIR"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

VERSION=$(grep -m1 "version" "$REPO_ROOT/meson.build" \
    | sed "s/.*version.*: *'\([^']*\)'.*/\1/")

# The two formats split the version differently. The deb carries it whole
# (0.1.50+build.13-1); the rpm keeps the release version in Version: and the
# build counter in Release: (0.1.50-13), which is what keeps its %changelog
# coherent with the package.
BASE_VERSION="${VERSION%%+*}"
if [[ "$VERSION" == *"+build."* ]]; then
    BUILD_COUNTER="${VERSION##*+build.}"
else
    BUILD_COUNTER="1"
fi

log "Repository version: $VERSION"
[[ -n "$RPM_FILE" ]] && log "rpm: $(basename "$RPM_FILE")"
[[ -n "$DEB_FILE" ]] && log "deb: $(basename "$DEB_FILE")"

CONTAINER=""
if [[ $USE_CONTAINER -eq 1 ]]; then
    for engine in podman docker; do
        have "$engine" && { CONTAINER="$engine"; break; }
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: payload checks shared by both formats
# ─────────────────────────────────────────────────────────────────────────────

# $1 extracted root, $2 label for the messages
check_payload() {
    local root="$1" label="$2" out

    out=$(find "$root" -xtype l -printf '%p -> %l\n' | sed "s#$root##")
    if [[ -z "$out" ]]; then
        pass "$label: no dangling symlinks"
    else
        fail "$label: dangling symlinks"
        detail "$out"
    fi

    out=$(find "$root" -name '__pycache__' -o -name '*.pyc' | sed "s#$root##")
    if [[ -z "$out" ]]; then
        pass "$label: no compiled bytecode"
    else
        fail "$label: ships $(echo "$out" | grep -c '\.pyc$') .pyc files in $(echo "$out" | grep -c '__pycache__$') __pycache__ directories"
        detail "$out" 5
    fi

    local desktop
    desktop=$(find "$root" -path '*/applications/*.desktop' | head -1)
    if [[ -z "$desktop" ]]; then
        warn "$label: no .desktop file in the payload"
    elif out=$(desktop-file-validate "$desktop" 2>&1); then
        pass "$label: desktop file valid"
    else
        fail "$label: desktop file invalid"
        detail "$out"
    fi

    local metainfo
    metainfo=$(find "$root" -path '*/metainfo/*.xml' | head -1)
    if [[ -z "$metainfo" ]]; then
        warn "$label: no metainfo file in the payload"
    elif ! have appstreamcli; then
        skip "$label: metainfo (appstreamcli not installed)"
    elif out=$(appstreamcli validate --no-net "$metainfo" 2>&1); then
        pass "$label: metainfo valid"
    else
        fail "$label: metainfo invalid"
        detail "$out"
    fi

    local schemadir
    schemadir=$(find "$root" -type d -path '*/glib-2.0/schemas' | head -1)
    if [[ -z "$schemadir" ]]; then
        warn "$label: no GSettings schema in the payload"
    elif ! have glib-compile-schemas; then
        skip "$label: schema (glib-compile-schemas not installed)"
    elif out=$(glib-compile-schemas --dry-run "$schemadir" 2>&1); then
        pass "$label: GSettings schema compiles"
    else
        fail "$label: GSettings schema does not compile"
        detail "$out"
    fi

    # A module carrying a shebang but no execute bit is either mislabelled or
    # missing the bit. rpmlint reports one error per file for this.
    out=$(find "$root" -name '*.py' ! -perm -u+x -exec grep -l '^#!' {} + 2>/dev/null | sed "s#$root##")
    if [[ -z "$out" ]]; then
        pass "$label: no non-executable scripts with a shebang"
    else
        fail "$label: $(echo "$out" | wc -l) non-executable .py files carry a shebang"
        detail "$out" 5
    fi

    # /usr/bin/python does not exist on Debian, and is not guaranteed anywhere.
    out=$(grep -rl '^#!/usr/bin/python$' "$root" 2>/dev/null | sed "s#$root##")
    if [[ -z "$out" ]]; then
        pass "$label: no '#!/usr/bin/python' shebangs"
    else
        fail "$label: '#!/usr/bin/python' is not a valid interpreter path"
        detail "$out"
    fi

    out=$(find "$root" -path '*/icons/*/scalable/*' -type f \
        \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
           -o -iname '*.gif' -o -iname '*.xpm' -o -iname '*.ico' \) \
        | sed "s#$root##")
    if [[ -z "$out" ]]; then
        pass "$label: scalable icon directories hold only SVG"
    else
        warn "$label: raster images in a scalable icon directory"
        detail "$out"
    fi

    if have python3; then
        if out=$(PYTHONPYCACHEPREFIX="$WORK/pycache" python3 -m compileall -q "$root" 2>&1); then
            pass "$label: every .py file compiles"
        else
            fail "$label: syntax errors in the payload"
            detail "$out"
        fi
    else
        skip "$label: python syntax (python3 not installed)"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# RPM
# ─────────────────────────────────────────────────────────────────────────────
check_rpm() {
    section "RPM: $(basename "$RPM_FILE")"
    have rpm || { skip "rpm not installed"; return; }

    local out pkgver pkgrel
    pkgver=$(rpm -qp --qf '%{VERSION}' "$RPM_FILE" 2>/dev/null)
    pkgrel=$(rpm -qp --qf '%{RELEASE}' "$RPM_FILE" 2>/dev/null)
    if [[ "$pkgver" == "$BASE_VERSION" && "$pkgrel" == "$BUILD_COUNTER"* ]]; then
        pass "version-release matches meson.build ($BASE_VERSION-$BUILD_COUNTER)"
    else
        # Packages are built from a commit, the working tree may have moved on.
        warn "package is $pkgver-$pkgrel, the working tree says $BASE_VERSION-$BUILD_COUNTER (built from another commit?)"
    fi

    if out=$(rpm -K "$RPM_FILE" 2>&1); then
        case "$out" in
            *"digests signatures OK"*) pass "signature and digests OK" ;;
            *"digests OK"*)            warn "unsigned package (digests OK)" ;;
            *)                         warn "$out" ;;
        esac
    else
        fail "digest check failed"
        detail "$out"
    fi

    # The %changelog version has to name the version being shipped, otherwise
    # the package and its history disagree about what this build is.
    local changelog_ver
    changelog_ver=$(rpm -qp --qf '%{CHANGELOGNAME}\n' "$RPM_FILE" 2>/dev/null \
        | head -1 | awk '{print $NF}')
    if [[ "$changelog_ver" == "$pkgver" || "$changelog_ver" == "$pkgver"-* ]]; then
        pass "%changelog names the shipped version ($changelog_ver)"
    else
        fail "%changelog says '$changelog_ver', package Version is '$pkgver'"
    fi

    local root="$WORK/rpm"
    mkdir -p "$root"
    ( cd "$root" && rpm2cpio "$RPM_FILE" | cpio -idm --quiet ) \
        || { fail "could not extract the payload"; return; }
    check_payload "$root" "rpm"

    if ! have rpmlint; then
        skip "rpmlint not installed"
        return
    fi
    local rpmlintrc=""
    [[ -f "$REPO_ROOT/miaz.rpmlintrc" ]] && rpmlintrc="-r $REPO_ROOT/miaz.rpmlintrc"
    out=$(rpmlint $rpmlintrc "$RPM_FILE" 2>&1)
    local errors warnings
    errors=$(echo "$out" | grep -c ': E: ')
    warnings=$(echo "$out" | grep -c ': W: ')
    if [[ "$errors" -eq 0 ]]; then
        pass "rpmlint: no errors ($warnings warnings)"
    else
        fail "rpmlint: $errors errors, $warnings warnings"
        detail "$(echo "$out" | grep ': E: ' | sed 's/.*: E: //' | sort | uniq -c | sort -rn)"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# DEB
# ─────────────────────────────────────────────────────────────────────────────
check_deb() {
    section "DEB: $(basename "$DEB_FILE")"
    have dpkg-deb || { skip "dpkg-deb not installed (dnf install dpkg)"; return; }

    local out pkgver name
    pkgver=$(dpkg-deb -f "$DEB_FILE" Version)
    name=$(dpkg-deb -f "$DEB_FILE" Package)
    if [[ "$pkgver" == "$VERSION"* ]]; then
        pass "version matches meson.build ($VERSION)"
    else
        # Packages are built from a commit, the working tree may have moved on.
        warn "version is $pkgver, the working tree says $VERSION (built from another commit?)"
    fi

    for field in Maintainer Depends Description Homepage; do
        if [[ -n "$(dpkg-deb -f "$DEB_FILE" "$field")" ]]; then
            pass "control: $field is set"
        else
            fail "control: $field is missing"
        fi
    done

    local root="$WORK/deb"
    mkdir -p "$root"
    dpkg-deb -x "$DEB_FILE" "$root" \
        || { fail "could not extract the payload"; return; }

    # Debian Policy requires both, and neither is generated when the package is
    # built with plain dpkg-deb instead of debhelper.
    if [[ -f "$root/usr/share/doc/$name/copyright" ]]; then
        pass "ships /usr/share/doc/$name/copyright"
    else
        fail "no /usr/share/doc/$name/copyright (Policy 12.5)"
    fi
    if compgen -G "$root/usr/share/doc/$name/changelog*.gz" >/dev/null; then
        pass "ships a compressed changelog"
    else
        fail "no /usr/share/doc/$name/changelog.Debian.gz (Policy 12.7)"
    fi

    out=$(dpkg-deb -c "$DEB_FILE" | awk '$1 ~ /^-/ && $1 !~ /^-rw.r..r..$/ && $1 !~ /^-rwxr-xr-x$/ {print $1, $6}')
    if [[ -z "$out" ]]; then
        pass "file modes are 0644 or 0755"
    else
        fail "unexpected file modes"
        detail "$out"
    fi

    check_payload "$root" "deb"

    local lintian_out=""
    if have lintian; then
        lintian_out=$(lintian --tag-display-limit 0 "$DEB_FILE" 2>&1)
    elif [[ -n "$CONTAINER" ]]; then
        log "running lintian in $CONTAINER (debian:stable-slim)"
        lintian_out=$($CONTAINER run --rm -v "$(dirname "$DEB_FILE")":/pkg:ro,z \
            debian:stable-slim bash -c \
            "apt-get update -qq >/dev/null 2>&1 && \
             apt-get install -y -qq lintian >/dev/null 2>&1 && \
             lintian --tag-display-limit 0 /pkg/$(basename "$DEB_FILE") 2>&1" \
            | grep -E '^[EWI]: ')
    else
        skip "lintian (not installed, no container engine)"
    fi

    if [[ -n "$lintian_out" ]]; then
        local errors warnings
        errors=$(echo "$lintian_out" | grep -c '^E: ')
        warnings=$(echo "$lintian_out" | grep -c '^W: ')
        if [[ "$errors" -eq 0 ]]; then
            pass "lintian: no errors ($warnings warnings)"
        else
            fail "lintian: $errors errors, $warnings warnings"
            detail "$(echo "$lintian_out" | grep '^E: ' | sed 's/\[.*//' | sort -u)"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Cross check: both packages should carry the same files
# ─────────────────────────────────────────────────────────────────────────────
check_both_agree() {
    [[ -d "$WORK/rpm" && -d "$WORK/deb" ]] || return 0
    section "rpm and deb agree"

    # The two formats spell the version differently: the rpm splits it into
    # Version and Release, the deb keeps it whole and adds a Debian revision.
    # Put both back together and compare, because "same version in both
    # packages" is the guarantee the shared source export exists to provide.
    local rpm_ver rpm_rel rpm_full deb_full
    rpm_ver=$(rpm -qp --qf '%{VERSION}' "$RPM_FILE" 2>/dev/null)
    rpm_rel=$(rpm -qp --qf '%{RELEASE}' "$RPM_FILE" 2>/dev/null)
    rpm_full="${rpm_ver}+build.${rpm_rel%%.*}"
    deb_full=$(dpkg-deb -f "$DEB_FILE" Version 2>/dev/null)
    deb_full="${deb_full%-*}"

    if [[ "$rpm_full" == "$deb_full" ]]; then
        pass "both declare version $deb_full"
    elif [[ "$rpm_ver" == "${deb_full%%+*}" ]]; then
        fail "same release version, different build: rpm $rpm_full, deb $deb_full"
    else
        fail "different versions: rpm $rpm_full, deb $deb_full"
    fi

    # Documentation and licence paths differ by design between the two
    # distributions, so they are not part of the comparison.
    local filter='^/usr/share/(doc|licenses|man)/'
    ( cd "$WORK/rpm" && find . -type f -o -type l ) | sed 's/^\.//' | grep -Ev "$filter" | sort > "$WORK/rpm.list"
    ( cd "$WORK/deb" && find . -type f -o -type l ) | sed 's/^\.//' | grep -Ev "$filter" | sort > "$WORK/deb.list"

    local only_rpm only_deb
    only_rpm=$(comm -23 "$WORK/rpm.list" "$WORK/deb.list")
    only_deb=$(comm -13 "$WORK/rpm.list" "$WORK/deb.list")

    if [[ -z "$only_rpm" && -z "$only_deb" ]]; then
        pass "same payload in both packages ($(wc -l < "$WORK/rpm.list") files)"
        return
    fi
    fail "payloads differ: $(echo -n "$only_rpm" | grep -c . ) only in rpm, $(echo -n "$only_deb" | grep -c . ) only in deb"
    [[ -n "$only_rpm" ]] && { echo "        only in rpm:"; detail "$only_rpm" 5; }
    [[ -n "$only_deb" ]] && { echo "        only in deb:"; detail "$only_deb" 5; }
}

# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: do the dependencies resolve against a real archive
# ─────────────────────────────────────────────────────────────────────────────
check_resolution() {
    [[ -n "$DEB_FILE" ]] || return 0
    section "dependency resolution"

    if [[ -z "$CONTAINER" ]]; then
        skip "no container engine (podman or docker) available"
        return
    fi

    local base out status
    base=$(basename "$DEB_FILE")
    for image in $IMAGES; do
        log "resolving against $image"
        out=$($CONTAINER run --rm -v "$(dirname "$DEB_FILE")":/pkg:ro,z "$image" \
            bash -c "apt-get update -qq >/dev/null 2>&1 && \
                     apt-get install -y --simulate --no-install-recommends /pkg/$base" 2>&1)
        status=$?
        if [[ $status -eq 0 ]] && echo "$out" | grep -q "Conf ${base%%_*} "; then
            pass "$image: every dependency resolves"
        else
            fail "$image: dependencies do not resolve"
            detail "$(echo "$out" | grep -vE '^(Inst|Conf) ' | tail -15)"
        fi
    done
}

# ─────────────────────────────────────────────────────────────────────────────
[[ -n "$RPM_FILE" ]] && check_rpm
[[ -n "$DEB_FILE" ]] && check_deb
check_both_agree
check_resolution

section "summary"
printf '  %d passed, %d failed, %d warnings, %d skipped\n' \
    "$PASS_COUNT" "$FAIL_COUNT" "$WARN_COUNT" "$SKIP_COUNT"
[[ $FAIL_COUNT -eq 0 ]] || exit 1
exit 0
