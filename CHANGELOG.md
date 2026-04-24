# Changelog

All notable changes to MiAZ are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — 2026-04-25

### Fixed

#### Backend

- **projects**: Fixed crash on startup — `conf['Project']` key does not exist in the
  config dict; now uses `conf.get('Project')` with a `None` guard throughout.
- **projects**: Fixed `TypeError` on file deletion — `_on_filename_deleted` was passing
  the entire `filepaths` set to `os.path.basename()`; now iterates the set correctly.
- **projects**: Fixed `description()` returning a raw `KeyError` object instead of a
  string, and crashing with `TypeError` when the config value was `None`.
- **projects**: Fixed `remove_batch()` calling `save()` N+1 times; now saves once after
  all removals.
- **util**: Fixed `NameError` — `GLib` was used in `check_remote_directory_sync()` but
  never imported; changed to `except Exception`.
- **util**: Fixed `get_files()` returning directories alongside files, causing `IndexError`
  in every caller that accessed filename fields.
- **util**: Fixed `filename_delete()` using `os.system("rm '...'")` — replaced with
  `os.unlink()` to prevent shell injection and expose errors properly.
- **util**: Fixed `zip_list()` leaking an open `ZipFile` handle; now uses a context manager.
- **util**: Fixed `which()` always returning `None` (body was entirely commented out);
  replaced with `shutil.which()`.
- **util**: Fixed `since_date_last_six_months()` returning a `date` object while all
  sibling methods return `datetime`, causing `TypeError` on comparisons.
- **util**: Fixed `Field` dict missing `Concept` (index 5), causing `KeyError` on any
  `field_used(Concept, …)` call.
- **util**: Fixed `Gio.content_type_guess()` called with `f"filename={path}"` instead of
  the bare path — MIME type detection was always wrong.
- **util**: Fixed shell injection in `directory_open()` and `filename_display()` which used
  `os.system("xdg-open '...'")`. Replaced with `subprocess.Popen`.
- **stats**: Fixed crash on malformed filenames — `_build()` called `.year` on the result
  of `string_to_datetime()` without checking for `None`; now skips bad entries.
- **watcher**: Fixed second `MiAZWatcher` instance never monitoring anything — the
  `GObject.__init__` was called twice and `set_path()` / `timeout_add_seconds()` were
  only called when `sid == 0`. Replaced runtime signal registration with `__gsignals__`
  and removed the guard so initialisation always runs.
- **webserver**: Fixed `start()` calling itself recursively on port collision, which could
  exhaust the call stack. Replaced with a `while` loop.
- **webserver**: Fixed `os.chdir(self.directory)` changing the process-wide working
  directory. Replaced with `functools.partial(SimpleHTTPRequestHandler, directory=…)`.
- **config**: Fixed `load()` returning `[]` (a list) on JSON parse error; callers expect
  a `dict`. Now returns `{}` and logs the exception.
- **config**: Fixed dead unreachable branch in `get()` (`if key in config` inside
  `except KeyError` is always `False`). Simplified to `return None`.
- **config**: Fixed `add()` and `remove()` continuing execution past an empty-key warning,
  allowing invalid keys to be written. Both now return `False` immediately.
- **log**: Fixed `enable_file_output()` raising `AttributeError` when called before
  `add_file_handler()`. Added class-level `file_handler = None` and an early-return guard.

#### Frontend (widgets — fixed in earlier session)

- **views**: Fixed signal handler accumulating on `CheckButton` every time a cell was
  recycled on scroll. Signal now connected once in `setup`; `bind` uses `handler_block`.
- **pluginuimanager**: Fixed `NameError` — `requests` and `HTTPError` were used without
  import. Added guarded import with `_REQUESTS_AVAILABLE` flag.
- **pluginuimanager**: Fixed call to undefined `self.update_user_plugins()`.
- **configview**: Fixed `HTTPError` used without import in `download_plugins()`. Added
  guarded import and early-return guard.
- **configview**: Replaced runtime `GObject.signal_new()` pattern with `__gsignals__` in
  `MiAZUserPlugins`.
- **sidebar**: Fixed `get_service('repository')` typo — should be `get_service('repo')`,
  which caused `AttributeError` on every `update_repo_status()` call.
- **window**: Fixed `_on_window_close_request()` calling `window.close()`, which
  re-emitted `close-request` and could loop. Changed to `return False`.
- **mainwindow**: Fixed typo `'page-webbroser'` → `'page-webbrowser'`, causing
  `_setup_webbrowser()` to be called and a new WebKit view to be created on every
  `_setup_ui()` invocation.
- **columnview**: Fixed `eval()` used for attribute access in sort comparators — replaced
  with `getattr()`, eliminating arbitrary code execution risk and giving ~10× speedup.
- **selector**: Fixed `searchentry.get_text()` called on every item in a filter pass;
  text is now cached before `refilter()`.
- **searchbar**: Fixed search entry registered under `'searchbar_entry'` while the rest
  of the app uses `'searchentry'`.
- **button**: Fixed `popover.present()` called during construction before the popover
  had a parent window.
