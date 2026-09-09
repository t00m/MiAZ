#!/bin/bash
#
# Cut a release: set the version everywhere, date the changelog, and check the
# result before anything leaves the machine.
#
# This drives the scripts that already exist rather than repeating them:
#
#   scripts/devel/increase_meson_version.sh   bumps meson.build
#   scripts/devel/sync_versions.sh            meson.build -> pyproject, spec,
#                                             debian/changelog, metainfo
#   scripts/devel/render_release_notes.py     releases/X.Y.Z.md -> the three
#                                             files that show notes to a user
#
# and fills the three gaps none of them cover: the bundled plugins, the
# CHANGELOG heading, and the tag.
#
# Usage:
#   scripts/release.sh                 release the version meson.build names
#   scripts/release.sh 0.4.0           set that version, then release it
#   scripts/release.sh minor           bump minor, then release it
#
#   --date YYYY-MM-DD   release date, default today
#   --dry-run           say what would change, write nothing
#   --commit            commit the result
#   --tag               commit and tag vX.Y.Z
#   --allow-dirty       proceed with uncommitted changes
#
# It writes files and stops. Committing and tagging need to be asked for: a
# tag is the thing other people build from, and it should not appear because a
# script was run to see what it would say.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

METAINFO="data/io.github.t00m.MiAZ.metainfo.xml.in"

log()  { echo "[release] $*"; }
warn() { echo "[release] WARNING: $*" >&2; }
die()  { echo "[release] ERROR: $*" >&2; exit 1; }

TARGET=""
DATE="$(date '+%Y-%m-%d')"
DRY_RUN=0
DO_COMMIT=0
DO_TAG=0
ALLOW_DIRTY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)        DATE="${2:-}"; shift 2 ;;
        --dry-run)     DRY_RUN=1; shift ;;
        --commit)      DO_COMMIT=1; shift ;;
        --tag)         DO_TAG=1; DO_COMMIT=1; shift ;;
        --allow-dirty) ALLOW_DIRTY=1; shift ;;
        -h|--help)     sed -n '2,31p' "$0"; exit 0 ;;
        -*)            die "unknown option: $1" ;;
        *)             [[ -n "$TARGET" ]] && die "give one version, not two"
                       TARGET="$1"; shift ;;
    esac
done

