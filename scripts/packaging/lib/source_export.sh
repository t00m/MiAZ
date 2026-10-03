# Shared source export for the packaging scripts. Not executable: source it.
#
# Every package is built from an export of one commit, never from the working
# tree. Before this existed the .rpm took its sources from 'git archive HEAD'
# but its spec and version from the working tree, while the .deb took
# everything from the working tree. The two could therefore disagree about
# their own version and about which files they carried, and did.
#
# Usage from a packaging script:
#
#     source "$SCRIPT_DIR/../lib/source_export.sh"
#     miaz_prepare_source "$REPO_ROOT" "rpm"
#     # now use $MIAZ_SRC_DIR as the root of every build input
#
# Environment:
#   MIAZ_SOURCE_DIR     an export another script already made. Used as is, and
#                       not cleaned up here: whoever exported it owns it. This
#                       is how build_all.sh gives both formats one tree.
#   MIAZ_SOURCE_COMMIT  the commit that export came from, for the log line.
#   MIAZ_BUILD_REF      what to export when there is no shared export:
#                       any ref or SHA, or the word 'pushed' for the last
#                       commit on the branch this one tracks. Default HEAD.
#
# Sets: MIAZ_SRC_DIR, MIAZ_SRC_COMMIT, MIAZ_SRC_VERSION

# Resolve MIAZ_BUILD_REF to a commit SHA. Echoes the SHA.
miaz_resolve_commit() {
    local repo_root="$1" tag="$2"
    local ref="${MIAZ_BUILD_REF:-HEAD}"

    if [[ "$ref" == "pushed" ]]; then
        # '@{upstream}' is the local record of the remote branch and is only as
        # fresh as the last fetch, so refresh it first. A failed fetch is not
        # fatal (offline builds still work), but it has to be said out loud.
        if ! git -C "$repo_root" fetch --quiet origin 2>/dev/null; then
            echo "[$tag] WARNING: could not fetch from origin, using the last known state of the remote branch" >&2
        fi
        ref="$(git -C "$repo_root" rev-parse --verify --quiet '@{upstream}')" || {
            echo "[$tag] ERROR: this branch tracks no remote branch, so there is no pushed commit to build" >&2
            exit 1
        }
    fi

    git -C "$repo_root" rev-parse --verify --quiet "${ref}^{commit}" || {
        echo "[$tag] ERROR: not a commit: ${MIAZ_BUILD_REF:-HEAD}" >&2
        exit 1
    }
}

# Say what the build will not contain. Silence here means the export matches
# what the user is looking at.
miaz_report_gap() {
    local repo_root="$1" tag="$2" commit="$3"
    local head dirty behind

    head="$(git -C "$repo_root" rev-parse --verify HEAD 2>/dev/null || true)"
    if [[ -n "$head" && "$head" != "$commit" ]]; then
        behind="$(git -C "$repo_root" rev-list --count "${commit}..HEAD" 2>/dev/null || echo '?')"
        echo "[$tag] NOTE: building $behind commit(s) behind HEAD"
    fi

    dirty="$(git -C "$repo_root" status --porcelain --untracked-files=no | wc -l)"
    if [[ "$dirty" -gt 0 ]]; then
        echo "[$tag] WARNING: $dirty modified file(s) in the working tree are NOT in this package"
        echo "[$tag]          commit them first, or build with MIAZ_BUILD_REF pointing elsewhere"
    fi
}

# Read the version out of an exported tree, so the package version is the one
# the commit declares rather than whatever the working tree happens to say.
miaz_version_from() {
    grep -m1 "version" "$1/meson.build" | sed "s/.*version.*: *'\([^']*\)'.*/\1/"
}

