# CLAUDE.md — MiAZ Project

> Personal Document Organizer  
> Repo: https://github.com/t00m/MiAZ  
> App ID: `io.github.t00m.MiAZ`  
> License: GPL v3

---

## What MiAZ does

MiAZ is a **GTK4/Libadwaita desktop application** that organises personal documents by enforcing a strict 7-field filename convention:

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
```

Example: `20240315-ES-HOU-BANKNAME-INV-Q1invoice-JOHNDOE`

The **directory is the database** — no SQLite, no external DB. Everything is derived from filenames.

---

## Tech stack

| Layer | Technology | Min version |
|---|---|---|
| Language | Python | 3.9 |
| GUI toolkit | GTK | 4.10 |
| GNOME style | Libadwaita | 1.6 |
| Python–GTK bindings | PyGObject / GObject | 3.50 |
| Build system | Meson + Ninja | — |
| Distribution | Flatpak (in progress) | — |
| i18n | gettext via GLib | — |

---

## Repository layout

```
MiAZ/                            ← repo root
├── MiAZ/                        ← Python package
│   ├── __init__.py              ← version / pkgdatadir constants
│   ├── main.py                  ← entry point (Adw.Application subclass)
│   ├── app/                     ← top-level application shell
│   ├── backend/                 ← business logic (NO GTK imports here)
│   ├── frontend/                ← widgets, dialogs, pages (GTK/Adw)
│   └── plugins/                 ← built-in and user plugins
├── data/
│   ├── icons/hicolor/           ← application icons
│   ├── *.desktop.in             ← desktop entry
│   ├── *.metainfo.xml.in        ← AppStream metadata
│   └── *.gschema.xml            ← GSettings schema
├── po/                          ← translations (POTFILES, *.po)
├── build-aux/meson/             ← postinstall.py and meson helpers
├── flatpak/                     ← Flatpak build helpers
├── scripts/
│   └── install/local/           ← install_user.sh / uninstall_user.sh
├── meson.build                  ← root Meson file
├── meson_options.txt
├── pyproject.toml
└── io.github.t00m.MiAZ.json    ← Flatpak manifest
```

---

## Architecture rules

### Backend (`MiAZ/backend/`)
- **Zero GTK/Adw imports** — must be testable headlessly.
- Owns: filename parsing/validation, repository management (CRUD on files), plugin loading, settings persistence via GSettings.
- Exposes a clean API that the frontend calls.

### Frontend (`MiAZ/frontend/`)
- All GTK4 / Libadwaita widgets live here.
- **Never perform file I/O directly** — always call backend APIs.
- Use `GLib.idle_add()` to marshal background-thread results back to the UI.

### Plugins (`MiAZ/plugins/`)
- Each plugin is a subdirectory with a `plugin.py` implementing the `Plugin` contract (see below).
- Plugins may add frontend panels **or** backend processors — not both in a single plugin.

---

## Filename convention (core domain)

The 7 fields, in order:

| # | Field | Format | Example |
|---|---|---|---|
| 1 | Date | `%Y%m%d` | `20240315` |
| 2 | Country | ISO-3166 Alpha-2 | `ES` |
| 3 | Group | 3-char code | `HOU`, `FIN`, `EDU` |
| 4 | SentBy | Free (no hyphens) | `BANKNAME` |
| 5 | Purpose | 3-char code | `INV`, `REQ`, `INF` |
| 6 | Concept | Free text | `Q1invoice` |
| 7 | SentTo | Free (no hyphens) | `JOHNDOE` |

Separator: `-` (hyphen). Any file added to a repository directory is **automatically renamed** to comply.

When writing code that parses or constructs filenames, always validate all 7 fields and reject/flag non-compliant names rather than silently ignoring them.

---

## Build & install

```bash
# Developer local install (user scope, no root)
./scripts/install/local/install_user.sh

# Manual Meson workflow
meson setup _build --prefix="$HOME/.local"
ninja -C _build
ninja -C _build install

# Uninstall
./scripts/uninstall/uninstall_user.sh

