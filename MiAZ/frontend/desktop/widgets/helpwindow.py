# File: helpwindow.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The user help, shown in its own window with WebKit.

from gettext import gettext as _

import gi
gi.require_version('WebKit', '6.0')

from gi.repository import Adw, Gtk, WebKit

from MiAZ.backend.help import help_uri, is_help_uri, with_theme
from MiAZ.backend.log import MiAZLog


class MiAZHelpWindow(Adw.Window):
    """A top-level window showing one help site, reused for every topic.

    It is a separate window, not a dialog, so the user can keep it open beside
    MiAZ and follow a page while doing what it describes. Closing it hides it;
    the next topic loads into the same window and the same history.
    """
    __gtype_name__ = 'MiAZHelpWindow'

    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        self.log = MiAZLog('MiAZ.HelpWindow')
        self.help_dir = app.get_env()['GPATH']['HELP']
        self.set_title(_('MiAZ Help'))
        self.set_default_size(960, 720)
        self.set_hide_on_close(True)

        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.set_hexpand(True)
        self.webview.connect('decide-policy', self._on_decide_policy)
        self.webview.connect('load-changed', self._on_load_changed)
        self.webview.get_back_forward_list().connect('changed', self._on_history_changed)

        header = Adw.HeaderBar()
        self.btn_back = Gtk.Button(icon_name='go-previous-symbolic',
                                   tooltip_text=_('Back'))
        self.btn_back.connect('clicked', lambda *_: self.webview.go_back())
        self.btn_forward = Gtk.Button(icon_name='go-next-symbolic',
                                      tooltip_text=_('Forward'))
        self.btn_forward.connect('clicked', lambda *_: self.webview.go_forward())
        btn_home = Gtk.Button(icon_name='go-home-symbolic',
                              tooltip_text=_('Help contents'))
        btn_home.connect('clicked', lambda *_: self.show_topic())
        header.pack_start(self.btn_back)
        header.pack_start(self.btn_forward)
        header.pack_start(btn_home)
        btn_external = Gtk.Button(icon_name='external-link-symbolic',
                                  tooltip_text=_('Open in the web browser'))
        btn_external.connect('clicked', self._on_open_external)
        header.pack_end(btn_external)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self.webview)
        self.set_content(toolbar)
        self._on_history_changed()

        self._style = Adw.StyleManager.get_default()
        self._style.connect('notify::dark', self._on_style_changed)

    def show_topic(self, help_id=None):
        """Load a topic by help id and bring the window forward."""
        uri = help_uri(help_id, self.help_dir, self._style.get_dark())
        self.log.debug(f"Help: {uri}")
        self.webview.load_uri(uri)
        self.present()
        return uri

    def get_uri(self):
        return self.webview.get_uri()

    def _on_history_changed(self, *args):
        self.btn_back.set_sensitive(self.webview.can_go_back())
        self.btn_forward.set_sensitive(self.webview.can_go_forward())

    def _on_load_changed(self, _webview, event):
        if event == WebKit.LoadEvent.FINISHED:
            self._on_history_changed()

    def _on_style_changed(self, *args):
        # The site keeps the theme parameter on every link, so the page on
        # screen and everything reached from it would stay in the old scheme.
        # Swapping the parameter and reloading follows the desktop instead.
        uri = self.webview.get_uri()
        if not uri or not is_help_uri(uri, self.help_dir):
            return
        themed = with_theme(uri, self._style.get_dark())
        if themed != uri:
            self.webview.load_uri(themed)

    def _on_decide_policy(self, _webview, decision, decision_type):
        if decision_type not in (WebKit.PolicyDecisionType.NAVIGATION_ACTION,
                                 WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            return False
        uri = decision.get_navigation_action().get_request().get_uri()
        if is_help_uri(uri, self.help_dir):
            if decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
                # A help page asking for a new window gets this one.
                decision.ignore()
                self.webview.load_uri(uri)
                return True
            return False
        # Everything outside the help belongs in the user's web browser,
        # where it has an address bar and the user's own settings.
        decision.ignore()
        self._launch(uri)
        return True

    def _on_open_external(self, *args):
        uri = self.webview.get_uri()
        if uri:
            self._launch(uri)

    def _launch(self, uri):
        Gtk.UriLauncher.new(uri).launch(self, None, self._on_launched, uri)

    def _on_launched(self, launcher, result, uri):
        try:
            launcher.launch_finish(result)
        except Exception as error:
            self.log.warning(f"Help: could not open {uri}: {error}")
