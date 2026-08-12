# File: browserpage.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Workspace page hosting an embedded WebKit browser whose page
#              list is contributed by plugins through subdirectories of
#              $HOME/.MiAZ/var/www/html.

import html
import os
import urllib.parse

import gi
gi.require_version('WebKit', '6.0')

from gi.repository import Gdk, Gio, GLib, GObject, Gtk, WebKit

from MiAZ.backend.log import MiAZLog


class MiAZBrowserPage(Gtk.Box):
    """Workspace page with a header bar (back, page dropdown, refresh) and a WebKit view."""
    __gtype_name__ = 'MiAZBrowserPage'
    __gsignals__ = {
        # Emitted whenever the set of available browser pages changes; carries
        # the current page count so the workspace can hide the Browser tab when
        # nothing is registered to load.
        'pages-updated': (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = MiAZLog('MiAZ.BrowserPage')
        self._pages = []
        self._suppress_change = False
        self._www_monitor = None
        self._www_debounce_id = 0
        self._build_ui()
        self._refresh_pages()
        self._setup_www_monitor()
        plugin_system = self.app.get_service('plugin-system')
        if plugin_system is not None:
            try:
                plugin_system.connect('plugins-updated', self._on_plugins_updated)
            except TypeError:
                pass

    def _build_ui(self):
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(False)
        # Quiet the topbar: '.flat' drops the headerbar's own background and
        # bottom shadow so it blends with the content instead of standing out.
        # Adwaita named colors switch with the theme, so this stays muted in
        # both light and dark mode.
        header.add_css_class('flat')

        center = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._back_button = Gtk.Button.new_from_icon_name('go-previous-symbolic')
        self._back_button.set_tooltip_text('Back')
        self._back_button.set_sensitive(False)
        self._back_button.connect('clicked', self._on_back_clicked)
        center.append(self._back_button)

        self._model = Gtk.StringList()
        self._dropdown = Gtk.DropDown(model=self._model)
        self._dropdown.set_sensitive(False)
        self._dropdown.connect('notify::selected', self._on_page_selected)
        center.append(self._dropdown)

        self._refresh_button = Gtk.Button.new_from_icon_name('view-refresh-symbolic')
        self._refresh_button.set_tooltip_text('Refresh')
        self._refresh_button.connect('clicked', self._on_refresh_clicked)
        center.append(self._refresh_button)

        header.set_title_widget(center)
        self.append(header)

        self._webview = WebKit.WebView()
        self._webview.set_hexpand(True)
        self._webview.set_vexpand(True)
        self._webview.connect('context-menu', self._on_context_menu)
        self._webview.connect('load-changed', self._on_load_changed)
        self._webview.connect('decide-policy', self._on_decide_policy)
        # Ctrl+C copies the current selection. WebKitGTK usually does this on
        # its own, but a controller on the view makes it work regardless of the
        # window-level key handling.
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self._on_key_pressed)
        self._webview.add_controller(key_controller)
        self.append(self._webview)

    # Page enumeration

    def _www_root(self):
        env = self.app.get_env()
        return env['LPATH']['WWW']

    def _plugin_description(self, module_name):
        plugin_system = self.app.get_service('plugin-system')
        if plugin_system is None:
            return module_name
        info = plugin_system.get_plugin_info(module_name)
        if info is None:
            return module_name
        try:
            desc = info.get_description()
        except AttributeError:
            desc = None
        return desc or module_name

    def _scan_pages(self):
        root = self._www_root()
        if not os.path.isdir(root):
            return []
        pages = []
        for name in sorted(os.listdir(root)):
            page_dir = os.path.join(root, name)
            index = os.path.join(page_dir, 'index.html')
            if os.path.isdir(page_dir) and os.path.isfile(index):
                pages.append((name, self._plugin_description(name)))
        return pages

    def has_pages(self):
        """True when at least one browser page is available to load."""
        return len(self._pages) > 0

    def _refresh_pages(self):
        pages = self._scan_pages()
        self._pages = pages
        self.emit('pages-updated', len(pages))

        self._suppress_change = True
        try:
            while self._model.get_n_items() > 0:
                self._model.remove(0)
            for _key, description in pages:
                self._model.append(description)
        finally:
            self._suppress_change = False

        if not pages:
            self._dropdown.set_sensitive(False)
            self._show_welcome()
            return

        self._dropdown.set_sensitive(True)
        # Preserve current selection if possible, otherwise pick the first page.
        current_key = self._current_key()
        next_index = 0
        if current_key is not None:
            for i, (key, _desc) in enumerate(pages):
                if key == current_key:
                    next_index = i
                    break
        self._suppress_change = True
        try:
            self._dropdown.set_selected(next_index)
        finally:
            self._suppress_change = False
        self._load_page(next_index)

    def _current_key(self):
        idx = self._dropdown.get_selected()
        if 0 <= idx < len(self._pages):
            return self._pages[idx][0]
        return None

    # Loading

    def _load_page(self, index):
        if not (0 <= index < len(self._pages)):
            return
        key, _desc = self._pages[index]
        webserver = self.app.get_service('webserver')
        if webserver is not None and webserver.is_running():
            url = f"{webserver.get_url()}{key}/index.html"
        else:
            path = os.path.join(self._www_root(), key, 'index.html')
            url = GLib.filename_to_uri(path, None)
        self.log.debug(f"Loading {url}")
        self._webview.load_uri(url)

    def _show_welcome(self):
        env = self.app.get_env()
        app_info = env.get('APP', {})
        name = html.escape(str(app_info.get('name', 'MiAZ')))
        version = html.escape(str(app_info.get('VERSION', '')))
        # Muted palette so the empty page blends with the (also muted) topbar.
        # Light and dark variants follow the app theme.
        dark = self._prefers_dark()
        if dark:
            page_bg, card_bg = '#242424', '#303030'
            title_fg, version_fg, hint_fg = '#e0e0e0', '#b0b0b0', '#909090'
            shadow = 'rgba(0,0,0,0.30)'
        else:
            page_bg, card_bg = '#f0f0f0', '#fafafa'
            title_fg, version_fg, hint_fg = '#2e2e2e', '#5e5e5e', '#777777'
            shadow = 'rgba(0,0,0,0.06)'
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>" + name + "</title>"
            "<style>"
            " html,body{height:100%;margin:0;font-family:sans-serif;"
            "  display:flex;align-items:center;justify-content:center;"
            f"  background:transparent;color:{title_fg};}}"
            " .card{text-align:center;padding:2.5em 3em;border-radius:12px;"
            f"  background:transparent;" #box-shadow:0 2px 12px {shadow};}}"
            " h1{margin:0 0 .25em 0;font-weight:300;font-size:2.2em;}"
            f" .version{{color:{version_fg};margin:.25em 0 1.5em 0;}}"
            f" .hint{{color:{hint_fg};font-size:.9em;}}"
            "</style></head><body>"
            f"<div class='card'><h1>{name}</h1>"
            f"<div class='version'><h5>v{version}</h5></div>"
            "<div class='hint'>No pages are available.</div>"
            "</div></body></html>"
        )
        self._webview.load_html(body, None)

    def _prefers_dark(self):
        """True when the app is using a dark theme, so the welcome page can
        match it. Falls back to light if Adwaita's style manager is unavailable."""
        try:
            from gi.repository import Adw
            return Adw.StyleManager.get_default().get_dark()
        except Exception:
            return False

    # Signal handlers

    def _on_back_clicked(self, _button):
        if self._webview.can_go_back():
            self._webview.go_back()

    def _on_refresh_clicked(self, _button):
        # Rebuild the dropdown from disk so a newly-installed plugin shows up,
        # then reload the current page.
        previous_key = self._current_key()
        self._refresh_pages()
        if previous_key is not None and self._current_key() == previous_key:
            self._webview.reload()

    def _on_page_selected(self, dropdown, _pspec):
        if self._suppress_change:
            return
        self._load_page(dropdown.get_selected())

    def _on_context_menu(self, _webview, context_menu, _hit):
        # Read-only viewer: replace the default menu (back/reload/download/...)
        # with just Copy and Select All so text on any page can be copied.
        context_menu.remove_all()
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.COPY))
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.SELECT_ALL))
        return False

    def _on_key_pressed(self, _controller, keyval, _keycode, state):
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self._webview.execute_editing_command(WebKit.EDITING_COMMAND_COPY)
            return True
        return False

    def _on_decide_policy(self, _webview, decision, decision_type):
        # A served page can ask MiAZ to open a repository document by linking to
        # `miazdoc:<filename>`. We intercept the click, open the file with the
        # system handler, and cancel the navigation so the view stays put. Any
        # other link (e.g. a plugin page's internal navigation) is left alone.
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        action = decision.get_navigation_action()
        if action.get_navigation_type() != WebKit.NavigationType.LINK_CLICKED:
            return False
        uri = action.get_request().get_uri()
        if not uri.startswith('miazdoc:'):
            return False
        decision.ignore()
        name = urllib.parse.unquote(uri[len('miazdoc:'):]).lstrip('/')
        if name:
            GLib.idle_add(self._open_document, name)
        return True

    def _open_document(self, name):
        actions = self.app.get_service('actions')
        if actions is not None:
            try:
                actions.document_display(name)
            except Exception as error:
                self.log.error(f"Could not open document '{name}': {error}")
        return False

    def _on_load_changed(self, webview, _event):
        self._back_button.set_sensitive(webview.can_go_back())

    def _on_plugins_updated(self, *_args):
        # Plugin set changed (load/unload); the description column may need to
        # be refreshed even if WWW directories did not change.
        self._refresh_pages()

    # WWW directory monitor

    def _setup_www_monitor(self):
        root = self._www_root()
        try:
            os.makedirs(root, exist_ok=True)
        except OSError as error:
            self.log.warning(f"Cannot create WWW root {root}: {error}")
            return
        try:
            gfile = Gio.File.new_for_path(root)
            self._www_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            self._www_monitor.connect('changed', self._on_www_changed)
            self.log.debug(f"WWW monitor started on {root}")
        except Exception as error:
            self.log.warning(f"Could not set up WWW monitor on {root}: {error}")
            self._www_monitor = None

    _WATCHED_EVENTS = frozenset({
        Gio.FileMonitorEvent.CREATED,
        Gio.FileMonitorEvent.DELETED,
        Gio.FileMonitorEvent.MOVED_IN,
        Gio.FileMonitorEvent.MOVED_OUT,
        Gio.FileMonitorEvent.RENAMED,
    })

    def _on_www_changed(self, _monitor, _file, _other_file, event_type):
        if event_type not in self._WATCHED_EVENTS:
            return
        if self._www_debounce_id > 0:
            GLib.source_remove(self._www_debounce_id)
        self._www_debounce_id = GLib.timeout_add(500, self._flush_www_refresh)

    def _flush_www_refresh(self):
        self._www_debounce_id = 0
        self._refresh_pages()
        return False
