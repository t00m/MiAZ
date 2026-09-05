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
| GNOME style | Libadwaita | 1.7 |
| Python–GTK bindings | PyGObject | 3.50 |
| Embedded web | WebKitGTK | 6.0 |
| Build system | Meson + Ninja | 1.5.1 |
| Distribution | deb / rpm / AppImage (native). Flatpak is deprecated | n/a |
| i18n | gettext | n/a |

## Repository layout

```
MiAZ/
├── AGENTS.md                     ← This file (AI context, read first)
├── MiAZ/                         ← Python package
│   ├── __init__.py               ← Package marker
│   ├── miaz.py                   ← Entry point (MiAZ class, main)
│   ├── env.in                    ← Environment template → env.py (meson-generated)
│   ├── backend/                  ← Business logic (no GTK/Adw widgets; GObject signals OK)
│   │   ├── config.py             ← MiAZConfig + subclasses, MiAZConfigStore (per repo)
│   │   ├── gate.py               ← UpdateGate (reference-counted refresh suspension)
│   │   ├── crash.py              ← console/log-only excepthook (install_backend_excepthook)
│   │   ├── data.py               ← Placeholder (package marker)
│   │   ├── dr.py                 ← MiAZDR (disaster recovery / backup)
│   │   ├── index.py              ← MiAZDocumentIndex (the parse: filename → MiAZItem)
│   │   ├── log.py                ← MiAZLog (colored logging)
│   │   ├── query.py              ← DocumentQuery (the workspace filter, as a value)
│   │   ├── tasks.py              ← run_in_background (thread + GLib.idle_add)
│   │   ├── models.py             ← MiAZItem, Country, Group, etc. (GObject models)
│   │   ├── repository.py         ← MiAZRepository (CRUD on file-based repo)
│   │   ├── stats.py              ← MiAZStats (document statistics)
│   │   ├── status.py             ← MiAZStatus (IntEnum: RUNNING=0, BUSY=1)
│   │   ├── util.py               ← MiAZUtil (file ops, JSON, normalization)
│   │   ├── watcher.py            ← MiAZWatcher (filesystem monitor)
│   │   └── webserver.py          ← MiAZWebServer (minimal static localhost HTTP server)
│   └── frontend/
│       ├── console/              ← Headless command line (no GTK, ever)
│       │   ├── app.py            ← MiAZConsoleApp (util + repo + index, nothing else)
│       │   └── cli.py            ← argparse, search and repos, three renderers
│       └── desktop/
│           ├── app.py            ← MiAZApp(Adw.Application)
│           └── services/
│           │   ├── actions.py    ← MiAZActions
│           │   ├── crash.py      ← MiAZCrashHandler (GUI crash dialog + excepthook)
│           │   ├── dialogs.py    ← MiAZDialog, MiAZWindowDialog, MiAZDialogAdd, MiAZDialogAddRepo
│           │   ├── massrename.py ← MiAZMassRename (core mass-rename service + menu)
│           │   ├── factory.py    ← MiAZFactory (widget factory)
│           │   ├── help.py       ← MiAZHelp, MiAZShortcutsWindow
│           │   ├── icm.py        ← MiAZIconManager
│           │   ├── importdoc.py  ← MiAZImportDoc (core add-document service + menu items)
│           │   ├── pluginsystem.py ← MiAZExtension, MiAZPlugin, MiAZPluginSystem
│           │   └── workflow.py   ← MiAZWorkflow (repo switching lifecycle)
│           └── widgets/
│               ├── about.py, assistant.py, browserpage.py, button.py
│               ├── columnview.py, configview.py, dr.py, mainwindow.py
│               ├── markdownview.py, pages.py, rename.py
│               ├── searchbar.py, selector.py, settings.py, sidebar.py
│               ├── views.py, webbrowser.py, window.py
│               └── workspace.py
├── data/
│   └── resources/
│       ├── plugins/              ← Built-in Peas plugins (20 with .plugin metadata)
│       ├── icons/                ← App icons (scalable + flag SVGs)
│       ├── conf/                 ← 6 default config JSON files (countries, extensions,
│       │                            groups, languages, people, purposes)
│       └── ...
├── data/io.github.t00m.MiAZ.gschema.xml  ← GSettings schema (window geometry; repo config stays in JSON)
├── data/io.github.t00m.MiAZ.metainfo.xml.in
├── flatpak/io.github.t00m.MiAZ.json      ← Flatpak manifest (+ .local.json for local builds)
├── scripts/packaging/            ← AppImage, deb, rpm, win, flatpak build scripts + build_all.sh
├── po/                           ← Translations
├── meson.build                   ← Root Meson build file (meson_version >= 1.5.1)
├── meson_options.txt
└── pyproject.toml
```

Two distinct WebKit widgets exist, do not confuse them:
- `widgets/browserpage.py` (`MiAZBrowserPage`): the **Browser page inside the Workspace** (`'workspace-browser'`). Lists plugin-published WWW sites and opens repo documents from `miazdoc:` links. This is the one plugins target.
- `widgets/webbrowser.py` (`MiAZWebBrowser`): a separate generic `WebKit.WebView` placed in the main window's outer `Gtk.Stack` as `'page-webbrowser'` (back/forward/URL bar). General-purpose, not the plugin surface.
- `widgets/markdownview.py` (`MiAZMarkdownView`): a reusable, read-only Markdown viewer. It converts Markdown to themed HTML (via `python-markdown`, with a `<pre>` fallback when that is missing) and renders it in a `WebKit.WebView` with a transparent background, a Copy/Select-All-only context menu, and external link handling. `set_markdown(text)` updates the content. Links open in the system browser, except `miazcmd:` links, which call the optional `on_command` callback so a host can map a Markdown link to an in-app action. Used by `MiAZNotes` to render the note body in view mode (edit mode keeps the raw Markdown `TextView`) and by the `MiAZAIChat` plugin to render the chat transcript with per-answer `miazcmd:save:<n>` links.

## Filename convention (core domain)

| # | Field | Typical format | Example |
|---|-------|--------|---------|
| 1 | Date | `%Y%m%d` (conventional, not enforced) | `20240315` |
| 2 | Country | user-defined code (often ISO-3166) | `ES` |
| 3 | Group | user-defined code | `HOU` |
| 4 | SentBy | user-defined code | `BANKNAME` |
| 5 | Purpose | user-defined code | `INV` |
| 6 | Concept | free text (underscores for spaces) | `Q1invoice` |
| 7 | SentTo | user-defined code | `JOHNDOE` |

Separator: `-`. Field index mapping in `MiAZ/backend/models.py`:
```python
Field = {Date: 0, Country: 1, Group: 2, SentBy: 3, Purpose: 4, Concept: 5, SentTo: 6}
```

### Validation is structural only (changed)

`util.filename_validate(doc)` is a **purely structural** check: it returns `True`
when `util.get_fields(doc)` yields exactly 7 **non-empty** fields. It does NOT
check the date format or a fixed country set anymore. Field *values* are
user-defined and repo-relative (countries can be invented and enabled, dates may
follow several patterns), so value validity is decided per field by the Workspace
parser (`_parse_files_worker` in `widgets/workspace.py`): each value is checked
against the enabled config (`config.exists_used`) or, for dates,
`filename_date_human_simple`; anything unknown flags the document for **Review**
(Pending). Helpers:
- `util.get_fields(filename)` → `[date, country, group, sentby, purpose, concept, sentto]`. Strips path + extension at the last dot and **merges hyphenated tail parts back into SentTo** (so a hyphen inside Concept/SentTo and directory hyphens are tolerated).
- `util.filename_is_normalized(name)` → `len(name.split('-')) == 7` (cheap stem check; still used by `MiAZInsights` and `filename_normalize`).

## Architecture

### Layered: Backend (no GTK) → Services (GTK-aware) → Widgets (GTK/Adw)

