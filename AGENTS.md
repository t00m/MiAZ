# MiAZ,  Personal Document Organizer

> App ID: `io.github.t00m.MiAZ` | License: GPL v3 | Repo: https://github.com/t00m/MiAZ

## What MiAZ does

GTK4/Libadwaita desktop app that organises personal documents by enforcing a strict 7-field filename convention:

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
```

Example: `20240315-ES-HOU-BANKNAME-INV-Q1invoice-JOHNDOE.pdf`

**The directory is the database**,  no SQLite, no external DB.

## Tech stack

| Layer | Technology | Min version |
|---|---|---|
| Language | Python | 3.9 |
| GUI toolkit | GTK | 4.10 |
| GNOME style | Libadwaita | 1.6 |
| Python–GTK bindings | PyGObject | 3.50 |
| Embedded web | WebKitGTK | 6.0 |
| Build system | Meson + Ninja | 1.5.1 |
| Distribution | Flatpak | GNOME 50 runtime |
| i18n | gettext |,  |

## Repository layout

```
MiAZ/
├── AGENTS.md                     ← This file (AI context, read first)
├── CLAUDE.md                     ← Condensed companion (signal map, conventions)
├── MiAZ/                         ← Python package
│   ├── __init__.py               ← Package marker
│   ├── miaz.py                   ← Entry point (MiAZ class, main)
│   ├── env.in                    ← Environment template → env.py (meson-generated)
│   ├── backend/                  ← Business logic (NO GTK imports)
│   │   ├── config.py             ← MiAZConfig + 10 subclasses (App, Repo, Country, etc.)
│   │   ├── data.py               ← Placeholder (package marker)
│   │   ├── dr.py                 ← MiAZDR (disaster recovery / backup)
│   │   ├── log.py                ← MiAZLog (colored logging)
│   │   ├── models.py             ← MiAZItem, Country, Group, etc. (GObject models)
│   │   ├── repository.py         ← MiAZRepository (CRUD on file-based repo)
│   │   ├── stats.py              ← MiAZStats (document statistics)
│   │   ├── status.py             ← MiAZStatus (IntEnum: RUNNING=0, BUSY=1)
│   │   ├── util.py               ← MiAZUtil (file ops, JSON, normalization)
│   │   └── watcher.py            ← MiAZWatcher (filesystem monitor)
│   └── frontend/
│       └── desktop/
│           ├── app.py            ← MiAZApp(Adw.Application)
│           └── services/
│           │   ├── actions.py    ← MiAZActions
│           │   ├── dialogs.py    ← MiAZDialog, MiAZDialogAdd, MiAZDialogAddRepo
│           │   ├── factory.py    ← MiAZFactory (widget factory)
│           │   ├── help.py       ← MiAZHelp, MiAZShortcutsWindow
│           │   ├── icm.py        ← MiAZIconManager
│           │   ├── pluginsystem.py ← MiAZExtension, MiAZPlugin, MiAZPluginSystem
│           │   └── workflow.py   ← MiAZWorkflow (repo switching lifecycle)
│           └── widgets/
│               ├── about.py, button.py, columnview.py, configview.py
│               ├── dr.py, mainwindow.py, pages.py, pluginuimanager.py
│               ├── rename.py, searchbar.py, selector.py, settings.py
│               ├── sidebar.py, views.py, webbrowser.py, window.py
│               └── workspace.py
├── data/
│   └── resources/
│       ├── plugins/              ← Built-in Peas plugins (17 total)
│       ├── icons/                ← App icons (64 scalable + 257 flag SVGs)
│       ├── conf/                 ← 6 default config JSON files
│       ├── *.desktop.in          ← Desktop entry template
│       ├── *.metainfo.xml.in     ← AppStream metadata
│       └── *.gschema.xml         ← GSettings schema (5 keys, unused at runtime; app uses JSON)
├── po/                           ← Translations
├── meson.build                   ← Root Meson build file
├── meson_options.txt
├── pyproject.toml
└── io.github.t00m.MiAZ.json      ← Flatpak manifest
```

## Filename convention (core domain)

| # | Field | Format | Example |
|---|-------|--------|---------|
| 1 | Date | `%Y%m%d` | `20240315` |
| 2 | Country | ISO-3166 Alpha-2 | `ES` |
| 3 | Group | 3-char code | `HOU` |
| 4 | SentBy | Free (no hyphens) | `BANKNAME` |
| 5 | Purpose | 3-char code | `INV` |
| 6 | Concept | Free text | `Q1invoice` |
| 7 | SentTo | Free (no hyphens) | `JOHNDOE` |

Separator: `-`. Field index mapping in `MiAZ/backend/models.py`:
```python
Field = {Date: 0, Country: 1, Group: 2, SentBy: 3, Purpose: 4, Concept: 5, SentTo: 6}
```

## Architecture

### Layered: Backend (no GTK) → Services (GTK-aware) → Widgets (GTK/Adw)

**Backend** (`MiAZ/backend/`): Zero GTK imports. File I/O, config, models, logging, util.
- `MiAZConfig` signals: `available-updated`, `used-updated`
- `MiAZUtil` signals: `filename-added`, `filename-deleted`, `filename-renamed`
- `MiAZRepository` signals: `repository-switched`
- `MiAZWatcher` signals: `repository-updated`
- `MiAZStats` signals: `stats-updated`

**Services** (`MiAZ/frontend/desktop/services/`): GTK-aware, app lifecycle.
- Registered via `app.set_service('name', instance)` in `MiAZApp.__init__`
- Access via `app.get_service('name')`
- Available services: `util`, `icons`, `factory`, `actions`, `dialogs`, `workflow`, `dr`, `repo`, `plugin-system`, `watcher`, `theme`

**Widgets** (`MiAZ/frontend/desktop/widgets/`): All GTK4+Adw widgets.

**App signals** (`MiAZApp`): `application-started`, `application-finished`
**Actions signals** (`MiAZActions`): `settings-loaded`, `rename-dialog-built`
**Settings signals** (`MiAZAppSettings`): `settings-loaded`
**PluginSystem signals** (`MiAZPluginSystem`): `plugins-updated`
**Workflow signals**: `repository-switch-started`, `repository-switch-finished`
**Workspace signals**: `workspace-loaded`, `workspace-view-updated`, `workspace-view-selection-changed`, `workspace-view-filtered`

### Workspace layout

`MiAZWorkspace` (`Gtk.Box VERTICAL`) contains an `Adw.InlineViewSwitcher` + `Adw.ViewStack`:

```
MiAZWorkspace (Gtk.Box VERTICAL)
├── Adw.InlineViewSwitcher        ← tab bar (registered as 'workspace-view-switcher')
└── Adw.ViewStack                  ← page area (get_stack())
    ├── [page 'workspace-default'] ← Documents columnview (always present)
    └── [page ...]                 ← plugin-added pages
