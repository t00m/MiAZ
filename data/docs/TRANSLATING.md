# Translating MiAZ

This guide explains how to translate MiAZ into a new language or update an
existing translation.

## Introduction

MiAZ uses the GNU gettext system, integrated through Meson with the `glib`
preset. The application binds to text domain `miaz`; translation catalogues
live in `po/` and are compiled to `.mo` files at install time.

- `po/POTFILES`: list of source files scanned for translatable strings.
- `po/LINGUAS`: list of language codes that have a translation.
- `po/miaz.pot`: generated template (not committed; produced by `meson compile ... miaz-pot`).
- `po/<lang>.po`: one file per language with the actual translations.

The source code wraps every user-visible string with `_()`:

```python
from gettext import gettext as _
button.set_label(_('Save'))
```

## Prerequisites

- `gettext` (provides `xgettext`, `msgmerge`, `msgfmt`, `msginit`)
- a `.po` editor:  [Poedit](https://poedit.net/) is recommended, but any text editor works
- a configured MiAZ build directory:

  ```sh
  meson setup builddir_user --prefix="$HOME/.local"
  ```

## Adding a new language

Replace `<lang>` with the target language code (`es`, `de`, `fr_CA`, `pt_BR`, ...).

1. Add the language code to `po/LINGUAS`, one per line.
2. Refresh the template:

   ```sh
   scripts/i18n/update_translations.sh
   ```
3. Initialise the catalogue:

   ```sh
   msginit -i po/miaz.pot -o po/<lang>.po -l <lang>
   ```

   If `msginit` is unavailable, copy `po/miaz.pot` to `po/<lang>.po` and edit
   the header (`Language`, `Language-Team`, `Plural-Forms`).
4. Open `po/<lang>.po` and translate each `msgid` by filling in the matching
   `msgstr`. Leave entries flagged `fuzzy` only after reviewing and removing
   the flag.
5. Test locally:

   ```sh
   meson compile -C builddir_user
   meson install -C builddir_user
   LANGUAGE=<lang> python -m MiAZ.miaz
   ```
6. Open a pull request with `po/<lang>.po` and the `po/LINGUAS` change only
   (never commit `.mo` files: the build system generates them).

## Updating an existing translation

1. Refresh the template and merge it into every `.po`:

   ```sh
   scripts/i18n/update_translations.sh
   ```

   New strings appear in your `po/<lang>.po` as empty `msgstr ""`. Obsolete
   strings are prefixed with `#~` and can be removed.
2. Translate the new entries (and clean up obsolete ones if you wish).
3. Test as in the previous section.
4. Open a pull request with the updated `po/<lang>.po`.

## Developer string guidelines

Read this if you contribute Python code, not just translations.

- Wrap every user-visible string with `_()`.
- Never wrap debug or log messages:  they are for developers, not users.
- Never put an f-string inside `_()`. The string extractor cannot read
  f-strings.

  Correct:
  ```python
  title = _('Manage %s') % item_type
  ```

  Wrong:
  ```python
  title = _(f'Manage {item_type}')
  ```
- Keep strings short and self-contained. Avoid embedding internal
  identifiers (config keys, file paths, GObject type names) in translatable
  text.
- Reuse existing strings where possible. For example, the dialog response
  labels (`Cancel`, `Close`, `Apply`, `Yes`, `No`) are centralised in
  `MiAZ/frontend/desktop/services/dialogs.py`.
- Every `.py` file containing `_()` must be listed in `po/POTFILES`.

## Cheat sheet

| Task | Command |
|---|---|
| Refresh `.pot` and merge into all `.po` | `scripts/i18n/update_translations.sh` |
| Just refresh the `.pot` | `scripts/i18n/update_pot.sh` |
| Just merge `.pot` into existing `.po` files | `scripts/i18n/update_po.sh` |
| Show completion ratio for a language | `msgfmt --statistics -o /dev/null po/<lang>.po` |
| Compile a `.mo` (normally handled by Meson) | `msgfmt po/<lang>.po -o po/<lang>.mo` |
| Run MiAZ in a specific language | `LANGUAGE=<lang> python -m MiAZ.miaz` |
