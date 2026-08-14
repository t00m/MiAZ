# MiAZ,  Personal Document Organizer

> App ID: `io.github.t00m.MiAZ` | License: GPL v3 | Repo: https://github.com/t00m/MiAZ

**Read `AGENTS.md` first**,  it contains the full, accurate project reference.

## What MiAZ does

GTK4/Libadwaita desktop app that organises personal documents by enforcing a strict 7-field filename convention:

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
```

Example: `20240315-ES-HOU-BANKNAME-INV-Q1invoice-JOHNDOE.pdf`

**The directory is the database**,  no SQLite, no external DB. Everything is derived from filenames.

## Architecture

### Layered: Backend (no GTK) → Services (GTK-aware) → Widgets (GTK/Adw)

**Backend** (`MiAZ/backend/`): No GTK/Adw/Gdk widget imports. File I/O, config, models, logging, util. `GObject`/`GLib`/`Gio` are allowed and used on purpose: the backend exposes its events through GObject signals (see the signals table below), which is the backend/frontend contract.
**Services** (`MiAZ/frontend/desktop/services/`): GTK-aware, app lifecycle. Access via `app.get_service('name')`.
**Widgets** (`MiAZ/frontend/desktop/widgets/`): All GTK4+Adw widgets.

### GObject signals used across the project

| File | Signals |
|---|---|
| `backend/config.py` | `available-updated`, `used-updated` (both carry the set of changed keys, `None` if unknown); `MiAZConfigApp`: `repo-settings-updated-app` |
| `backend/util.py` | `filename-added`, `filename-deleted`, `filename-renamed` |
| `backend/watcher.py` | `repository-updated` |
| `backend/stats.py` | `stats-updated` |
| `backend/repository.py` | `repository-switched` |
| `frontend/app.py` | `application-started`, `application-finished` |
| `frontend/services/actions.py` | `settings-loaded`, `rename-dialog-built` |
| `frontend/services/workflow.py` | `repository-switch-started`, `repository-switch-finished` |
| `frontend/services/pluginsystem.py` | `plugins-updated` |
| `frontend/services/dialogs.py` | `MiAZWindowDialog`: `response`, `closed`; `MiAZDialogAdd`/`MiAZDialogAddRepo`: `response` |
| `frontend/widgets/workspace.py` | `workspace-loaded`, `workspace-view-updated`, `workspace-view-selection-changed`, `workspace-view-filtered` |
| `frontend/widgets/rename.py` | `MiAZRenameDialog`: `fields-changed` |
| `frontend/widgets/configview.py` | `MiAZPlugins`: `plugins-downloaded` |
| `frontend/widgets/settings.py` | `settings-loaded` |

## Key patterns

- **Repository switching**: `MiAZWorkflow.switch_start(repo_id=None)`, in place, no restart. It unloads the plugins of the repository being left (the enabled set is per repository), resolves the target with `repository.use()` (which does **not** write `App.current`), loads the new configuration and reloads the workspace on `application-started`. Setting the default is a separate decision, taken by the checkbox in the Settings confirmation dialog. Anything naming the repository to the user calls `repository.get_active_id()`, never `App.current`: they differ after a switch that did not set the default. See `AGENTS.md` for the full order.
- **CLI**: `frontend/console/` is a headless command line (`miaz search`, `miaz repos`). `MiAZConsoleApp` registers only `util`, `repo` and `index`; filtering is `DocumentQuery.matches`, never a condition written twice; repository selection uses `MiAZRepository.use()`, which does not rewrite `current`. It must never import GTK or `frontend.desktop` (enforced by `tests/test_boundaries.py`). Results go to stdout, diagnostics to stderr. The console shows INFO and above; the log file keeps DEBUG, one file per run with the previous one as `MiAZ.last.log`. `MIAZ_DEBUG=1` shows DEBUG on the console.
- **Threading**: `threading.Thread` + `GLib.idle_add()` for UI marshal
- **List model (GTK4 MVC)**: Workspace chain is `Gio.ListStore` → `Gtk.SortListModel` → `Gtk.FilterListModel` → `Gtk.MultiSelection` → `Gtk.ColumnView` (`widgets/columnview.py`)
- **No GTK3**: no `GtkListStore`, `GtkTreeView`, `GtkDialog` subclassing
- **Python 3.9+**: no `X | Y` union syntax in annotations
- **Filechooser**: use `Gtk.FileDialog` (async, GTK4 API,  not `Gtk.FileChooserDialog`)
- **Markdown view**: `MiAZMarkdownView` (`frontend/desktop/widgets/markdownview.py`) renders Markdown as themed HTML in a read-only `WebKit.WebView`. `set_markdown(text)` to update; `on_command` callback handles `miazcmd:` links. Used by MiAZNotes (view mode) and MiAZAIChat. Reuse it for any read-only Markdown display.
- **Document tabs**: the single-document rename dialog (`widgets/rename.py`) is an `Adw.ViewStack` whose first page is `Fields`. Plugins add tabs through the `document-tabs` service (`services/doctabs.py`) via `MiAZPlugin.register_document_tab(...)`; tab edits are held until the rename succeeds and are written by `apply(old_id, new_id)`. See `AGENTS.md` for the contract.
- **Mass rename**: core service `MiAZMassRename` (`frontend/desktop/services/massrename.py`, service `massrename`, formerly a plugin) sets one filename field across the selection. `build_menu` registers seven `massrename-*` actions and a shared `Gio.Menu`. The workspace headerbar shows the single-rename button for one selected document and a same-icon `Gtk.MenuButton` (the seven functions: Date, Country, Group, Purpose, Concept, Sent by, Sent to) for two or more; the same submenu is in the right-click selection menu. Concept uses a guided transform whose pure ops are module-level functions in that file; the Date dialog has a "Detect date from each file" checkbox (reuses `util.filename_guess_date`).

## Plugin system

Uses **libpeas** (`Peas.Engine`) with two search paths:
- System: `~/.local/share/MiAZ/resources/plugins/` (19 built-in with `.plugin` metadata)
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

The schema (`data/io.github.t00m.MiAZ.gschema.xml`) stores desktop window state only: `frontend/desktop/app.py` reads and writes `window-width`, `window-height`, and `window-maximized` through `Gio.Settings`. Everything else (the active repository, sidebar visibility, document/repo config) lives in JSON files in `<repo>/.conf/`, not in GSettings.

Document and repository configuration does **not** use GSettings. It lives in JSON files in `<repo>/.conf/`.