**Backend** (`MiAZ/backend/`): No GTK/Adw/Gdk widget imports. File I/O, config, models, logging, util. `GObject`/`GLib`/`Gio` are allowed and used on purpose: the backend exposes its events through GObject signals, which is the backend/frontend contract.
- `MiAZConfig` signals: `available-updated`, `used-updated` (both carry the set of keys that changed, or `None` when the previous contents could not be read)
- `MiAZUtil` signals: `filename-added`, `filename-deleted`, `filename-renamed`
- `MiAZRepository` signals: `repository-switched`
- `MiAZWatcher` signals: `repository-updated`
- `MiAZStats` signals: `stats-updated`
- `MiAZDocumentIndex` signals: `index-loaded`, `index-changed`

**The command line** (`MiAZ/frontend/console/`) is the proof that the layering is
real. `MiAZConsoleApp` (`console/app.py`) provides the six things the backend
asks of an application object (`get_service`, `get_env`, `get_config`,
`get_config_dict`, `connect`, service registration) and registers three
services: `util`, `repo` and `index`. No factory, no dialogs, no plugin system,
no window. `console/cli.py` holds argparse, the `search` and `repos` commands and
the three output renderers.

Two rules keep it honest, both enforced by `tests/test_boundaries.py`:

- Nothing under `frontend/console/` may import Gtk, Adw, Gdk, Pango, GdkPixbuf,
  WebKit or `MiAZ.frontend.desktop`. The command line has to run where there is
  no display.
- The command line writes no filter conditions of its own. Flags map onto
  `DocumentQuery` fields and filtering is `query.matches(item)`, the same call
  the workspace makes, so the two cannot disagree about what a search means.

Choosing a repository goes through `MiAZRepository.use(repo_id=None, path=None)`,
which points the instance at a repository **without** writing `current` into the
application configuration. Writing it is how the desktop app switches, and a
command that did the same would change which repository the window opens next
time. Diagnostics go to stderr (never stdout, which carries results). The console
shows INFO and above; DEBUG goes only to the log file, which keeps everything.
`MIAZ_DEBUG=1` puts DEBUG back on the console, and `log.set_console_level()`
raises the bar further, which is how a command prints results rather than a
startup narration. Each run starts a fresh `~/.MiAZ/var/log/MiAZ.log` and keeps
the run before it as `MiAZ.last.log`.

**The document index** (`backend/index.py`, service `index`) owns the only path
from a filename to a `MiAZItem`. `build_item(filename)` is that path; `reload()`
runs it over the whole repository and `apply_change(path, event, other=None)`
over one file, so the full scan and the incremental update cannot disagree
(`tests/test_index.py::test_incremental_and_full_scan_agree` enforces it). It
also owns the description cache, the field index, the invalid list and the
pending set. Read documents from here, not from `workspace.view.store`:

```python
index = app.get_service('index')
for item in index.documents():      # every MiAZItem, unfiltered
    ...
index.pending()                     # flagged for review
index.document('20240315-ES-...pdf')
```

`index-changed` carries `[(action, payload), ...]` where `action` is `add`,
`update` or `remove`; payload is a `MiAZItem` for the first two and a filename
for `remove`. `apply_change` returns `False` when the caller must fall back to a
full `reload()`, which is the case for a name that still has to be normalized on
disk. `reload()` emits on the calling thread, so a caller running it off the main
loop must marshal the result back itself.

**Services** (`MiAZ/frontend/desktop/services/`): GTK-aware, app lifecycle.
- Registered via `app.set_service('name', instance)` in `MiAZApp._on_activate` (returns the instance)
- Access via `app.get_service('name')`
- Registration order: `crash`, `util`, `icons`, `factory`, `dialogs`, `actions`, `workflow`, `dr`, `progress`, `secrets`, `venv`, `extlibs`, `webserver`, `repo`, `index`, `massrename`, `importdoc` (early); then `plugin-system` and `theme` (`Gtk.IconTheme`) once the window exists. `massrename` and `importdoc` are registered before the window is built because each builds its menu item(s) in `__init__` (`massrename-menu` widget; `importdoc.menuitem`) that the headerbar consumes when it is constructed.

- `progress` (`services/progress.py`): runs one long operation at a time behind a modal progress dialog. `run(work, title, message='', parent=None, on_close=None)` sends `work(report)` to a worker thread through `run_in_background`, makes `window-mainbox` insensitive, and presents an `Adw.AlertDialog` whose Close response is disabled (and `can_close` off) until the work ends. `report(text, fraction=None)` may be called from the worker: it marshals with `GLib.idle_add`, and a fraction of `None` pulses the bar. Whatever `work` returns is shown as the outcome; the UI comes back and `on_close(ok, result)` runs when the user closes the dialog, not when the work ends. Returns the dialog, or `None` when one is already running. Only the window *content* is disabled, never the window: libadwaita hosts dialogs beside that content, so disabling the window would disable the dialog too. Used by Backup & Restore (`widgets/dr.py`, six operations) and by MiAZNotes (three entry points). Covered by `tests/ui/test_ui_progress.py`.

**Widgets** (`MiAZ/frontend/desktop/widgets/`): All GTK4+Adw widgets.

**Signal map (verified):**

| Emitter | Signals |
|---|---|
| `MiAZApp` (app.py) | `application-started`, `application-finished` |
| `MiAZActions` (actions.py) | `settings-loaded`, `rename-dialog-built` |
| `MiAZAppSettings` / `MiAZRepoSettings` (settings.py) | `settings-loaded` |
| `MiAZPluginSystem` (pluginsystem.py) | `plugins-updated` |
| `MiAZPlugins` config view (configview.py) | `plugins-downloaded` |
| `MiAZWorkflow` (workflow.py) | `repository-switch-started`, `repository-switch-finished` |
| `MiAZWorkspace` (workspace.py) | `workspace-loaded`, `workspace-view-updated`, `workspace-view-selection-changed`, `workspace-view-filtered` |
| `MiAZRenameDialog` (rename.py) | `fields-changed` |
| `MiAZConfig` (config.py) | `available-updated` (set), `used-updated` (set) |
| `MiAZConfigApp` (config.py) | `repo-settings-updated-app` |
| `MiAZUtil` (util.py) | `filename-added`, `filename-deleted`, `filename-renamed` |
| `MiAZWatcher` (watcher.py) | `repository-updated` |
| `MiAZRepository` (repository.py) | `repository-switched` |
| `MiAZStats` (stats.py) | `stats-updated` |
| `MiAZWindowDialog` (dialogs.py) | `response` (str), `closed` |
| `MiAZDialogAdd` / `MiAZDialogAddRepo` (dialogs.py) | `response` (str) |

### Holding the workspace still during bulk work

Importing twenty documents should refresh the view once, not twenty times. Take a handle from `workspace.suspend_updates()`; every `update()` asked for meanwhile is collapsed into a single refresh when the last holder releases.

```python
with workspace.suspend_updates():
    for path in files:
        util.filename_import(path, target)
    workspace.update()          # recorded, runs once on exit
```

Work that finishes on another thread keeps the handle and releases it from the main loop:

```python
suspend = workspace.suspend_updates()
threading.Thread(target=self._import, args=(paths, suspend), daemon=True).start()
# ...at the end of the worker:
GLib.idle_add(workspace.update)     # ask while still suspended
GLib.idle_add(suspend.release)
```

It is reference counted (`backend/gate.py`), so two plugins working at once do not reopen the gate on each other, and `release()` is idempotent. This replaced `app.set_status(MiAZStatus.BUSY)`, which was one process-wide flag reset unconditionally by all six of its setters.

**`MiAZStatus` now means one thing only**: `BUSY` says a repository is being loaded or switched, and only `MiAZWorkflow` sets it. Do not use it to suppress refreshes. (`MiAZWatcher` keeps a separate `self.status` for its own internal state; same enum, unrelated.)

### Configuration ownership

A repository's eight configurations (`Country`, `Group`, `Purpose`, `Concept`, `SentBy`, `SentTo`, `Person`, `Plugin`) belong to a **`MiAZConfigStore`** (`backend/config.py`), built by `repository.load()` and disposed when another repository is loaded. Read them the usual way:

