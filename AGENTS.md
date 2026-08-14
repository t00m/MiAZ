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
| Distribution | deb / rpm / AppImage (native). Flatpak is deprecated | — |
| i18n | gettext | — |

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
│           │   ├── importdoc.py  ← MiAZImportDoc (core add-document service + menu item)
│           │   ├── pluginsystem.py ← MiAZExtension, MiAZPlugin, MiAZPluginSystem
│           │   └── workflow.py   ← MiAZWorkflow (repo switching lifecycle)
│           └── widgets/
│               ├── about.py, assistant.py, browserpage.py, button.py
│               ├── columnview.py, configview.py, dr.py, mainwindow.py
│               ├── markdownview.py, pages.py, pluginuimanager.py, rename.py
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
- Registration order: `crash`, `util`, `icons`, `factory`, `dialogs`, `actions`, `workflow`, `dr`, `secrets`, `venv`, `extlibs`, `webserver`, `repo`, `index`, `massrename`, `importdoc` (early); then `plugin-system` and `theme` (`Gtk.IconTheme`) once the window exists. `massrename` and `importdoc` are registered before the window is built because each builds its menu item(s) in `__init__` (`massrename-menu` widget; `importdoc.menuitem`) that the headerbar consumes when it is constructed.

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
    ├── [page 'workspace-default'] ← Documents columnview (always present)
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

**Verifying it**: `PYTHONPATH=. python scripts/devel/check_plugin_ui.py [PluginName ...]` drives a real disable/enable cycle in the running app and reports what every shared container held at each step. It cannot be a unit test, since it needs a display and a loaded repository.

### Startup flow

1. `MiAZ.miaz.py:MiAZ.run()` → creates `MiAZApp(Adw.Application)` → `app.set_env(ENV)`
2. `app._on_activate()` → creates `MiAZPluginSystem` → `_setup_ui()` → `workflow.switch_start()`
3. `switch_start()` → `repository.load()` → `app.load_plugins()` → `switch_finish()`
4. `switch_finish()` → creates `MiAZWatcher`, sets up workspace page

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

### First-run repository assistant (`widgets/assistant.py`)

`MiAZRepoAssistant(Adw.Window)` is a guided wizard shown when **no repository is configured** (triggered from `MiAZWorkflow._maybe_launch_assistant`; also reachable via `actions.show_repository_assistant`). Pages: welcome, create-repository (free-text name → derived key via `util.valid_key`, location), one page per filing property (Countries/Groups/Purposes/Senders/Recipients embedding the config selectors), and a summary. It initialises the repo before building the selector pages and runs the normal workspace load through `MiAZWorkflow.switch_start` on finish.

### Header bar "Add" menu (`widgets/mainwindow.py`)

A `Gtk.MenuButton` (`headerbar-button-add`) with a persistent `Gio.Menu` (`headerbar-add-menu`) aggregates the core `importdoc` action plus every **Import**-subcategory plugin action, so documents can be added even when filters leave the workspace empty (the "No documents found" page has no context menu). Built in `_populate_add_menu`, which always appends the core service's `importdoc.menuitem` first, then reuses each loaded Import plugin's `plugin-menuitem-<name>` item; visibility kept in sync by `_update_add_button_visibility` (always visible now that a core entry always exists); rebuilt on `plugins-updated`.

### Crash handling

`MiAZCrashHandler` (`services/crash.py`, the first service installed) sets `sys.excepthook` and `threading.excepthook` to show a GUI crash dialog. `backend/crash.py` provides a console/log-only excepthook (`install_backend_excepthook`) for headless/backend contexts.

The dialog is presented over the window the user is currently using, not always the main window. `_present_target` walks `Gtk.Window.get_toplevels()` and returns the visible, `is_active()` top-level, falling back to the main window when none is active. This keeps the dialog on top when a crash fires while a separate top-level (for example the rename window, `MiAZWindowDialog`) is in front. The "Try to Continue" response is offered only when the main window exists; a crash at startup shows "Close MiAZ" only.

### Mass rename

