# Contributing to MiAZ

Thank you for your interest in contributing. The sections below cover everything
you need to get started.

## Development environment

Requirements:

- Python 3.9 or later
- PyGObject
- libpeas 2.x
- meson and ninja
- GTK >= 4.10, Libadwaita >= 1.6 (system packages)

Clone your fork and install dependencies:

```bash
git clone <your-fork-url>
cd MiAZ
pip install pygobject
```

Run the app directly from the repository root without installing:

```bash
PYTHONPATH=. python -m MiAZ.miaz
```

## Running the test suite

```bash
python -m pytest tests/ -v
```

Tests run headless; no display or Wayland/X11 session is needed.

## Code style

- Follow PEP 8.
- Do not use `get_style_context()`. Use `add_css_class()` and `remove_css_class()` instead.
- Files under `MiAZ/backend/` must not import from `gi.repository.Gtk` or
  `gi.repository.Adw`. The backend layer has zero GTK dependencies by design.
- Use `GLib.idle_add()` to marshal results from background threads back to the
  GTK main loop.

## Running locally without installing

The dev-run command above (`PYTHONPATH=. python -m MiAZ.miaz`) works from the
repo root at any time, provided the system GTK4 and Libadwaita packages are
installed. No meson build step is required for basic development.

## Submitting a pull request

1. Fork the repository and create a branch from `main`.
2. Name the branch `fix/short-description` for bug fixes or `feat/short-description`
   for new features.
3. Make your changes, add tests where appropriate, and confirm the test suite
   passes (`python -m pytest tests/ -v`).
4. Open a pull request against the `main` branch. Describe what the change does
   and why.

## Releasing

Cutting a release is documented in [RELEASING.md](RELEASING.md). The short
version is `scripts/release.sh --dry-run` to look, then `scripts/release.sh`,
then write `releases/X.Y.Z.md` by hand.

## Translations

Translatable strings use `gettext`. The template is at `po/miaz.pot`.

To add a new language:

1. Copy `po/miaz.pot` to `po/<lang>.po` (e.g. `po/fr.po`).
2. Fill in the translations using a PO editor such as Poedit or GNOME Translation
   Editor.
3. Open an issue on GitHub to request that `<lang>` be added to `po/LINGUAS` so
   the build system picks it up.
