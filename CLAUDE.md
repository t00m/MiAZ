# MiAZ — Personal Document Organizer

> App ID: `io.github.t00m.MiAZ` | License: GPL v3 | Repo: https://github.com/t00m/MiAZ

**Read `AGENTS.md` first** — it contains the full, accurate project reference.

## What MiAZ does

GTK4/Libadwaita desktop app that organises personal documents by enforcing a strict 7-field filename convention:

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
```

Example: `20240315-ES-HOU-BANKNAME-INV-Q1invoice-JOHNDOE.pdf`

**The directory is the database** — no SQLite, no external DB. Everything is derived from filenames.

## Architecture

### Layered: Backend (no GTK) → Services (GTK-aware) → Widgets (GTK/Adw)

**Backend** (`MiAZ/backend/`): Zero GTK imports. File I/O, config, models, logging, util.
**Services** (`MiAZ/frontend/desktop/services/`): GTK-aware, app lifecycle. Access via `app.get_service('name')`.
**Widgets** (`MiAZ/frontend/desktop/widgets/`): All GTK4+Adw widgets.

### GObject signals used across the project

| File | Signals |
|---|---|
| `backend/config.py` | `available-updated`, `used-updated` |
| `backend/util.py` | `filename-added`, `filename-deleted`, `filename-renamed` |
| `backend/watcher.py` | `repository-updated` |
| `backend/stats.py` | `stats-updated` |
| `backend/repository.py` | `repository-switched` |
| `frontend/app.py` | `application-started`, `application-finished` |
| `frontend/services/workflow.py` | `repository-switch-started`, `repository-switch-finished` |
| `frontend/widgets/workspace.py` | `workspace-loaded`, `workspace-view-updated`, `workspace-view-selection-changed`, `workspace-view-filtered` |
| `frontend/widgets/settings.py` | `settings-loaded` |

## Key patterns

- **Threading**: `threading.Thread` + `GLib.idle_add()` for UI marshal
- **List model (GTK4 MVC)**: `Gio.ListStore` → `Gtk.FilterListModel`/`Gtk.SortListModel` → `Gtk.SingleSelection`/`Gtk.MultiSelection` → `Gtk.ColumnView`
- **No GTK3**: no `GtkListStore`, `GtkTreeView`, `GtkDialog` subclassing
- **Python 3.9+**: no `X | Y` union syntax in annotations
- **Filechooser**: use `Gtk.FileDialog` (async, GTK4 API — not `Gtk.FileChooserDialog`)

## Plugin system

Uses **libpeas** (`Peas.Engine`) with two search paths:
- System: `~/.local/share/MiAZ/resources/plugins/` (19 built-in)
- User: `~/.MiAZ/opt/plugins/` (imported ZIPs)

Plugin contract: `MiAZExtension` subclass with `do_activate()` / `do_deactivate()`. See `AGENTS.md`.

## Build & install

```bash
./scripts/install/local/install_user.sh           # dev install
meson setup _build --prefix="$HOME/.local" && ninja -C _build && ninja -C _build install
PYTHONPATH=. python -m MiAZ.miaz                 # run without installing
```

## i18n

Translatable strings via `gettext`:
```python
from gettext import gettext as _
```
Translation files in `po/`. Update with `ninja -C _build miaz-update-po`.

## GSettings

Schema is **empty** — the app uses JSON configuration files in `<repo>/.conf/`.