```

**Public API on MiAZWorkspace:**
- `get_stack()` → `Adw.ViewStack`
- `get_view_switcher()` → `Adw.InlineViewSwitcher`
- `add_stack_page(widget, name, title, icon_name=None)` → registers a new page
- `show_stack_page(name)` → switches to page by name
- `is_loaded()` → `bool`, true after workspace is configured

**Plugin helper on MiAZPlugin:**
```python
self.plugin.add_workspace_page(my_widget, 'my-view', _('My View'), 'my-icon')
```

**Workspace page lifecycle (activate / deactivate / reactivate):**

PluginSystem creates a **fresh plugin instance** per activation. Pages added to the workspace stack must survive across cycles:

1. **Activation** → `startup()`: call `stack.get_child_by_name('notes-all')` to detect a hidden page from a prior instance. If found, reuse it (`page.set_visible(True)`, update `store`/`backup` refs). If not, create and add via `add_workspace_page()`.
2. **Deactivation** → `do_deactivate()`: hide the page via `page.set_visible(False)`,  it stays in the `Adw.ViewStack` but disappears from the `InlineViewSwitcher`.
3. **Reactivation** → same as activation: the hidden page is found by name and shown again.

This avoids the "duplicate child name in AdwViewStack" warning.

### Startup flow

1. `MiAZ.miaz.py:MiAZ.run()` → creates `MiAZApp(Adw.Application)` → `app.set_env(ENV)`
2. `app._on_activate()` → creates `MiAZPluginSystem` → `_setup_ui()` → `workflow.switch_start()`
3. `switch_start()` → `repository.load()` → `app.load_plugins()` → `switch_finish()`
4. `switch_finish()` → creates `MiAZWatcher`, sets up workspace page

## Plugin system

### Location
- **System** (bundled): `~/.local/share/MiAZ/resources/plugins/` (17 plugins)
- **User** (imported): `~/.MiAZ/opt/plugins/`

### Discovery
Uses **libpeas** (`Peas.Engine`) with a direct-import fallback for systems missing the Python loader RPM. Engine is fed both search paths at startup. Plugin index is cached at `~/.MiAZ/var/cache/index-plugins.json`.

### Plugin contract

A plugin consists of two required files:

```
MiAZPluginName/
├── plugin_name.plugin           ← Peas metadata (INI)
└── plugin_name.py               ← Python implementation
```

**`.plugin` file:**
```ini
[Plugin]
Module=plugin_name
Name=MiAZPluginName
Loader=python
Description=One line description
Authors=Tomás Vírseda <tomasvirseda@gmail.com>
Copyright=Copyright © 2026 Tomás Vírseda
Website=http://github.com/t00m/MiAZ
Version=0.1
Category=Integration and Interoperability
Subcategory=API Connectors
```

Valid categories (with subcategories):
- `Data Management`: Import, Export, Backup, Restore, Single mode, Batch mode, Synchronisation, Migration, Deletion
- `Content Organisation`: Tagging and Classification, Search and Indexing, Metadata Management
- `Visualisation and Diagrams`: Diagram Creation, Data Visualisation, Dashboard Widgets, Document Viewers
- `Security and Privacy`: Encryption/Decryption, Access Control, Audit and Logging
- `Automation and Workflow`: Task Automation, Workflow Management, Notification Systems
- `Integration and Interoperability`: API Connectors, Third-Party Service Integration, Communication Tools
- `Customisation and Personalisation`: Themes and UI Customisation, Templates, Language Packs
- `Analytics and Reporting`: Usage Analytics, Document Statistics, Custom Reports
- `Collaboration`: Real-time Collaboration, Version Control, Comments and Annotations
- `Content Editing and Formatting`: Advanced Editors, Formatting Tools, Conversion Tools
- `Support and Help`: Guides and Tutorials, Troubleshooting Tools, User Feedback
- `Archiving and Compliance`: Long-Term Archiving, Compliance Checkers, Retention Policies
- `ETL and Data Processing`: Data Extraction, Data Transformation, Data Loading, Workflow Automation, Data Quality
- `Artificial Intelligence`: Text Analysis, Document AI, Predictive Analytics, Recommendation Systems, AI Assistants, Model Integration
- `Others`: Miscelanea

**Python file contract:**
```python
plugin_info = {
    'Module': 'module_name', 'Name': 'PluginName', 'Loader': 'Python3',
    'Description': '...', 'Authors': '...', 'Copyright': '...',
    'Website': '...', 'Help': '...', 'Version': '...',
    'Category': '...', 'Subcategory': '...'
}