# Flatpak (when available)
flatpak-builder --user --install --force-clean _flatpak_build io.github.t00m.MiAZ.json
flatpak run io.github.t00m.MiAZ
```

Prerequisites: `meson`, `ninja`, `python3 >= 3.9`, `PyGObject >= 3.50`, `GTK >= 4.10`, `Libadwaita >= 1.6`.

---

## GObject / GTK4 conventions used in this project

```python
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, GObject
```

**Always call `gi.require_version()` before any `from gi.repository` import.**

### Signal connections
```python
widget.connect('signal-name', self._handler)
# For background → UI updates:
GLib.idle_add(self._update_ui, result)
```

### List model (GTK4 MVC — no GtkListStore/GtkTreeView)
```python
store = Gio.ListStore(item_type=MyGObjectItem)
filter_model = Gtk.FilterListModel(model=store)
sel_model = Gtk.SingleSelection(model=filter_model)
column_view = Gtk.ColumnView(model=sel_model)
```

### Window structure
```python
class MiAZWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(self._build_content())
        self.set_content(toolbar_view)
```

---

## Plugin contract

```python
# plugins/myplugin/plugin.py
class Plugin:
    name = 'myplugin'           # unique slug
    title = 'My Plugin'         # human-readable
    description = 'One line.'

    def activate(self, app):
        """Called when plugin is enabled. Receive the Adw.Application."""

    def deactivate(self):
        """Called when plugin is disabled or app quits."""
```

---

## Coding standards

- Python 3.9+ compatible syntax (no 3.10+ union types with `|` in annotations).
- PEP 8 naming: `snake_case` for methods and variables, `PascalCase` for classes.
- Private methods prefixed with `_` (e.g., `_on_button_clicked`).
- Signal handler naming: `_on_<widget>_<signal>` (e.g., `_on_search_entry_changed`).
- No bare `except:` — always catch specific exceptions or at minimum `Exception as e`.
- Backend code must have no side-effects on import.
- Do **not** use `print()` for debug output — use Python `logging` module:
  ```python
  import logging
  log = logging.getLogger(__name__)
  log.debug("Processing file: %s", path)
  ```

---

## i18n

Translatable strings use `_()`:
```python
from gi.repository import GLib
_ = GLib.dgettext.bind('miaz')   # or via standard gettext
label = Gtk.Label(label=_("Document Organizer"))
```

Translation files live in `po/`. Update with:
```bash
ninja -C _build miaz-update-po
```

---

## GSettings schema

Schema ID: `io.github.t00m.MiAZ`  
Schema file: `data/io.github.t00m.MiAZ.gschema.xml`

```python
settings = Gio.Settings(schema_id='io.github.t00m.MiAZ')
# Bind widget property to setting:
settings.bind('some-key', widget, 'property', Gio.SettingsBindFlags.DEFAULT)
```

---

## Common tasks

### Add a new Libadwaita dialog
1. Create `MiAZ/frontend/dialogs/my_dialog.py` with a class extending `Adw.Dialog` or `Adw.AlertDialog`.
2. Import and instantiate from the relevant view; call `.present(parent)`.

### Add a new backend service
1. Create `MiAZ/backend/my_service.py` — no GTK imports.
2. Wire it into the application object in `main.py` or `app/__init__.py`.

### Add a new plugin
1. Create `MiAZ/plugins/myplugin/` with `plugin.py` implementing the `Plugin` contract.
2. Register in the plugin manager (see `backend/plugin_manager.py`).

### Add a translated string
1. Wrap with `_("...")`.
2. Run `ninja -C _build miaz-update-po` to regenerate `po/miaz.pot`.

### Run without installing
```bash
PYTHONPATH=. python -m MiAZ.main
```

---

## What to avoid

- Do **not** import GTK inside `backend/`.
- Do **not** block the GTK main loop — use threads + `GLib.idle_add()`.
- Do **not** use deprecated GTK3 widgets (`GtkListStore`, `GtkTreeView`, `GtkDialog` subclassing).
- Do **not** hardcode paths — use `pkgdatadir` from `MiAZ/__init__.py`.
- Do **not** rename files outside of the MiAZ rename pipeline — always go through the backend.
- Do **not** store application state in global module-level variables.

---

## Useful references

- [GNOME Developer Docs](https://developer.gnome.org/)
- [PyGObject API Reference](https://pygobject.gnome.org/reference/)
- [Libadwaita Widget Gallery](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/widget-gallery.html)
- [GNOME HIG](https://developer.gnome.org/hig/)
- [Flatpak docs](https://docs.flatpak.org/)