- **columnview**: Fixed `get_selected()` iterating the raw store with `is_selected()`,
  giving wrong results after filtering/sorting. Replaced with `get_selected_item()` (O(1)).

### Performance

- **repository**: `get()` no longer calls `setup()` (JSON I/O) on every property access.
  Result is cached in `_conf_cache` and invalidated when `load()` is called.
- **stats**: `get()` no longer triggers a full directory scan on every call. Stats are
  built once and callers invoke `_build()` directly when a refresh is needed.
- **util**: `field_used()` no longer performs a full O(N) scan per call. An inverted
  field-index is built once per directory and invalidated automatically on file changes.
- **workspace**: `update()` no longer called `get_files()` twice per refresh.
- **workspace**: `_on_filter_selected()` no longer performed a full directory scan on
  every keystroke and dropdown change.
- **workspace**: Date range bounds are now parsed once per filter pass, not once per
  document.
- **workspace**: Dropdowns and search text are now resolved once per filter pass.
- **workspace**: `initialize_caches()` no longer loaded the cache JSON from disk only
  to immediately discard it.
- **columnview**: `update()` now uses a single `splice()` call instead of `remove_all()`
  + `splice()`, sending one model-change notification instead of two.

### Changed

- **util**: `filename_validate()` now delegates to `filename_is_normalized()` (they were
  functional duplicates).
- **util**: `valid_key()` now applies both substitutions in a single chained expression.
- **util**: `get_files_recursively()` now uses `os.walk(topdown=True)` with in-place
  directory pruning, replacing an O(N²) substring-based hidden-directory check.
- **util**: `download_and_unzip()` now checks for the `requests` library at call time and
  logs a clear error if it is not installed.
- **watcher**: First `next_files_async` batch size changed from 10 to 100 to match all
  subsequent batches.
- **webserver**: Log message corrected from "Sleeping 5 seconds" to "Sleeping 3 seconds".
- **config**: `set()` return-type annotation corrected from `-> None` to `-> bool`.
- **config**: `save_available()`, `save_used()`, `save_data()`, and `MiAZConfigApp.save()`
  mutable default argument `items: dict = {}` replaced with `items: dict = None`.
- **repository**: `load()` `path` parameter made optional (`path=None`) since it was
  never used internally.
- **mainwindow**: Removed duplicate `add_widget('page-404', …)` call that overwrote the
  content widget with the `GtkStackPage` wrapper.
- **log**: `has_console_handler()` comment added explaining why strict type equality
  (not `isinstance`) is used to exclude `FileHandler`.

### Removed

- **config**: Removed dead unreachable branch in `get()`.
- **repository**: Removed commented-out `except KeyError` block in `validate()`.
- **log**: Removed unused `counter = 0` class variable.
- **widget**: Deleted `widget.py` — the file's own comment stated "Not used" and no
  import of `MiAZWidget` was found anywhere in the codebase.
- **settings**: Removed dead `_on_selected_repo()` method (defined but never connected
  to any signal) and empty `on_filechooser_response_source()` stub.
- **configview**: Removed 15 lines of dead code after an early `return` in
  `_add_config_menubutton()`.
- **columnview**: Removed dead `_on_filter_view()` methods from both `MiAZColumnView`
  and `MiAZColumnViewSelector` (referenced non-existent attributes).

### Fixed (signal / GObject patterns)

- **util**, **watcher**: Replaced `GObject.signal_new()` in `__init__` with class-level
  `__gsignals__` dict, eliminating duplicate-registration errors on second instantiation.
- **config**, **repository**, **configview**: Same `__gsignals__` migration (done in
  prior session).
- **config**, **stats**, **repository**, **watcher**: Class-level mutable dicts (`cache`,
  `stats`, `_errmsg`, `before`) moved to instance `__init__` to prevent cross-instance
  data sharing.

### Fixed (i18n)

- **sidebar**: Fixed untranslatable f-string in `update_repo_status()`; now uses
  `_('…').format(…)`.
- **configview**: Fixed `_(f'<b>{key}</b>')` → `f'<b>{_(key)}</b>'` so the key string
  is extracted correctly by xgettext.
- **pages**: Fixed `_(f"Welcome to {shortname}!")` → `_("Welcome to {shortname}!").format(…)`.

### Fixed (deprecated GTK API)

- **mainwindow**, **assistant**, **statusbar**, **views**, **pages**, **button**:
  Replaced all `get_style_context().add_class()` / `remove_class()` calls with
  `add_css_class()` / `remove_css_class()` (deprecated since GTK 4.10).

### Fixed (Python patterns)

- **about**, **button**, **pages**, **assistant**: Fixed `super(ParentClass, self).__init__()`
  → `super().__init__()` in five classes.
- **data**: Added prominent TODO comment to unimplemented `MiAZData` / `MiAZDataBackup`
  / `MiAZDataRestore` stubs.
- **models**: Fixed `# File: watcher.py` in module docstring → `# File: models.py`.
- **repository**: Fixed typo `"initialited"` → `"initialized"` in log message.
- **webbrowser**: Same typo fix in log message; removed duplicate widget registration.