```python
config = app.get_config('Country')                    # unchanged; the store publishes here
store = app.get_service('repo').get_config_store()    # when you want the store itself
```

The store also owns the in-memory cache the configs read through, and hands the *same* dict to all eight. That matters because `SentBy`, `SentTo` and `Person` all point their available pool at `people-available.json`, so divergent copies drop each other's entries. It used to be a class attribute on `MiAZConfig`, which shared correctly but never expired, so a repository switched away from was read from the copy cached before the switch. `dispose()` is what ends that lifetime.

`App` and `Repository` are app-scoped, not repo-scoped: they are built in `MiAZApp.set_env()` and keep their own caches.

A plugin subclassing `MiAZConfig` for its own vocabulary (`MiAZProjectMgt`, `MiAZPeriodicity`) gets a fresh per-instance cache, which is right: the plugin is re-activated on a repository switch, so its config is rebuilt with it.

### Workspace layout

`MiAZWorkspace` (`Gtk.Box VERTICAL`) contains an `Adw.InlineViewSwitcher` + `Adw.ViewStack`:

```
MiAZWorkspace (Gtk.Box VERTICAL)
├── Adw.InlineViewSwitcher        ← tab bar (registered as 'workspace-view-switcher')
├── filter-tags revealer          ← removable chips for the active sidebar filters
└── Adw.ViewStack                  ← page area (get_stack())
    ├── [page 'workspace-default'] ← Documents columnview (always present, accepts dropped files)
    ├── [page 'workspace-browser'] ← built-in Browser page (MiAZBrowserPage, always present)
    └── [page ...]                 ← plugin-added pages
```

**Public API on MiAZWorkspace:**
- `get_stack()` → `Adw.ViewStack`
- `get_view_switcher()` → `Adw.InlineViewSwitcher`
- `add_stack_page(widget, name, title, icon_name=None)` → adds a page, replacing any other child already holding that name
- `get_stack_page(name)` / `remove_stack_page(name)` → takes the page out of the stack, freeing its name
- `show_stack_page(name)` → switches to page by name
- `clear_filters()` → resets every filter control (search, concept, all dropdowns) and refilters once
- `get_workspace_view()` → the `MiAZColumnView` (also reachable as `workspace.view`)
- `is_loaded()` → `bool`, true after workspace is configured

**Dropping files on the Documents page:** `_setup_drop_target()` installs a `Gtk.DropTarget` for `Gdk.FileList` / `Gdk.DragAction.COPY` on the documents page content box (registered as `workspace-drop-target`), not on the whole workspace: dropping on the Browser page or anywhere else in the window does nothing, so the gesture means what it looks like. `enter`/`leave` add and remove the `miaz-drop-active` CSS class (installed once, next to the filter-tag CSS); `drop` maps the `Gio.File`s to local paths (a remote URI gives `None`, which the import reports as failed) and hands them to `importdoc.import_dropped()`. See "Add documents".

### Filtering the Documents view (programmatic)

The active filter is a **`DocumentQuery`** (`backend/query.py`), a dataclass whose `matches(item)` is pure: no widget access, no app access. `MiAZWorkspace._read_query()` builds one from the filter widgets once per pass and `_do_filter_view_main` just calls `matches`. Prefer it over poking the widgets:

```python
from MiAZ.backend.query import ANY, DATE_RANGE, DocumentQuery

workspace = app.get_widget('workspace')
query = DocumentQuery(sentby='BANKNAME', concept='invoice')
workspace.set_query(query)                 # refilters and emits workspace-view-filtered
workspace.show_stack_page('workspace-default')
```

`set_query` does not rewrite the filter widgets, so the next widget change rebuilds the query from them; call `clear_filters()` first for a clean base. `get_query()` returns the current one. `to_dict()` / `from_dict()` round-trip through JSON.

To adjust the query the widgets produced rather than replace it, register a hook:

```python
def _adjust_query(self, query):
    if self._project_selected() is not None:
        query.ignore_date = True      # show members whatever their date
        query.ignore_active = True    # ...and whatever their field values

self.workspace.register_query_hook('projects', self._adjust_query)
# in do_deactivate: self.workspace.unregister_query_hook('projects')
```

Use `register_filter_view(name, callback)` when you need an extra condition ANDed in per item, and `register_query_hook` when you need to relax one of the built-in checks. `MiAZProjectMgt` uses both.

The Documents page itself is a `Gtk.ColumnView` fed by `Gio.ListStore` → `Gtk.FilterListModel` with a single composite filter callback (`_do_filter_view`). The filter widgets stay registered in the app's widget registry:

- `app.get_widget('searchentry')` → free-text search across all fields.
- `app.get_widget('searchentry-concept')` → substring filter on the Concept field; `set_text(...)` triggers a refilter (connected to `changed`).
- `app.get_widget('ws-dropdowns')` → dict of the five field dropdowns keyed by GType name: `Country`, `Group`, `SentBy`, `Purpose`, `SentTo` (plus `Date`). Each dropdown's model holds items whose `.id` is the field code (and an `'Any'` / `'None'` sentinel). Select a value by matching `.id` then `dropdown.set_selected(pos)`; this fires `notify::selected-item` and refilters automatically.

```python
# Filter Documents to one sender, then bring the page forward.
workspace = app.get_widget('workspace')
workspace.clear_filters()
dd = (app.get_widget('ws-dropdowns') or {}).get('SentBy')
model = dd.get_model()
for i in range(model.get_n_items()):
    if model.get_item(i).id == 'BANKNAME':
        dd.set_selected(i)            # triggers refilter
        break
workspace.show_stack_page('workspace-default')
```

### Iterating documents in code

- `workspace.view.store` → `Gio.ListStore` of all `MiAZItem`s (unfiltered).
- `workspace.view.filter_model` → only what is currently visible.
- `MiAZItem` fields: `id` (filename), `date`, `country`, `group`, `sentby_id`, `purpose`, `subtitle` (the Concept field), `sentto_id`, the `*_dsc` human-readable descriptions, `active` (valid per config), `extension`.
- Map a field code to its display name with `app.get_config('SentBy').load_used()` → `{code: description}` (same for `Country`, `Group`, `Purpose`, `SentTo`).
- Or, outside the view: `util.get_fields(filename)` → `[date, country, group, sentby, purpose, concept, sentto]`; gate on `util.filename_is_normalized(stem)`.

**Plugin helper on MiAZPlugin:**
```python
self.plugin.add_workspace_page(my_widget, 'my-view', _('My View'), 'my-icon')
```

**Workspace page lifecycle: the plugin system owns the page.**

PluginSystem creates a fresh plugin instance per activation, so a plugin cannot remember what it added last time. It does not need to. `add_workspace_page` records the page against the plugin, and `unload_plugin` removes it, next to where it already removes that plugin's web content and rename-dialog tabs.

So a page-adding plugin builds a page in `startup()` and does nothing about it in `do_deactivate()`:

```python
def startup(self, *args):
    self._page = MyView(self.app)
    self.plugin.add_workspace_page(self._page, 'my-view', _('My View'), 'my-icon')

def do_deactivate(self):
    self._page = None          # the plugin system removes the page itself
```

Earlier versions required the plugin to hide the page on deactivate and find it by name on the way back, to dodge a "duplicate child name in AdwViewStack" warning. That is gone: `remove_stack_page` now removes the child instead of hiding it, so the name is free and adding a fresh page just works. Guard any late-firing handler with `if self._page is not None`.

This is a helper, not a restriction. `workspace.get_stack()` still returns the real `Adw.ViewStack`, and a plugin that wants to manage its own pages there can.

**Contributing to the sidebar and the header bar** works the same way. The plugin system detaches whatever these hand it, so `do_deactivate` has nothing to undo:

