# Releasing MiAZ

How to cut a release, and why the steps are what they are.

`scripts/release.sh` does most of it. This document exists because the parts it
cannot do, writing the release notes and deciding the version, are the parts
that matter, and because knowing what the script is doing is the difference
between running it and trusting it.

## What the version means

`meson.build` owns the version. Everything else copies it.

The number names a **release**, not a change. It moves when something ships,
not per commit. Between releases it stays where it is, naming the version being
built: `0.3.0` in `meson.build` with `## [0.3.0] - Unreleased` in the changelog
means 0.3.0 is the target, not that the file is stale.

Commits are already identified, better than a counter would:

```
$ git describe --tags
v0.2-80-gaa124e79
```

The last tag, the number of commits since it, and the commit itself, all
derived. Nothing to edit and nothing to forget.

The project follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Under SemVer `0.3.1`
promises "backwards-compatible fixes released after 0.3.0". A number that moves
without a release makes that promise to nobody, and every move would need an
AppStream `<release>` entry for packages that were never built.

## Where the version ends up

One number, six files. This is why it is scripted.

| Carried in | Written by |
|---|---|
| `meson.build` | you, or `scripts/devel/increase_meson_version.sh` |
| `pyproject.toml`, `miaz.spec` | `scripts/devel/sync_versions.sh` |
| `debian/changelog`, spec `%changelog`, AppStream `<releases>` | `scripts/devel/sync_versions.sh` |
| `CHANGELOG.md` heading | `scripts/release.sh` |
| the `vX.Y.Z` tag | `scripts/release.sh --tag` |

**The bundled plugins are not on that list, and must not go back on it.** A
plugin that ships with MiAZ declares no version of its own and takes the
application's at runtime, through `pluginsystem.plugin_version()`. It used to
be written into both halves of all 21, forty-two files carrying one number,
and nine of them had drifted from themselves by the time anything checked.
`tests/test_plugin_categories.py` now fails if any bundled plugin declares a
version at all.

An out-of-tree plugin is released on its own schedule, so a `Version=` in its
`.plugin` file is used as it stands. The fallback only applies to plugins that
declare none.

## Before you start

- Every change for this release is committed. The script refuses a dirty tree.
- `python3 -m pytest tests -q` passes.
- `ruff check MiAZ data/resources/plugins tests` is clean.
- The UI tests pass: `scripts/checks/run_ui_tests.sh`. They take about twenty
  minutes and are not part of `meson test`, so they are easy to skip and worth
  not skipping before a release.
- `CHANGELOG.md` has an `Unreleased` section holding everything since the last
  release.

## The steps

### 1. Look at what would happen

```bash
scripts/release.sh --dry-run
```

Reports the version, how many plugin files disagree with it, the changelog
heading it found, and whether the release notes exist. Writes nothing.

### 2. Prepare the release

```bash
scripts/release.sh              # release the version meson.build names
scripts/release.sh 0.4.0        # set that version first
scripts/release.sh minor        # bump minor first
```

This syncs the plugins and the packaging metadata, dates the changelog section
and opens a fresh `Unreleased` above it, dates the AppStream entry with today
rather than the day the version was bumped, and drafts `releases/X.Y.Z.md` from
the changelog headings.

It then stops, because the draft is not shippable yet.

### 3. Write the release notes

`releases/X.Y.Z.md` is what a software centre shows. One sentence, then the
handful of changes a user would notice:

```markdown
# 0.3.0

Steps back through changes you did not mean to make, checks the repository is
in order, and a command line that works.

- Undo and redo, with a history of what changed and what it cost
- The repository can check itself when it opens
- Searching by date on the command line works at last
```

The draft holds one candidate line per changelog entry, which for a large
release is far too many. Cut it down. Delete the `TODO` line when you are done:
the script refuses to finish while it is there, and that guard exists because
0.1.50 and 0.1.60 both shipped with a placeholder nobody had replaced.

Write for someone deciding whether to update, not for someone reading a diff.

### 4. Finish, commit and tag

```bash
scripts/release.sh --tag
```

Runs the checks again, commits as `release: X.Y.Z`, and tags `vX.Y.Z`. Use
`--commit` to commit without tagging, or neither to have it print the commands
and leave them to you.

It never pushes. That stays a decision you make.

```bash
git push && git push --tags
```

### 5. Build the packages

```bash
scripts/packaging/build_all.sh
```

RPM, DEB, Flatpak and AppImage, all from one export of one commit so they
cannot disagree about their own version. They land in `dist/`. A format whose
toolchain is not installed is skipped rather than failed.

Build the tag, not the working tree, if anything has moved since:

```bash
scripts/packaging/build_all.sh --ref v0.3.0
```

### 6. Verify the packages

```bash
scripts/checks/verify_packages.sh dist/
```

Checks the metadata and payload, runs `rpmlint` and `lintian`, and simulates
`apt-get install` in a container to prove the `Depends` names exist in the
target release.

### 7. Publish

Upload `dist/` to the GitHub release for the tag, with the text of
`releases/X.Y.Z.md`.

## What the guards catch

The script refuses to finish, and commits nothing, when:

- the working tree is dirty (`--allow-dirty` overrides)
- the tag already exists, which would move what people already built from
- a plugin file has no `Version` line, or more than one
- there is no `Unreleased` section to release
- the unit tests fail, or ruff reports something
- the release notes are missing, still a draft, or not rendered

Running it twice is safe. A second run finds the release already dated and
leaves it alone rather than dating the fresh `Unreleased` as well.

## Things worth knowing

**CI runs on a listed branch and no other.** `.github/workflows/ci.yml`
triggers on `main`, `0.2` and `0.3`, in two lists, one for pushes and one for
pull requests. A branch that is not in both runs no CI at all and says nothing
about it: the whole 0.3 series ran that way, eighty commits with only the
checks somebody remembered to run by hand. **When a new series opens, add its
branch to both lists.**

**`meson test` runs the unit suite and the three file validations**, in about
fifteen seconds. The UI tests are deliberately not in it: they need a display
and a throwaway HOME, take twenty minutes, and skip themselves without
`MIAZ_UI_SANDBOX`.

**`sync_versions.sh` dates an AppStream entry when the version is bumped**,
which is the day the cycle opens. `release.sh` restamps it with the ship date.
0.3.0 sat in the metainfo dated 31 August, the same day as 0.2.0, for the whole
cycle that produced it.

## Keeping this document current

This describes real scripts. When one of them changes, change this too, in the
same commit. The parts most likely to go out of date:

- the file list in **Where the version ends up**, whenever something new
  carries the version. Adding a plugin is not such a change: a bundled plugin
  carries no version, and a test enforces that
- the steps, whenever `release.sh`, `sync_versions.sh`,
  `render_release_notes.py` or `build_all.sh` grow or lose a stage
- the CI note above, whenever the workflow's branch lists change

A release document that is wrong is worse than none: it gets followed.