# Build the user help into an export, as help/target. Every package carries
# it: the rpm tarball (Source0) and the .deb are built from the export, and
# meson installs help/target when the build machine has no KB4IT. A distribution
# rebuilding from the tarball therefore needs no KB4IT either.
#
# Needs KB4IT 0.8 or newer on PATH (pip install 'KB4IT>=0.8'). MIAZ_SKIP_HELP=1
# builds without it, and the packages then carry no help: the help window
# falls back to the published site.
miaz_build_help() {
    local src="$1" tag="$2"
    if [[ "${MIAZ_SKIP_HELP:-0}" == "1" ]]; then
        echo "[$tag] WARNING: MIAZ_SKIP_HELP=1, the packages will carry no help" >&2
        return 0
    fi
    local kb4it version work
    kb4it="$(command -v kb4it || true)"
    if [[ -z "$kb4it" ]]; then
        echo "[$tag] ERROR: kb4it not found. Every package carries the user help, built with KB4IT." >&2
        echo "[$tag]        Install it with: pip install 'KB4IT>=0.8'   (or MIAZ_SKIP_HELP=1 to build without help)" >&2
        exit 1
    fi
    version="$("$kb4it" --version 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)+' | head -1)"
    if ! python3 -c "import sys; v = tuple(int(x) for x in sys.argv[1].split('.')[:2]); sys.exit(v < (0, 8))" "${version:-0}"; then
        echo "[$tag] ERROR: KB4IT ${version:-unknown} is too old for the help pages; 0.8 or newer is needed." >&2
        echo "[$tag]        Upgrade it with: pip install --upgrade 'KB4IT>=0.8'" >&2
        exit 1
    fi
    work="$(mktemp -d)"
    if ! python3 "$src/build-aux/meson/build_help.py" --kb4it "$kb4it" \
            --help-dir "$src/help" --output "$src/help/target" \
            --work "$work" --mode enabled; then
        rm -rf "$work"
        echo "[$tag] ERROR: the help did not build; see the KB4IT messages above" >&2
        exit 1
    fi
    rm -rf "$work"
    echo "[$tag] Help: built with KB4IT $version into the export"
}

miaz_prepare_source() {
    local repo_root="$1" tag="${2:-pkg}"

    if [[ -n "${MIAZ_SOURCE_DIR:-}" ]]; then
        [[ -d "$MIAZ_SOURCE_DIR" ]] || {
            echo "[$tag] ERROR: MIAZ_SOURCE_DIR does not exist: $MIAZ_SOURCE_DIR" >&2
            exit 1
        }
        MIAZ_SRC_DIR="$MIAZ_SOURCE_DIR"
        MIAZ_SRC_COMMIT="${MIAZ_SOURCE_COMMIT:-unknown}"
        MIAZ_SRC_VERSION="$(miaz_version_from "$MIAZ_SRC_DIR")"
        echo "[$tag] Source: shared export of ${MIAZ_SRC_COMMIT:0:12} (version $MIAZ_SRC_VERSION)"
        return 0
    fi

    command -v git >/dev/null || { echo "[$tag] ERROR: git is required" >&2; exit 1; }

    MIAZ_SRC_COMMIT="$(miaz_resolve_commit "$repo_root" "$tag")"
    MIAZ_SRC_DIR="$(mktemp -d)"
    # Only this script exported it, so only this script removes it.
    trap 'rm -rf "$MIAZ_SRC_DIR"' EXIT

    git -C "$repo_root" archive --format=tar "$MIAZ_SRC_COMMIT" | tar -x -C "$MIAZ_SRC_DIR"
    MIAZ_SRC_VERSION="$(miaz_version_from "$MIAZ_SRC_DIR")"
    [[ -n "$MIAZ_SRC_VERSION" ]] || {
        echo "[$tag] ERROR: could not read the version from the exported meson.build" >&2
        exit 1
    }

    echo "[$tag] Source: ${MIAZ_SRC_COMMIT:0:12} $(git -C "$repo_root" log -1 --format=%s "$MIAZ_SRC_COMMIT" | cut -c1-60)"
    echo "[$tag] Version: $MIAZ_SRC_VERSION"
    miaz_build_help "$MIAZ_SRC_DIR" "$tag"
    miaz_report_gap "$repo_root" "$tag" "$MIAZ_SRC_COMMIT"
}