```python
# A row in the sidebar's plugin section.
self.plugin.add_sidebar_widget(row, widget_key=MY_ROW_ID)

# A button in the header bar; position is 'left' or 'right'.
self.plugin.add_headerbar_widget(button, position='left', widget_key=MY_BUTTON_ID)

# A filter dropdown, wired the way the built-in ones are: sized, joined to the
# shared size group, appended to the 'plugin-dropdowns' list the workspace
# filter pass reads, registered under 'plugin-<Name>-dropdown', and shown
# behind the plugin's icon.
self.plugin.add_sidebar_dropdown(dropdown)
```

Pass `widget_key` whenever the plugin looks the widget up later. The key is unregistered on unload along with the widget: detaching a widget but leaving its key is a trap, because the next activation finds the old widget, concludes it has nothing to do, and never re-attaches anything. `MiAZFullscreen` had exactly that bug, and its button did not come back after a disable/enable cycle.

Reaching `sidebar-plugin-section`, `headerbar-left-box` and friends directly still works. These only save writing the teardown.

**Menu entries are recorded, not rebuilt by rerunning startup.** `install_menu_entries(callbacks)` builds the declared entries and appends each one, remembering it against the plugin; `install_menu_entry(menuitem, category=None, subcategory=None, name=None)` is the single item underneath it. `install_menu_submenu(title, menu)` does the same for a plugin that hangs several actions under its entry (assign, unassign, manage). The workspace menu is thrown away and rebuilt whenever plugins change, and the rebuild replays those records.

It did not always. The rebuild used to clear every loaded plugin's `started` flag and call its `startup()` again, so each plugin ran its whole setup once per load or unload of **any** plugin: another gesture on the column view, another background probe of the scanner, another handler. One of those extra gestures is what made a right click crash after the plugin was disabled. Two rules follow:

- **Never append to a shared menu directly.** `app.install_plugin_menu(...)` followed by `append_item` leaves the entry unrecorded, and the next rebuild drops it. That is what happened to the notes backup and restore entries. Pass the category and subcategory to `install_menu_entry` instead.
- **`startup()` runs once per activation.** Guarding its expensive half with a sentinel widget is no longer needed, though it does no harm.

**Contributions are refused once the plugin is unloaded.** `MiAZPlugin.is_active()` goes false before `do_deactivate` runs, and every contribution helper (menu entry, submenu, workspace page, sidebar widget, header bar widget, sidebar dropdown, document tab) returns early when it is false. Background work that finishes late cannot add UI for a plugin that is gone: `MiAZAutoScan` builds its source menu when the scanner answers, which can easily be after the user disabled it.

**A plugin that registers a service must take it away.** `app.set_service(name, None)` removes it, and `set_service` replaces rather than ignoring, which it used to do. `MiAZProjectMgt` registers `Projects`; its `do_deactivate` calls `dispose()` on it (disconnecting the file signals it took) and then removes it. Leaving it registered meant a disabled plugin's service kept reacting to every file change, and, because it holds the path to one repository's `projects.json`, kept writing to the repository the user had switched away from.

**Verifying it**: `tests/ui/test_ui_plugin_cycle.py` loads, unloads and reloads every plugin twice and compares pages, menu entries, sidebar and header bar contents and rename tabs. `tests/ui/test_ui_plugin_signals.py` counts the handlers on every long-lived emitter around a cycle, which is the only way to see a handler that was never disconnected. `PYTHONPATH=. python scripts/devel/check_plugin_ui.py [PluginName ...]` remains for looking at one plugin by hand.

### Startup flow

1. `MiAZ.miaz.py:MiAZ.run()` → creates `MiAZApp(Adw.Application)` → `app.set_env(ENV)`
2. `app._on_activate()` → creates `MiAZPluginSystem` → `_setup_ui()` → `workflow.switch_start()`
3. `switch_start()` → `repository.load()` → `app.load_plugins()` → `switch_finish()`
4. `switch_finish()` → creates `MiAZWatcher`, sets up workspace page

### Switching repository

`MiAZWorkflow.switch_start(repo_id=None)` is the one way in, at startup and for every later switch. **It never restarts the application.** In order:

1. An unknown `repo_id` is rejected before anything is torn down, and the repository on screen is left alone (returns `False`).
2. `repository-switch-started` is emitted, then every loaded plugin is unloaded (`pluginsystem.unload_all()`) and `app.set_plugins_loaded(False)`. The enabled set is per repository (`plugins-used.json` lives in the repository `.conf`), so the plugins of the one being left have to go before the new list is read.
3. The target is resolved: `repository.use(repo_id=...)` for a named one, `repository.reset()` for the default. `use()` does **not** write `App.current`, so a switch and a change of default are two separate decisions.
4. `repository.load()` disposes the previous `MiAZConfigStore` and publishes the new configurations, then emits `repository-switched` → `switch_finish()` (re-points the watcher with `set_path()`, shows the workspace page, emits `repository-switch-finished`).
5. `MiAZRepoSettings` is rebuilt, `app.load_plugins()` loads what the new repository enables, and `application-started` is emitted, which is where `MiAZWorkspace._on_finish_configuration` reloads the view and reconnects to the new configuration objects.

Two rules follow from that order:

- **Anything naming the repository to the user calls `repository.get_active_id()`**, not `App.current`. They differ whenever a switch did not set the default, and `current` then names a repository that is not on screen.
- **Reload work belongs after the configurations are swapped**, so listen to `repository-switch-finished` or `application-started`. `repository-switch-started` fires before the swap and means "teardown is beginning"; a handler that repopulates there binds to the objects being replaced.

A scan already in flight when a switch happens is discarded on arrival: `_apply_parse_results` compares `_repo_docs` with the current `repository.docs` and drops what belongs to the repository that was left.

## Embedded web (webserver + Browser page)

MiAZ ships a **minimal static-file HTTP server** and a built-in WebKit page so plugins can publish browsable HTML (reports, dashboards, summaries) without bundling a server each.

> **Note:** there is no request-routing, action bridge (`miaz.invoke`), per-run token, or `run_on_main_loop` in the webserver. Earlier revisions of this file documented such an API; it does not exist in the code. `webserver.py` is ~130 lines of static serving only.

### Webserver service (`MiAZ/backend/webserver.py`)

`MiAZWebServer` is registered as `app.get_service('webserver')` and started during `_on_activate`. It is a `ThreadingHTTPServer` wrapping a `SimpleHTTPRequestHandler` rooted at the WWW dir, running on a daemon thread (never blocks the GTK main loop), bound to a free localhost port (`port=0`).

| Method | Returns |
|---|---|
| `get_root()` | served directory (`ENV['LPATH']['WWW']`) |
| `get_host()` | bound host (`127.0.0.1`) or `None` |
| `get_port()` | OS-assigned port or `None` |
| `get_url()` | `http://<host>:<port>/` or `None` |
| `is_running()` | `bool` |
| `start()` / `stop()` | idempotent lifecycle |

### WWW root and publishing convention

The serving root is `ENV['LPATH']['WWW']` = `~/.MiAZ/var/www/html`. A plugin publishes a site by writing files to `<WWW>/<PluginName>/`, with an `index.html` at its top. The directory name is the page key; the matching plugin `Description` becomes its dropdown label. To make the Browser refresh, rewrite the page **directory** (the WWW monitor watches created/deleted/moved entries, not in-place edits): the `MiAZInsights` plugin `rmtree`s and recreates its dir on every republish for exactly this reason.

### Built-in Browser page (`MiAZBrowserPage`, `widgets/browserpage.py`)

A WebKit 6.0 viewer added to the **workspace** stack as `'workspace-browser'` (also `app.get_widget('workspace-browser')`). Header bar with Back, a page dropdown, and Refresh. It scans `<WWW>/*/index.html`, lists each as a dropdown entry, and loads it via the webserver URL when running, else a `file://` URI. It watches the WWW root with `Gio.FileMonitor` (`WATCH_MOVES`, 500 ms debounce) and refreshes the dropdown when plugin dirs appear/disappear. The context menu is replaced with just **Copy** / **Select All**, and **Ctrl+C** copies the selection (read-only viewer).