class MyPlugin(MiAZExtension):
    __gtype_name__ = 'MyPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        self.srvdlg = self.app.get_service('dialogs')
        self.factory = self.app.get_service('factory')
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect('workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            menuitem = self.plugin.get_menu_item(callback=self._on_activate)
            self.plugin.install_menu_entry(menuitem)
            self.plugin.set_started(True)
```

**`MiAZPlugin` helper key methods:**
- `register(plugin_obj, info_dict)`,  stores widget reference, creates `conf/` and `data/` dirs
- `get_config_dir()` → `<repo>/.conf/plugins/<Name>/conf/`
- `get_data_dir()` → `<repo>/.conf/plugins/<Name>/data/`
- `get_config_key(key)` / `set_config_key(key, value)`,  JSON config persistence
- `get_menu_item(callback)` → `Gio.MenuItem` (registered as app action)
- `install_menu_entry(menuitem)`,  appends to workspace menu under category/subcategory
- `add_workspace_page(widget, name, title, icon_name=None)`,  registers a page on the workspace's `Adw.ViewStack`
- `get_logger()` → named logger `Plugin.<Name>`
- `get_name()` → plugin name string
- `get_widget_name()` → `plugin-<Module>` identifier
- `get_plugin_info_dict()` → full plugin info `dict`
- `get_plugin_info_key(key)` → specific info key value
- `menu_item_loaded()` → `bool`, checks if menu item is registered
- `set_started(True/False)` / `started()` → toggle/query started state

## Environment paths

| Variable | Path |
|---|---|---|
| `GPATH['ROOT']` | `~/.local/share/MiAZ` |
| `GPATH['PLUGINS']` | `~/.local/share/MiAZ/resources/plugins` |
| `LPATH['ROOT']` | `~/.MiAZ` |
| `LPATH['PLUGINS']` | `~/.MiAZ/opt/plugins` |
| `LPATH['CACHE']` | `~/.MiAZ/var/cache` |
| `LPATH['LOG']` | `~/.MiAZ/var/log` |
| `LPATH['VAR']` | `~/.MiAZ/var` |
| `LPATH['CONF']` | `~/.MiAZ/etc` |
| `LPATH['REPOS']` | `~/.MiAZ/var/repos` |
| `LPATH['DB']` | `~/.MiAZ/var/db` |
| `LPATH['TMP']` | `~/.MiAZ/var/tmp` |
| `LPATH['REPO']` | `repository root` |

## Coding conventions

- **Python 3.9+ compatible**,  no `X | Y` union syntax in annotations
- **PEP 8**: `snake_case` methods/vars, `PascalCase` classes, `_` prefix for private
- **Signal handlers**: `_on_<widget>_<signal>`
- **No bare `except:`**,  always catch `Exception as e` or specific types
- **No `print()`**,  use `logging.getLogger(__name__)`
- **Backend**: no GTK imports, no side-effects on import
- **Frontend**: no direct file I/O, always call backend APIs
- **Threading**: `threading.Thread` + `GLib.idle_add()` for UI marshal
- **GTK4 patterns**: `Gio.ListStore` → `Gtk.FilterListModel` → `Gtk.SingleSelection` → `Gtk.ColumnView`
- **No GTK3**: no `GtkListStore`, `GtkTreeView`, `GtkDialog` subclassing

## Build & install

```bash
# Developer install (user scope)
./scripts/install/local/install_user.sh

# Manual Meson
meson setup _build --prefix="$HOME/.local"
ninja -C _build
ninja -C _build install

# Uninstall
./scripts/uninstall/uninstall_user.sh

# Run without installing
PYTHONPATH=. python -m MiAZ.miaz
```

## Existing plugins (17)

| Plugin | Category | Purpose |
|---|---|---|---|
| HelloWorld | Support and Help / Guides and Tutorials | Example plugin |
| MiAZAddFromDir | Data Management / Import | Import all files from a directory |
| MiAZColumnVisibility | Customisation and Personalisation / User Interface | Toggle column visibility |
| MiAZCopy2Clipboard | Data Management / Export | Copy file info to clipboard |
| MiAZExport2CSV | Data Management / Export | Export to CSV |
| MiAZExport2Dir | Data Management / Export | Export to directory |
| MiAZExport2Text | Data Management / Export | Export to text file |
| MiAZExport2Zip | Data Management / Export | Export to ZIP archive |
| MiAZImportDoc | Data Management / Import | Import single document |
| MiAZImportFromScan | Data Management / Import | Import from scanner |
| MiAZImportFromZip | Data Management / Import | Import from ZIP file |
| MiAZMassRename | Data Management / Batch mode | Batch rename documents |
| MiAZPeriodicity | Content Organisation / Tagging and Classification | Periodicity analysis |
| MiAZProjectMgt | Content Organisation / Tagging and Classification | Project management |
| MiAZSidebarTB | Customisation and Personalisation / User Interface | Sidebar toolbar |
| MiAZWSFont | Customisation and Personalisation / User Interface | Workspace font settings |
| MiAZWorkspaceToggleView | Customisation and Personalisation / User Interface | Toggle workspace view |