`MiAZMassRename` (`services/massrename.py`, service `massrename`) sets a single filename field across the whole selection. It was a plugin and is now core. `build_menu` (called once in `__init__`) registers the seven `massrename-*` app actions and stores a shared `Gio.Menu` as the `massrename-menu` widget. Three dialog builders back the menu: `rename_field` (value dropdown for country/group/purpose/sentby/sentto), `rename_date` (calendar, plus a "Detect date from each file" checkbox, on by default, that sets each file's date per file via `util.filename_guess_date` instead of one shared calendar date), and `rename_concept` (the guided concept transform; the pure ops are module-level functions in the same file, e.g. `parse_positions`, `keep_tokens`, `apply_concept_op`). All three preview with `MiAZColumnViewMassRename` and apply through the shared rename loop (no `MiAZStatus.BUSY` toggling; skip-and-continue; `util.filename_rename` + debounced workspace refresh).

The menu is exposed from two places, both reusing the one stored `massrename-menu` (rebuilding it would re-register the actions and fail):
- The workspace headerbar (`widgets/mainwindow.py`): a `Gtk.MenuButton` (`headerbar-button-massrename`) with the same `io.github.t00m.MiAZ-rename` icon as single rename. `_on_workspace_menu_update` shows the single-rename button when exactly one document is selected and this menu button when two or more are selected.
- The right-click selection menu: `_append_massrename_submenu` adds a "Mass renaming" submenu, called from both `_setup_menu_selection` and `_on_plugins_updated` (which rebuilds the menu).

### Add documents

`MiAZImportDoc` (`services/importdoc.py`, service `importdoc`) adds documents to the repository from the local filesystem via `Gtk.FileDialog`. It was the `MiAZImportDoc` plugin and is now core, because every repository needs a way to add its first document and that action should not be behind an optional, togglable plugin. `__init__` builds its `Gio.MenuItem` once (`factory.create_menuitem`, action `import-doc`, shortcut `<Control>Insert`) and stores it as `self.menuitem`; `import_files`/`_on_filechooser_response` do the actual copy (`util.filename_normalize` + `util.filename_import`), reporting successes and failures via toast/error dialog.

## Plugin system

### Location
- **System** (bundled): `~/.local/share/MiAZ/resources/plugins/` (19 plugins with `.plugin` metadata)
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
    'Category': '...', 'Subcategory': '...',
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

## Existing plugins (19 with `.plugin` metadata)

| Plugin | Category / Subcategory | Purpose |
|---|---|---|
| HelloWorld | Support and Help / Guides and Tutorials | Hello World example plugin |
| MiAZAddFromDir | Data Management / Import | Add documents from a directory |
| MiAZAutoScan | Data Management / Import | Scan documents in background (SANE `scanimage`, source submenu) and import them |
| MiAZColumnVisibility | Customisation and Personalisation / User Interface | Toggle workspace column visibility |
| MiAZCopy2Clipboard | Data Management / Export | Copy to clipboard |
| MiAZExport2CSV | Data Management / Export | Export to CSV |
| MiAZExport2Dir | Data Management / Export | Export to directory |
| MiAZExport2Text | Data Management / Export | Export to text editor |
| MiAZExport2Zip | Data Management / Export | Compress documents into a ZIP file |
| MiAZFullscreen | Customisation and Personalisation / User Interface | Toggle fullscreen |
| MiAZImportFromScan | Data Management / Import | Import document from scanner |
| MiAZImportFromZip | Data Management / Import | Import documents from a ZIP file |
| MiAZInsights | Analytics and Reporting / Custom Reports | Insights into the repository (totals, activity heatmap, rank movers, country map) published to the Browser page |
| MiAZNotes | Collaboration / Comments and Annotations | Take Markdown notes linked to documents (adds a workspace page) |
| MiAZOCR | Artificial Intelligence / Document AI | Extract text from PDFs with OCR and save as a note (depends on MiAZNotes; vetoes activation if `ocrmypdf` is missing) |
| MiAZPeriodicity | Content Organisation / Tagging and Classification | Set document periodicity |
| MiAZProjectMgt | Content Organisation / Tagging and Classification | Project management |
| MiAZWSFont | Customisation and Personalisation / User Interface | Modify workspace font name and size |

WIP plugin directories without a `.plugin` file yet (not loaded): `MiAZDeleteDoc`, `MiAZRenameDoc`, `MiAZViewDoc`, `MiAZWorkspaceToggleView`.

`MiAZInsights` is the reference example for the WWW-publish + Browser-page pattern; `MiAZAutoScan` and `MiAZOCR` show background-thread work and vetoable activation.