**Opening repository documents from a page.** A served page links a document with the `miazdoc:<filename>` URI scheme. The page's `decide-policy` handler intercepts only `LINK_CLICKED` navigations whose URI starts with `miazdoc:`, cancels the navigation, and opens the named repo document via `actions.document_display(name)` (system handler). Every other link navigates normally. There is no custom URI scheme registration, no in-process file streaming, and no `load_path()` API. Caveat: WebKitGTK has no built-in PDF viewer; render HTML/SVG/images/text in the page and open PDFs via the system viewer.

Vendor third-party JS inside the plugin to keep resources local; fall back to a CDN only when the local copy is missing.

## UI subsystems and gotchas

### Dialogs (`services/dialogs.py`)

- `MiAZDialog` (`app.get_service('dialogs')`): factory of `Adw.AlertDialog`s (`show_info`, `show_error`, `show_question`, `show_confirmation`, `show_toast`). `Adw.AlertDialog` renders as an in-window overlay; it cannot be dragged.
- `MiAZWindowDialog(Adw.Window)`: a **movable, top-level** dialog for when the overlay is not wanted (used by the rename flow). It mirrors the slice of the AlertDialog API callers use (`add_response`, `set_response_appearance/enabled`, `set_default_response`, `set_close_response`, `response` + `closed` signals).
  - **Gotcha:** do **not** pair `set_transient_for` with `set_modal(True)`. GNOME's `org.gnome.mutter attach-modal-dialogs` (default `true`) then glues the window to the parent titlebar so it moves with the parent. To keep it free-floating *and* block the parent, set it transient (not modal) and disable the parent with `window.set_sensitive(False)`, re-enabling on the dialog's `closed` signal. This is how `MiAZActions._document_rename_single` does it.
- `MiAZDialogAdd(Adw.Dialog)` / `MiAZDialogAddRepo`: HIG key+description input dialogs, emit `response`.

### Rename flow (`services/actions.py`)

`document_rename` → `_document_rename_single(doc)` builds the `MiAZRenameDialog` content (`widgets/rename.py`) inside a `MiAZWindowDialog` with responses Cancel / Preview / Rename. Registered as widget `'dialog-rename'` and announced via the `rename-dialog-built` signal. Unlike an AlertDialog it does not auto-dismiss on a response: the handlers close it explicitly on Cancel or a confirmed rename, present the confirmation over the rename window, and leave it open after Preview. `MiAZAutoScan` chains multi-page scans by connecting the dialog's `closed` signal.

### Date detection (`util.filename_guess_date`, `util.dates_from_text`)

`dates_from_text` reads every **unambiguous** date out of a piece of text and returns it as `YYYYMMDD`, in order of appearance. It accepts a year-first date with a separator (`2024_03_15`, `2024-03-15`, `2024.03.15`), a solid eight-digit run even inside a longer one (`IMG20240315123456`), and a year-last date whose order is decided by the text itself (`15_03_2024`, because there is no month 15). It refuses what it would have to guess: `03_04_2024` is 3 April or 4 March depending on the country, so it reads nothing. Two-digit years are refused for the same reason. Years outside 1900..2100 are rejected, which is what keeps an ID or an IBAN from being read as a date.

`dates_from_metadata(filepath)` reads the date the file itself carries, and needs **no third-party library**. For a PDF it scans the raw bytes for `/CreationDate (D:YYYYMMDD…)` and `<xmp:CreateDate>`; only when the plain scan comes back empty does it inflate up to `_PDF_MAX_STREAMS` Flate streams and look again, which is where an XMP-only PDF keeps its packet. For an image it walks the EXIF TIFF block by hand (`_exif_original_date`, tags `0x8769` → `0x9003`) and also scans for an XMP packet. A file starting with the ZIP magic is read as an office document: `docProps/core.xml` `dcterms:created` for OOXML, `meta.xml` `meta:creation-date` for OpenDocument, matched by magic number rather than by listing a dozen mime types. `/ModDate` is deliberately not read, and when several creation dates are present (an incrementally updated PDF carries one Info dictionary per revision) the earliest wins.

Metadata is a claim by whatever wrote the file, not ground truth. An office document made from a template inherits the template's created date, which in this repository is off by years for two files. It is still a date about the document rather than about when it was downloaded, and the rename preview shows it before anything is applied.

This used to go through `pypdf` and `Pillow` behind `except ImportError: return ''`. Neither is a dependency of MiAZ, so on a normal install the whole branch was dead and the date silently fell through to the mtime. Do not reintroduce that shape: an optional import whose failure path is indistinguishable from "no date found" is a feature that is off without saying so.

`filename_guess_date(filepath, concept_hint)` chains: `dates_from_metadata` first, then the first unambiguous date in the concept hint (where `filename_normalize` keeps the original filename), then `UNKNOWN_DATE` (`99991231`, in `backend/util.py`).

**Metadata wins over the name, and the order matters.** A filename is not a reliable place to find a date: invoice numbers, policy numbers and national IDs are digit runs that pass every shape check a date parser can apply. `RG240719880042` is an invoice number, and `15111990` inside it reads as a perfectly valid 15 November 1990; `1988073100123` is a national ID that reads as 27 January 1979. Metadata cannot fail that way, because a field named `CreationDate` holds a date or holds nothing. Measured against 1257 hand-filed documents, the metadata date agreed with the owner's choice 46% of the time and the filename date 26%, and where both existed and disagreed the metadata was right 5 times to 3. End to end the swap moves only 2 documents, because the two sources rarely both fire; it is worth it for the failure mode it removes, not for the aggregate.

`util.filename_get_creation_date` was renamed to `filename_get_modification_date`, since it reads `st_mtime` and the old name claimed something it never delivered. It has no callers; use `dates_from_metadata` for a document date.

There is **no mtime fallback**: a document downloaded today has today's mtime, so the old one filed every dateless document under its import date and looked like "MiAZ always suggests today". `UNKNOWN_DATE` is a real date, so the entry validator, the calendar and the sort order need no special case, and it sorts last so unknown dates group at the end of the workspace.

Measured on a 1257-document repository: 1094 dates from metadata, 19 from the name, 144 unknown, at 1.6 ms per document.

Both rename paths use it. The single rename (`widgets/rename.py`) prefills the date in `set_data` when field 0 is empty; `detect_date()` reads it again on demand from the *current* concept entry text, so it also works for a document already filed under a wrong date. It is wired to the "Detect date" item in the rename dialog's grouped **Detect** menu (`services/actions.py::build_detect_menu`), not a standalone button any more — see the field-detection section below for the rest of that menu. The mass rename Date dialog reads per file when its checkbox is ticked and reports how many dates it really read.

### Local field detection (no AI)

`backend/extract.py` is the core, non-AI counterpart to the `MiAZAIAssistant` plugin's LLM-based suggestions: same idea (read the document, propose filename fields), no network call and no API key. It has no GTK imports, matching every other `backend/` module.

`extract(path) -> ExtractResult(text, method)` gets a document's text: `pdftotext` for a PDF with a text layer, falling back to `pdftoppm` + `tesseract` OCR when there is none; `tesseract` directly for an image; the file's own bytes for plain text/Markdown. `ExtractResult.is_useful` gates on a minimum length and at least one letter, the same bar `MiAZAIAssistant` used before this module existed (it now delegates to it — `miazai/extractor.py` calls `MiAZ.backend.extract.extract()` for every format except `.docx`, which stays plugin-only since `python-docx` is not a core dependency). `match_vocab(text, used)` returns the key of a repository's used vocabulary (`MiAZConfig.load_used()`, key → description) whose description occurs in `text`, longest description first so a specific match does not lose to a shorter coincidental one.

