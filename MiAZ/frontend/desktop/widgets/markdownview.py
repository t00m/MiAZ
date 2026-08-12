# File: markdownview.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Reusable read-only widget that renders Markdown as styled HTML.

import urllib.parse

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gdk, Gio, GLib, Gtk, WebKit

try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
except Exception:
    Adw = None

from MiAZ.backend.log import MiAZLog

try:
    import markdown as _markdown
except ImportError:
    _markdown = None

# Links using this scheme are not opened in a browser. Instead the widget calls
# the on_command callback with the rest of the URI, so a host (for example the
# AI chat) can wire a Markdown link to an in-app action.
_COMMAND_SCHEME = 'miazcmd:'

_PAGE = (
    '<!DOCTYPE html><html><head><meta charset="utf-8">'
    '<style>{css}</style></head><body>{body}'
    '<script>window.scrollTo(0, document.body.scrollHeight);</script>'
    '</body></html>'
)


def _css(dark: bool) -> str:
    if dark:
        fg = '#e3e3e3'
        code_bg = 'rgba(255,255,255,0.08)'
        border = '#555'
        link = '#78aeed'
        quote = '#aaa'
    else:
        fg = '#2e2e2e'
        code_bg = 'rgba(0,0,0,0.06)'
        border = '#d0d0d0'
        link = '#1a5fb4'
        quote = '#666'
    return (
        "html,body{margin:0;padding:8px 10px;background:transparent;color:" + fg + ";"
        "font-family:-apple-system,'Cantarell','Segoe UI',sans-serif;"
        "font-size:14px;line-height:1.5;word-wrap:break-word;}"
        "h1,h2,h3,h4{line-height:1.25;margin:0.6em 0 0.3em;}"
        "h1{font-size:1.5em;} h2{font-size:1.3em;} h3{font-size:1.15em;}"
        "p{margin:0.4em 0;} a{color:" + link + ";text-decoration:none;}"
        "a:hover{text-decoration:underline;}"
        "code{background:" + code_bg + ";padding:0.1em 0.3em;border-radius:4px;"
        "font-family:monospace;font-size:0.92em;}"
        "pre{background:" + code_bg + ";padding:10px;border-radius:6px;overflow:auto;}"
        "pre code{background:transparent;padding:0;}"
        "blockquote{margin:0.5em 0;padding:0 0.8em;border-left:3px solid " + border + ";"
        "color:" + quote + ";}"
        "ul,ol{margin:0.4em 0;padding-left:1.4em;}"
        "table{border-collapse:collapse;margin:0.5em 0;}"
        "th,td{border:1px solid " + border + ";padding:4px 8px;}"
        "hr{border:none;border-top:1px solid " + border + ";margin:0.8em 0;}"
        "img{max-width:100%;}"
    )


class MiAZMarkdownView(Gtk.Box):
    """Render Markdown as styled, theme-aware HTML in a read-only WebKit view.

    Use set_markdown(text) to update the content. Links open in the system
    browser, except 'miazcmd:' links, which invoke the optional on_command
    callback so a host can map a link to an in-app action.
    """

    def __init__(self, app=None, on_command=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.on_command = on_command
        self.log = MiAZLog('MiAZ.MarkdownView')
        self._text = ''

        self._webview = WebKit.WebView()
        self._webview.set_hexpand(True)
        self._webview.set_vexpand(True)
        try:
            # Transparent background so the view blends with the GTK theme.
            self._webview.set_background_color(Gdk.RGBA())
        except Exception:
            pass
        self._webview.connect('context-menu', self._on_context_menu)
        self._webview.connect('decide-policy', self._on_decide_policy)
        self.append(self._webview)

    def set_markdown(self, text):
        self._text = text or ''
        self._webview.load_html(self._render(self._text), None)

    def get_markdown(self):
        return self._text

    def _render(self, text):
        if _markdown is not None:
            try:
                body = _markdown.markdown(
                    text,
                    extensions=['fenced_code', 'tables', 'sane_lists', 'nl2br'])
            except Exception as error:
                self.log.error(f"Markdown render failed: {error}")
                body = '<pre>' + GLib.markup_escape_text(text) + '</pre>'
        else:
            # No markdown library: show the raw text, escaped, in a code block.
            body = '<pre>' + GLib.markup_escape_text(text) + '</pre>'
        return _PAGE.format(css=_css(self._prefers_dark()), body=body)

    def _prefers_dark(self):
        if Adw is None:
            return False
        try:
            return Adw.StyleManager.get_default().get_dark()
        except Exception:
            return False

    def _on_context_menu(self, _webview, context_menu, _hit):
        # Read-only viewer: keep only Copy and Select All.
        context_menu.remove_all()
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.COPY))
        context_menu.append(
            WebKit.ContextMenuItem.new_from_stock_action(WebKit.ContextMenuAction.SELECT_ALL))
        return False

    def _on_decide_policy(self, _webview, decision, decision_type):
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        action = decision.get_navigation_action()
        if action.get_navigation_type() != WebKit.NavigationType.LINK_CLICKED:
            return False
        uri = action.get_request().get_uri()
        decision.ignore()
        if uri.startswith(_COMMAND_SCHEME):
            command = urllib.parse.unquote(uri[len(_COMMAND_SCHEME):])
            if self.on_command is not None:
                GLib.idle_add(self.on_command, command)
        elif uri:
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except Exception as error:
                self.log.error(f"Could not open link '{uri}': {error}")
        return True
