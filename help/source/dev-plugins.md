---
Feature: Development, Plugins
HelpId: dev-plugins
Kind: howto
Level: advanced
Order: 930
Section: Developers
Summary: "Write a MiAZ plugin: the two files, the menu entries, and what to clean up."
---

# Write a plugin

A plugin is a folder with two files. Bundled plugins live in
`data/resources/plugins/`; plugins a user imports go to `~/.MiAZ/opt/plugins/`.
`HelloWorld` is the smallest complete example.

```
MiAZMyPlugin/
├── myplugin.plugin
└── myplugin.py
```

## The metadata file {#plugin-file}

```ini
[Plugin]
Module=myplugin
Name=MiAZMyPlugin
Loader=python
Description=One line description
Authors=Your Name <you@example.com>
Copyright=Copyright © 2026 Your Name
Website=https://github.com/t00m/MiAZ
Help=https://t00m.github.io/MiAZ/go.html?id=plugin-myplugin
Category=Documents
Subcategory=Annotation
MenuEntry-hello=Say hello
```

`Category` and `Subcategory` must be a pair defined in `plugin_categories`
(`MiAZ/backend/plugins.py`); they become the menu path, here
**Documents > Annotation > Say hello**. A bundled plugin has no `Version=`: it
takes the application's.

## The module {#module}

The same keys go in a `plugin_info` dictionary, with the menu entries
declared once:

```python
from gettext import gettext as _
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module': 'myplugin', 'Name': 'MiAZMyPlugin', 'Loader': 'python',
    'Description': _('One line description'),
    'Authors': 'Your Name <you@example.com>',
    'Copyright': 'Copyright © 2026 Your Name',
    'Website': 'https://github.com/t00m/MiAZ',
    'Help': 'https://t00m.github.io/MiAZ/go.html?id=plugin-myplugin',
    'Category': 'Documents', 'Subcategory': 'Annotation',
    'MenuEntries': [('hello', _('Say hello'))],
}


class MyPlugin(MiAZExtension):
    __gtype_name__ = 'MiAZMyPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.workspace = self.app.get_widget('workspace')
        if self.workspace.is_loaded():
            self.startup()
        else:
            self._startup_handler = self.workspace.connect(
                'workspace-loaded', self.startup)

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            self.plugin.install_menu_entries({'hello': self._on_hello})
            self.plugin.set_started(True)

    def _on_hello(self, *args):
        self.app.get_service('dialogs').show_toast(_('Hello'))
```

## Adding to the window {#contribute}

Use the helpers on `self.plugin`. The plugin system removes what they add
when the plugin is turned off, so `do_deactivate` has nothing to undo for them:

- `install_menu_entries` and `install_menu_entry`: menu items
- `add_workspace_page`, `add_workspace_view`: a page or a document view
- `add_workspace_column(column, name, title)`: a column in the Details table,
  also listed in the column chooser; call `workspace.refresh_rows()` when the
  data behind its cells changes
- `add_sidebar_widget`, `add_headerbar_widget`, `add_sidebar_dropdown`
- a filter: `add_sidebar_dropdown(dropdown)` (put "any" first, since Clear
  filters selects the first entry), `workspace.register_filter_view(name,
  callback)` for the condition, and `workspace.filters_changed()` when the
  dropdown changes. Unregister the condition in `do_deactivate`; the plugin
  system only takes back the dropdown
- `register_document_tab`: a tab in the rename dialog
- `install_settings_group`, `install_metadata_view`: Repository Settings

## Cleaning up {#cleanup}

Anything you connected yourself (a signal on `util`, a service you
registered) must be disconnected or removed in `do_deactivate`. A plugin is
turned off and on again on every repository switch, and
`tests/ui/test_ui_plugin_signals.py` counts the handlers left behind.

## Storage {#storage}

`self.plugin.get_config_dir()` and `get_data_dir()` are inside the open
repository, under `.conf/plugins/<Name>/`, so plugin data travels and is
backed up with the repository.

## Help for your plugin {#help}

Add a page to `help/` with a `HelpId` and point the `Help` key at it, as
above. See [Write help pages](dev-help.md).