`pdftotext`/`pdftoppm` (poppler-utils) and `tesseract` are **hard package dependencies** (`miaz.spec` `Requires`, `debian/control` `Depends`), not optional like `MiAZOCR`'s `ocrmypdf`. `missing_tools()` still checks for them at call time, because a dev install or the AppImage (which has no dependency resolution of its own, see `scripts/packaging/AppImage/build_appimage.sh`) can be missing them regardless of what the packages declare; `widgets/rename.py::_notify_missing_tools` shows the same install-command dialog shape as `MiAZOCR`'s.

`widgets/rename.py` exposes `detect_country()`, `detect_sentby()`, `detect_sentto()` (one `extract()` + `match_vocab()` pass each, backgrounded through `run_in_background`) and `detect_all()` (one extraction, every field applied together). Group, Purpose and Concept are deliberately not guessed: they are open vocabulary, where a wrong guess is harder to notice than a missing one, unlike Country/SentBy/SentTo which only ever resolve to something already in the repository's used list. `services/actions.py::build_detect_menu()` builds the five `rename-detect-*` actions as one shared `Gio.Menu`, built once and cached the same way `MiAZMassRename.build_menu()` is: each callback resolves the *current* rename widget (`app.get_widget('rename-widget')`) rather than closing over one, since the menu outlives any single dialog. The `Gtk.MenuButton` ("Detect") sits in the rename dialog's action bar next to Suggest/Preview.

### Plugin index

`scan_plugin_index()` reads both plugin directories and writes `index-plugins.json`. `update_available_plugins()` writes the scanned set into the open repository's available plugins. They are separate because only the second one needs a repository: the constructor scans once, `repository-switched` updates only, and `create_plugin_index()` still does both for the one caller that really changed what is on disk (importing a plugin ZIP). Do not put them back together; that is what made the constructor scan, fail on the repository half, warn, and then have the first switch redo the whole thing.

### Archive extraction

`util.check_zip_members(names, install_dir)` is the one place that decides whether an archive may be unpacked. It raises `RuntimeError` for any member that would land outside `install_dir`. It is a **module-level** function, not a method, so callers without the app object can reach it: `MiAZNotes/lib/dr.py` builds its own `ZipFile` and has no service registry.

Three callers, and there must not be a fourth that skips it: `util.unzip` (which every `util.unzip` caller inherits), `pluginsystem.install_plugin` (goes through `util.unzip`, **not** `extractall`), and the `MiAZNotes` restore.

Note what this check is and is not. CPython's `zipfile` already strips `..` and leading separators, so a member named `../evil` is quietly rewritten to sit inside the target rather than escaping: nothing gets out today. The check exists so that case is refused out loud instead of silently relocating a file, and so the guard is already in place if extraction ever moves to `tarfile`, which sanitises nothing. Do not describe it as fixing a live traversal escape.

### First-run repository assistant (`widgets/assistant.py`)

`MiAZRepoAssistant(Adw.Window)` is a guided wizard shown when **no repository is configured** (triggered from `MiAZWorkflow._maybe_launch_assistant`; also reachable via `actions.show_repository_assistant`). Pages: welcome, create-repository (free-text name → derived key via `util.valid_key`, location), Countries (the config selector), and a summary. Countries is the only field it asks about: `MiAZRepository.init` writes `groups-used.json`, `purposes-used.json`, `senders-used.json` and `recipients-used.json` from the shipped defaults (`MiAZRepository.DEFAULT_VALUES`), so a new repository can file a document immediately, while the country list is the whole ISO set and nobody wants all of it. The summary still reports the enabled count for all five fields (`SUMMARY_PROPERTIES`). It initialises the repo before building the selector pages and runs the normal workspace load through `MiAZWorkflow.switch_start` on finish.

### Header bar "Add" menu (`widgets/mainwindow.py`)

A `Gtk.MenuButton` (`headerbar-button-add`) with a persistent `Gio.Menu` (`headerbar-add-menu`) aggregates the core `importdoc` action plus every **Import**-subcategory plugin action, so documents can be added even when filters leave the workspace empty (the "No documents found" page has no context menu). Built in `_populate_add_menu`, which always appends the core service's `importdoc.menuitem` first, then reuses each loaded Import plugin's `plugin-menuitem-<name>` item; visibility kept in sync by `_update_add_button_visibility` (always visible now that a core entry always exists); rebuilt on `plugins-updated`.

### Crash handling

`MiAZCrashHandler` (`services/crash.py`, the first service installed) sets `sys.excepthook` and `threading.excepthook` to show a GUI crash dialog. `backend/crash.py` provides a console/log-only excepthook (`install_backend_excepthook`) for headless/backend contexts.

The dialog is presented over the window the user is currently using, not always the main window. `_present_target` walks `Gtk.Window.get_toplevels()` and returns the visible, `is_active()` top-level, falling back to the main window when none is active. This keeps the dialog on top when a crash fires while a separate top-level (for example the rename window, `MiAZWindowDialog`) is in front. The "Try to Continue" response is offered only when the main window exists; a crash at startup shows "Close MiAZ" only.

### Mass rename