[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die "--date wants YYYY-MM-DD, not '$DATE'"

# --- preflight -------------------------------------------------------------

git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository"
command -v python3 >/dev/null || die "python3 is required"

if [[ $ALLOW_DIRTY -eq 0 && $DRY_RUN -eq 0 ]]; then
    if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
        die "the working tree has uncommitted changes. Commit them, or pass --allow-dirty."
    fi
fi

current_version() {
    grep -m1 -oP "^\s*version\s*:\s*'\K[^']+" meson.build
}

CURRENT="$(current_version)"
[[ -n "$CURRENT" ]] || die "could not read the version from meson.build"

# --- what are we releasing -------------------------------------------------

case "$TARGET" in
    "")
        # No argument: release what meson.build already names. This is the
        # normal case, because the version is chosen when the cycle opens and
        # the changelog has been collecting under it since.
        VERSION="${CURRENT%%+*}"
        ;;
    major|minor|patch)
        if [[ $DRY_RUN -eq 1 ]]; then
            log "would bump $TARGET from $CURRENT"
            VERSION="(bumped $TARGET)"
        else
            ./scripts/devel/increase_meson_version.sh "$TARGET" >/dev/null \
                || die "increase_meson_version.sh failed"
            VERSION="$(current_version)"
            VERSION="${VERSION%%+*}"
            log "meson.build $CURRENT -> $VERSION"
        fi
        ;;
    *)
        [[ "$TARGET" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
            || die "'$TARGET' is not a version. Use X.Y.Z, or major, minor, patch."
        VERSION="$TARGET"
        ;;
esac

if [[ $DRY_RUN -eq 0 && "$VERSION" != "${CURRENT%%+*}" ]]; then
    sed -i -E "s/^(\s*version\s*:\s*')[^']+(')/\1$VERSION\2/" meson.build
    [[ "$(current_version)" == "$VERSION" ]] || die "meson.build was not updated"
    log "meson.build version -> $VERSION"
fi

if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
    die "tag v$VERSION already exists. Releasing it again would move what people built from."
fi

log "releasing $VERSION on $DATE"

if [[ $DRY_RUN -eq 1 ]]; then
    log "dry run: nothing below is written"
    echo
    echo "  meson.build       $CURRENT -> $VERSION"
    # -L, files with no match: the ones whose Version line is not $VERSION.
    plugin_total=$(ls data/resources/plugins/*/*.plugin 2>/dev/null | wc -l)
    plugin_stale=$(grep -L "^Version=$VERSION$" data/resources/plugins/*/*.plugin 2>/dev/null | wc -l)
    echo "  plugins           $plugin_stale of $plugin_total .plugin files carry another version"
    echo "  CHANGELOG.md      $(grep -m1 '^## \[' CHANGELOG.md)"
    echo "  release notes     releases/$VERSION.md $([[ -f "releases/$VERSION.md" ]] && echo exists || echo 'does not exist yet')"
    echo "  tag               v$VERSION would be created with --tag"
    exit 0
fi

# --- the bundled plugins ---------------------------------------------------
#
# A bundled plugin is not released on its own, so it carries the version of the
# MiAZ it ships in. Both halves of every plugin have to move: libpeas reads the
# .plugin file, and the plugin info dialog reads the dict.
# tests/test_plugin_categories.py fails if this misses one.

log "syncing the bundled plugins to $VERSION ..."
python3 - "$VERSION" <<'PYEOF'
import glob, os, re, sys

version = sys.argv[1]
changed = 0
for plugin_file in sorted(glob.glob('data/resources/plugins/*/*.plugin')):
    text = open(plugin_file, encoding='utf-8').read()
    new, count = re.subn(r'^Version=.*$', f'Version={version}', text, flags=re.MULTILINE)
    if count != 1:
        sys.exit(f'{plugin_file}: expected one Version line, found {count}')
    if new != text:
        open(plugin_file, 'w', encoding='utf-8').write(new)
        changed += 1

    for module in sorted(glob.glob(os.path.join(os.path.dirname(plugin_file), '*.py'))):
        src = open(module, encoding='utf-8').read()
        if re.search(r"'Version'\s*:\s*'[^']*'", src) is None:
            continue
        out, n = re.subn(r"('Version'\s*:\s*')[^']*(')", rf"\g<1>{version}\g<2>", src)
        if n != 1:
            sys.exit(f'{module}: expected one Version key, found {n}')
        if out != src:
            open(module, 'w', encoding='utf-8').write(out)
            changed += 1
        break

print(f'  {changed} plugin files updated')
PYEOF
[[ $? -eq 0 ]] || die "the plugin sync failed"

# --- the packaging metadata ------------------------------------------------

log "syncing the packaging metadata ..."
./scripts/devel/sync_versions.sh | sed 's/^/  /' || die "sync_versions.sh failed"

# sync_versions.sh stamps the day the version was bumped, which is the day the
# cycle opened and not the day it ships. 0.3.0 sat in the metainfo dated 31
# August for the whole of the cycle that produced it.
log "dating the metainfo release ..."
python3 - "$VERSION" "$DATE" "$METAINFO" <<'PYEOF'
import re, sys

version, date, path = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding='utf-8').read()
pattern = re.compile(r'(<release version="' + re.escape(version) + r'" date=")[^"]*(")')
new, count = pattern.subn(rf'\g<1>{date}\g<2>', text)
if count == 0:
    sys.exit(f'no <release version="{version}"> in {path}')
if new != text:
    open(path, 'w', encoding='utf-8').write(new)
    print(f'  metainfo release {version} dated {date}')
else:
    print(f'  metainfo release {version} already dated {date}')
PYEOF
[[ $? -eq 0 ]] || die "could not date the metainfo release"

# --- the changelog ---------------------------------------------------------
#
# Keep a Changelog: the section that has been collecting entries becomes the
# release, and a fresh Unreleased opens above it for the next cycle.

log "dating the changelog ..."
python3 - "$VERSION" "$DATE" <<'PYEOF'
import re, sys

version, date = sys.argv[1], sys.argv[2]
path = 'CHANGELOG.md'
text = open(path, encoding='utf-8').read()

# Both spellings are in use: the heading names the coming version once it is
# chosen, and is a bare Unreleased before that.
# [ \t]*$ and not \s*$: \s matches a newline, so a greedy \s*$ ate the blank
# line below the heading and welded it to the ### that follows.
heading = re.compile(r'^## \[(?:Unreleased|' + re.escape(version) + r')\](?: - Unreleased)?[ \t]*$',
                     re.MULTILINE)
# Asked first, because this script tells the caller to run it again once the
# release notes are written. A second run finds the fresh Unreleased heading
# left by the first and would date that one too, leaving two headings for the
# same release.
if re.search(r'^## \[' + re.escape(version) + r'\] - \d{4}-\d{2}-\d{2}[ \t]*$',
             text, re.MULTILINE):
    print(f'  {version} is already dated, left alone')
    sys.exit(0)

match = heading.search(text)
if match is None:
    sys.exit(f'no Unreleased section in {path} to release as {version}')

new_heading = f'## [Unreleased]\n\n## [{version}] - {date}'
text = text[:match.start()] + new_heading + text[match.end():]
open(path, 'w', encoding='utf-8').write(text)
print(f'  [{version}] - {date}, with a fresh Unreleased above it')
PYEOF
[[ $? -eq 0 ]] || die "could not update the changelog"

# --- the release notes -----------------------------------------------------
#
# These are the lines a software centre shows, so they are written by a person,
# not generated. What is created here is a draft seeded from the changelog
# headings, with a marker that keeps it from being shipped by accident.

NOTES="releases/$VERSION.md"
if [[ ! -f "$NOTES" ]]; then
    log "drafting $NOTES from the changelog ..."
    mkdir -p releases
    python3 - "$VERSION" "$NOTES" <<'PYEOF'
import re, sys

version, out = sys.argv[1], sys.argv[2]
text = open('CHANGELOG.md', encoding='utf-8').read()
start = text.find(f'## [{version}] - ')
end = text.find('\n## [', start + 1)
section = text[start:end if end != -1 else len(text)]

# The bold lead of each entry is the one line that entry is about.
leads = re.findall(r'^- \*\*(.+?)\*\*', section, re.MULTILINE)

with open(out, 'w', encoding='utf-8') as handle:
    handle.write(f'# {version}\n\n')
    handle.write('TODO: replace this line with one sentence a software centre '
                 'can show, then cut the list below down to the handful of '
                 'changes a user would notice. Delete this TODO when done.\n\n')
    for lead in leads:
        handle.write(f'- {lead.rstrip(".")}\n')
print(f'  {len(leads)} candidates to cut down. The TODO line has to go.')
PYEOF
    warn "$NOTES is a draft. Write it before building packages."
fi

# A draft is not rendered. render_release_notes.py only recognises the older
# "See CHANGELOG.md for details" placeholder, so without this the TODO line
# above would be written into the metainfo as the sentence users read, which is
# the accident that shipped in 0.1.50 and 0.1.60.
if grep -q '^TODO:' "$NOTES" 2>/dev/null; then
    warn "$NOTES still has its TODO line, so the notes were not rendered"
else
    log "rendering the release notes ..."
    ./scripts/devel/render_release_notes.py 2>&1 | sed 's/^/  /' || true
fi

# --- check what we just did ------------------------------------------------

log "checking ..."
FAILED=0

if command -v ruff >/dev/null; then
    if ruff check MiAZ data/resources/plugins tests >/dev/null 2>&1; then
        log "  ruff: clean"
    else
        warn "ruff reports problems"; FAILED=1
    fi
else
    warn "ruff not found, skipping the lint"
fi

if python3 -m pytest tests -q >/dev/null 2>&1; then
    log "  tests: pass"
else
    warn "the unit tests fail. Run: python3 -m pytest tests -q"; FAILED=1
fi

if grep -q '^TODO:' "$NOTES" 2>/dev/null; then
    warn "$NOTES is still a draft. Write it, then run this again."
    FAILED=1
elif ./scripts/devel/render_release_notes.py --check >/dev/null 2>&1; then
    log "  release notes: written and rendered"
else
    warn "the release notes are missing, still a placeholder, or not rendered."
    warn "Write $NOTES, then run scripts/devel/render_release_notes.py"
    FAILED=1
fi

# --- report ----------------------------------------------------------------

echo
log "$VERSION is prepared. Changed:"
git status --porcelain | sed 's/^/  /'

if [[ $FAILED -ne 0 ]]; then
    echo
    die "something above needs attention. Nothing was committed."
fi

if [[ $DO_COMMIT -eq 1 ]]; then
    git add -A
    git commit -q -m "release: $VERSION"
    log "committed"
    if [[ $DO_TAG -eq 1 ]]; then
        git tag -a "v$VERSION" -m "MiAZ $VERSION"
        log "tagged v$VERSION"
    fi
else
    echo
    log "nothing committed. To finish:"
    echo "  git add -A && git commit -m 'release: $VERSION'"
    echo "  git tag -a v$VERSION -m 'MiAZ $VERSION'"
fi

echo
log "then build the packages:"
echo "  scripts/packaging/build_all.sh"
