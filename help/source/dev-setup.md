---
DocType: How-to guide
Feature: Development
HelpId: dev-setup
Level: advanced
Order: 920
Section: Developers
Summary: Run MiAZ from source, install it locally, and run the checks before a commit.
---

# Run, test and check MiAZ

## Run from source {#run}

From the repository root, with the system GTK 4, libadwaita, libpeas 2 and
WebKitGTK 6 packages installed:

```bash
PYTHONPATH=. python -m MiAZ.miaz
```

No build step is needed for this.

## Install for your user {#install}

```bash
./scripts/install/local/install_user.sh
```

Or by hand with Meson:

```bash
meson setup _build --prefix="$HOME/.local"
ninja -C _build install
```

When `kb4it` is on your `PATH`, the build also builds this help and installs
it, so a change under `help/` reaches the installed MiAZ with the next
install. `-Dhelp=enabled` makes a help build failure fail the build;
`-Dhelp=disabled` skips the help.

## Checks before a commit {#checks}

| Check | Command | Time |
|---|---|---|
| Lint | `ruff check MiAZ tests` | seconds |
| Unit tests | `python -m pytest -q tests` | about a minute |
| One UI test file | `scripts/checks/run_ui_tests.sh --headless tests/ui/test_ui_<name>.py` | seconds to minutes |
| All UI tests | `scripts/checks/run_ui_tests.sh` | about twenty minutes |

The UI tests drive the real application in a throwaway home folder. Run the
files that cover what you changed; the full suite runs in CI.

## Logs {#logs}

Each run writes `~/.MiAZ/var/log/MiAZ.log` and keeps the previous one as
`MiAZ.last.log`. Set `MIAZ_DEBUG=1` to also see debug messages on the console.

## Conventions {#conventions}

- Python 3.9 compatible: no `X | Y` type unions.
- No `print()`; use the logger.
- No bare `except:`.
- Frontend code does not touch files directly; it calls the `util` service.
- Every change gets a `CHANGELOG.md` entry, in Keep a Changelog format.