`MiAZMassRename` (`services/massrename.py`, service `massrename`) sets a single filename field across the whole selection. It was a plugin and is now core. `build_menu` (called once in `__init__`) registers the seven `massrename-*` app actions and stores a shared `Gio.Menu` as the `massrename-menu` widget. Three dialog builders back the menu: `rename_field` (value dropdown for country/group/purpose/sentby/sentto), `rename_date` (calendar, plus a "Detect date from each file" checkbox, on by default, that sets each file's date per file via `util.filename_guess_date` instead of one shared calendar date, and reports how many dates were read against how many got `UNKNOWN_DATE`), and `rename_concept` (the guided concept transform; the pure ops are module-level functions in the same file, e.g. `parse_positions`, `keep_tokens`, `apply_concept_op`). All three preview with `MiAZColumnViewMassRename` and apply through the shared rename loop (no `MiAZStatus.BUSY` toggling; skip-and-continue; `util.filename_rename` + debounced workspace refresh).

The menu is exposed from two places, both reusing the one stored `massrename-menu` (rebuilding it would re-register the actions and fail):
- The workspace headerbar (`widgets/mainwindow.py`): a `Gtk.MenuButton` (`headerbar-button-massrename`) with the same `io.github.t00m.MiAZ-rename` icon as single rename. `_on_workspace_menu_update` shows the single-rename button when exactly one document is selected and this menu button when two or more are selected.
- The right-click selection menu: `_append_massrename_submenu` adds a "Mass renaming" submenu, called from both `_setup_menu_selection` and `_on_plugins_updated` (which rebuilds the menu).

### Copy document names

`MiAZActions.document_copy_names()` (`services/actions.py`) puts the selected document names on the clipboard, one per line, in the order the workspace shows them. It was the `MiAZCopy2Clipboard` plugin. The text is composed by the module-level `document_names_text(items)` and the method returns it: on Wayland only a focused client may set the clipboard, so reading the value back tests the compositor rather than MiAZ, and the return value is what `tests/test_actions.py` and `tests/ui/test_ui_import.py` assert on. Its `Gio.MenuItem` (`menuitem_copy_names`, action `copy-document-names`, shortcut `<Control><Shift>c`) is built in `__init__` and appended to the workspace selection menu by `mainwindow._append_clipboard_item`, called from both menu paths the way `_append_massrename_submenu` is, so a plugin-driven menu rebuild puts it back.

### Add documents

`MiAZImportDoc` (`services/importdoc.py`, service `importdoc`) adds documents to the repository from the local filesystem via `Gtk.FileDialog`. It was the `MiAZImportDoc` plugin and is now core, because every repository needs a way to add its first document and that action should not be behind an optional, togglable plugin. `__init__` builds its `Gio.MenuItem` once (`factory.create_menuitem`, action `import-doc`, shortcut `<Control>Insert`) and stores it as `self.menuitem`; `import_files`/`_on_filechooser_response` resolve the chosen files and hand their paths to `import_paths(paths)`, which does the actual copy (`util.filename_normalize` + `util.filename_import`) and reports successes and failures via toast/error dialog.

`import_directory()` opens a folder chooser and hands the chosen path to `import_dropped()`, so a chosen folder and a dropped one raise the same question about subfolders and answer it once. It has its own menu item (`self.menuitem_dir`, action `import-dir`, shortcut `<Shift>Insert`), appended to the headerbar Add menu right after the first one. It was the `MiAZAddFromDir` plugin, moved into the core for the same reason `MiAZImportDoc` was: adding documents is not optional.

Every entry point goes through `import_paths`, so a document added by dropping it is the same operation, with the same reporting, as one picked from a chooser. Above `BATCH_THRESHOLD` (20) files it takes the batched route instead (`needs_batch`): the workspace is held back with `suspend_updates()`, the watcher is turned off, and the copy runs through `run_in_background`, so a hundred files cause one refresh rather than a hundred. Both are released from the main loop in `_copy_batch`'s `finally`, which is what stops a failure halfway through leaving the workspace suspended for the session. The batched call returns `None`, since it reports later, from the main loop. The drop entry point is `import_dropped(paths)`: plain files are imported straight away; if any dropped path is a folder it asks first, since how many documents a folder means depends on whether its subfolders count. The question dialog (`_ask_recursive`) carries an **Include subfolders** `Gtk.CheckButton` (`import-drop-recursive`) and a label (`import-drop-count`) that recounts on every toggle, so the user sees how many files each answer would import before answering. The counting itself is the module-level, side-effect-free `expand_dropped(paths, recursive=False)`: folders are replaced by the files they hold (direct children, or the whole tree when recursive), everything else is kept as it is (including a path that does not exist, which the import then reports as failed rather than dropping silently), symlinked folders are not followed, order is the order dropped and each file appears once. Covered by `tests/test_importdoc.py` (the expansion) and `tests/ui/test_ui_dnd.py` (the drop target, the dialog and both answers).

## Plugin system

### Location
- **System** (bundled): `~/.local/share/MiAZ/resources/plugins/` (17 plugins with `.plugin` metadata)
- **User** (imported): `~/.MiAZ/opt/plugins/`

### Discovery
Uses **libpeas** (`Peas.Engine`) with a direct-import fallback for systems missing the Python loader RPM. Engine is fed both search paths at startup. The plugin index is cached at `~/.MiAZ/var/cache/index-plugins.json`; it is (re)built on startup and on `repository-switched` by globbing `<plugins_dir>/*/*.py` and reading each module's `plugin_info`. Bundled plugins ship via `install_subdir('plugins', …)` in `data/resources/meson.build`, so the whole plugin directory (including any vendored assets such as JS libraries) is copied verbatim to `GPATH['PLUGINS']`.

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
Category=Documents
Subcategory=Import
MenuEntry-import=Import documents from ZIP
MenuEntry-doc=Create a new note|<Ctrl>N
```

Valid categories (with subcategories), defined once in `plugin_categories`
(`frontend/desktop/services/pluginsystem.py`):

- `Documents`: Import, Export, Annotation, Contacts, Periodicity, Projects, Search, Assistants
- `Repository`: Health, Stats
- `Interface`: Behavior, Display, Accessibility
- `Help`: Examples

Names are one word on purpose: both are menu labels. The workspace plugins section
shows one submenu per category and each of those one per subcategory, so a plugin's
actions read as `Documents > Annotation > Create a new note`.

Write the pair in English in both the `.plugin` file and `plugin_info`. It is a
vocabulary key, translated once at display time by `_(category)` in `configview.py`
and `_(subcategory)` in `app.install_plugin_menu`. Those lookups only resolve because
`plugin_categories` marks every name with `N_()` for extraction into `po/`, so a name
that is not in that dict shows up untranslated. `MiAZPlugin.register()` warns when a
plugin declares a pair the dict does not define; `install_menu_entry(category=...,
subcategory=...)` warns for a pair passed explicitly.

**Python file contract:**
```python
plugin_info = {
    'Module': 'module_name', 'Name': 'PluginName', 'Loader': 'Python3',
    'Description': '...', 'Authors': '...', 'Copyright': '...',
    'Website': '...', 'Help': '...', 'Version': '...',
    'Category': '...', 'Subcategory': '...',
    'MenuEntries': [
        ('doc', _('Create a new note'), ['<Ctrl>N']),
        ('all', _('See all notes…')),
    ],
    'Dependencies': 'MiAZOtherPlugin, MiAZAnotherPlugin'   # optional
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
            self.plugin.install_menu_entries({
                'doc': self._on_new_doc_note,
                'all': self._on_open_all_notes,
            })
            self.plugin.set_started(True)
```

**Menu entries are declared, not built.** `MenuEntries` says which entries the
plugin has, in what order, under what label and on what shortcut;
`install_menu_entries` says what each one does, keyed by the id the definition
gave it. The plugin never names an action, writes a label or passes a shortcut in
code. Labels go through `_()` in `plugin_info` so they reach `po/`; the `.plugin`
file carries the same entries untranslated, one `MenuEntry-<id>=` key each, because
repeated keys are not an INI file. `tests/test_plugin_menu_entries.py` checks the
two halves agree and that every declared id is wired to a callback.

An entry the definition cannot describe still goes through `install_menu_entry`:
`MiAZAutoScan` builds a submenu of whatever sources the scanner reports, and asks
`get_menu_entry_label('scan')` for its label so even that one is written in the
definition.

**`MiAZPlugin` helper key methods:**
- `register(plugin_obj, info_dict)`,  stores widget reference, creates `conf/` and `data/` dirs
- `get_config_dir()` → `<repo>/.conf/plugins/<Name>/conf/`
- `get_data_dir()` → `<repo>/.conf/plugins/<Name>/data/`
- `get_config_key(key)` / `set_config_key(key, value)`,  JSON config persistence
- `install_menu_entries({id: callback})` → `{id: Gio.MenuItem}`, builds and installs every entry the definition declares
- `get_menu_entries()` → `[(id, label, shortcuts)]` as declared
- `get_menu_entry_label(id)` → the declared label, for an item the plugin has to build itself
- `get_menu_item_name(id=None)` → the action name of one entry, which is also its widget key
- `install_menu_entry(menuitem, category=None, subcategory=None, name=None)`,  appends one item to the workspace menu under category/subcategory
- `get_menu_item(callback)` → `Gio.MenuItem`, the older single-entry path, kept for out of tree plugins
- `install_settings_group(builder)` → `bool`, offers a settings group to the Repository Settings dialog's Settings tab; `builder` is called with no arguments, returns an `Adw.PreferencesGroup`, and is held rather than called immediately, so a slow builder (AutoScan asking SANE what devices exist) is not paid for until the tab is shown
- `install_metadata_view(name, title, icon_name, factory)` → `bool`, adds one repository vocabulary to the Metadata tab, for a plugin that owns a vocabulary rather than a preference (MiAZPeriodicity's periodicities, MiAZProjectMgt's projects); `factory` is called with no arguments and returns the widget. Unlike a settings builder, it is not held: the Metadata tab calls every registered factory while the dialog is being built, since the dialog is constructed fresh each time it opens and a vocabulary view is cheap to create
- `show_settings(widget=None)`, the older path: a plugin's own settings dialog, opened directly. MiAZAIAssistant still defines it, for its own standalone dialog reached from outside the Repository Settings dialog. The Plugins tab no longer has a button for it; `MiAZRepoSettingsPage.build_legacy_rows` is the shim that keeps it working for out-of-tree plugins written against it, with a Configure row under "Other plugins" for any loaded plugin that has `show_settings` but no `install_settings_group` builder
- `add_workspace_page(widget, name, title, icon_name=None)`,  registers a page on the workspace's `Adw.ViewStack`
- `register_document_tab(name, title, factory, icon_name=None, weight=100)` / `unregister_document_tabs()`,  contributes a tab to the single-document rename dialog (see below)
- `get_source_dir()` → the plugin folder, looked up by `Name` then by `Module`
- `get_icon_path()` → `<source_dir>/icon.svg` or `icon.png`, or `None`
- `get_icon_name()` → themed icon name, the plugin's own icon or the generic MiAZ plugin icon; never empty
- `get_logger()` → named logger `Plugin.<Name>`
- `get_name()` → plugin name string
- `get_widget_name()` → `plugin-<Module>` identifier
- `get_plugin_info_dict()` → full plugin info `dict`
- `get_plugin_info_key(key)` → specific info key value
- `menu_item_loaded()` → `bool`, checks if menu item is registered
- `set_started(True/False)` / `started()` → toggle/query started state

### Document tabs (rename dialog)

The single-document rename dialog is an `Adw.ViewStack`. Its first page,
**Fields**, holds the seven filename fields; plugins add further pages through
the `document-tabs` service (`frontend/desktop/services/doctabs.py`). With no
tab registered, the view switcher is not installed and the dialog looks as it
always did.

```python
# in startup()
self.plugin.register_document_tab(
    name='projects', title=_('Projects'),
    factory=lambda app: MiAZProjectTab(app, self.config),
    weight=100)

# in do_deactivate()
self.plugin.unregister_document_tabs()
```

`factory(app)` is called once per dialog and returns a `Gtk.Widget`. Tabs are
ordered by `(weight, title)`; Fields is always first. Registering a name twice
replaces it, and `MiAZPluginSystem.unload_plugin` drops a plugin's tabs even if
it forgets to.

**Icons.** Leave `icon_name` unset and the tab wears the plugin's own icon.
Every plugin has one: ship `icon.svg` or `icon.png` next to the module and it is
exported into `~/.MiAZ/opt/icons` as `miaz-plugin-<module>`, which the icon
theme resolves; a plugin without an icon file gets the generic MiAZ plugin icon.
`MiAZPlugin.get_icon_name()` returns that name and never an empty value, so it
suits anything taking an icon name.

The widget answers a duck-typed contract:

| Method | When | Required |
|---|---|---|
| `set_document(doc_id)` | once, when the dialog opens | yes |
| `apply(old_id, new_id)` | after the rename succeeded | yes |
| `is_valid()` | before renaming; `False` vetoes and shows the tab | no |
| `discard()` | on Cancel | no |

`apply` should return `True` when it actually wrote something, so the dialog can
tell an empty apply from a real one (it shows a toast when only tab edits were
saved).

**Hold the edits.** A tab must not write anything while the user edits it. The
dialog calls `apply(old_id, new_id)` only after the rename went through, so
Cancel discards tab edits the same way it discards field changes. By then
`filename-renamed` has already fired, so plugin data has moved to the new name
and `apply` writes against `new_id`. Every call is wrapped in try/except by the
dialog: a failing tab logs and never blocks the rename.

**A document can be opened here without renaming it.** When every filename field
is left alone (the user came only to set a project or a periodicity), there is
nothing to rename: `util.filename_rename` would return `False`, which also means
"the rename failed". The dialog checks `util.filename_rename_needed(source,
target)` first and, when no rename is due, skips the confirmation, calls
`apply(doc_id, doc_id)` with the unchanged name and closes.

For header-bar additions rather than a tab (the AI "Suggest" button), connect to
the `rename-dialog-built` signal on the `actions` service instead.

### Plugin dependencies

A plugin can declare that it needs other plugins via the optional
`Dependencies` key in its `plugin_info` dict: a comma-separated list of plugin
**Names** (the `Name` field, the same key used in `plugins-used.json` and the
plugin index). The handling lives in `MiAZPlugins` (`widgets/configview.py`):

- **Enable**: before enabling a plugin, its full dependency chain is resolved
  (recursively). If every missing dependency is installed but disabled, a
  confirmation dialog offers to enable the whole chain, then enables the
  requested plugin. If any dependency is not installed, an error dialog names
  it and the enable is aborted.
- **Disable**: disabling a plugin that other enabled plugins depend on is
  warned and blocked. A dialog lists the dependents; the user must disable
  those first.

No backend change is needed: `create_plugin_index` stores the whole
`plugin_info` dict verbatim, so `Dependencies` flows into
`index-plugins.json` automatically.

### Vetoable activation

A plugin can refuse to be enabled by **raising from `do_activate()`**. The
loader (`_activate_plugin_instance` / `load_plugin` in `pluginsystem.py`)
catches the exception, unloads the half-loaded plugin, and returns `False`;
`MiAZPlugins._enable_single` then does not write it to `plugins-used.json`. The
plugin shows its own dialog before raising. `MiAZOCR` uses this to refuse
activation (with install instructions) when `ocrmypdf` is not on `PATH`.

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
| `LPATH['WWW']` | `~/.MiAZ/var/www/html` (webserver / Browser root) |
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
- **Backend**: no GTK/Adw/Gdk widget imports (GObject/GLib/Gio signals are fine), no side-effects on import
- **Frontend**: no direct file I/O, always call backend APIs
- **Threading**: `run_in_background(fn, on_done, on_error, name)` from `backend/tasks.py`, not a raw `threading.Thread`. It marshals the callbacks back with `GLib.idle_add` and, with no `on_error`, logs the failure with its traceback instead of letting it die in the worker:
  ```python
  from MiAZ.backend.tasks import run_in_background

  run_in_background(lambda: self._scan(path),
                    on_done=self._apply,          # runs on the main loop
                    on_error=self._release_busy,  # optional; logged either way
                    name='workspace-scan')
  ```
- **Architectural rules are tested**, not just written here: `tests/test_boundaries.py` fails the build when the backend imports a GUI toolkit, or when a frontend module calls `os.unlink` / `shutil.copy` and friends instead of the util service. Exemptions go in `FS_ALLOWED` with a reason, and a third test removes them once they stop being needed.
- **GTK4 list-model chain** (Workspace, `widgets/columnview.py`): `Gio.ListStore` → `Gtk.SortListModel` → `Gtk.FilterListModel` → `Gtk.MultiSelection` → `Gtk.ColumnView`
- **No GTK3**: no `GtkListStore`, `GtkTreeView`, `GtkDialog` subclassing
- **Filechooser**: `Gtk.FileDialog` (async GTK4 API), not `Gtk.FileChooserDialog`


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

## Existing plugins (17 with `.plugin` metadata)

| Plugin | Category / Subcategory | Purpose |
|---|---|---|
| HelloWorld | Help / Examples | Hello World example plugin |
| MiAZAutoScan | Documents / Import | Scan documents in background (SANE `scanimage`, source submenu) and import them |
| MiAZColumnVisibility | Interface / View | Toggle workspace column visibility |
| MiAZExport2CSV | Documents / Export | Export to CSV |
| MiAZExport2Dir | Documents / Export | Export to directory |
| MiAZExport2Text | Documents / Export | Export to text editor |
| MiAZExport2Zip | Documents / Export | Compress documents into a ZIP file |
| MiAZFullscreen | Interface / View | Toggle fullscreen |
| MiAZImportFromScan | Documents / Import | Import document from scanner |
| MiAZImportFromZip | Documents / Import | Import documents from a ZIP file |
| MiAZInsights | Repository / Statistics | Insights into the repository (totals, activity heatmap, rank movers, country map) published to the Browser page |
| MiAZNotes | Documents / Notes | Take Markdown notes linked to documents (adds a workspace page) |
| MiAZOCR | Documents / Text | Extract text from PDFs with OCR and save as a note (depends on MiAZNotes; vetoes activation if `ocrmypdf` is missing) |
| MiAZPeriodicity | Organise / Tags | Set document periodicity |
| MiAZProjectMgt | Organise / Projects | Project management |
| MiAZWSFont | Interface / Fonts | Modify workspace font name and size |

WIP plugin directories without a `.plugin` file yet (not loaded): `MiAZDeleteDoc`, `MiAZRenameDoc`, `MiAZViewDoc`, `MiAZWorkspaceToggleView`.

`MiAZInsights` is the reference example for the WWW-publish + Browser-page pattern; `MiAZAutoScan` and `MiAZOCR` show background-thread work and vetoable activation.
