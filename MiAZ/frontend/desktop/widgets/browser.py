#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
# File: browser.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Web browser widget
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Soup', '2.4')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Soup
from gi.repository import WebKit2 as WebKit

from MiAZ.backend.log import get_logger


class BasicoBrowser(WebKit.WebView):
    def __init__(self):
        super().__init__()

    def _setup_widget(self):
        self.log = get_logger('MiAZ.Browser')
        self.web_context = WebKit.WebContext.get_default()
        self.web_settings = WebKit.Settings()
        self.web_settings.set_enable_smooth_scrolling(True)
        self.web_settings.set_enable_plugins(False)

        WebKit.WebView.__init__(self,
                                 web_context=self.web_context,
                                 settings=self.web_settings)
        self.connect('load-failed',self._on_load_failed)

    def _get_api(self, uri):
        """Use Soup.URI to split uri
        Args:
            uri (str)
        Returns:
            A list with two strings representing a path and fragment
        """
        path = None
        fragment = None

        if uri:
            soup_uri = Soup.URI.new(uri)
            action = soup_uri.host
            args = soup_uri.path.split('/')[1:]

        return [action, args]


    def _on_append_items(self, webview, context_menu, hit_result_event, event):
        """Attach custom actions to browser context menu"""
        # ~ # Example:
        # ~ action = Gtk.Action("help", "Basico Help", None, None)
        # ~ action.connect("activate", self.display_help)
        # ~ option = WebKit.ContextMenuItem().new(action)
        # ~ context_menu.prepend(option)
        pass


    def load_url(self, url):
        self.log.debug("Loading url: %s", url)
        self.load_uri(url)

    def _on_decide_policy(self, webview, decision, decision_type):
        """Decide what to do when clicked on link
        Args:
            webview (WebKit2.WebView)
            decision (WebKit2.PolicyDecision)
            decision_type (WebKit2.PolicyDecisionType)
        Returns:
            True to stop other handlers from being invoked for the event.
            False to propagate the event further.
        """
        if decision_type is WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            action = WebKit.NavigationPolicyDecision.get_navigation_action(decision)
            click = action.get_mouse_button() != 0
            uri = webview.get_uri()
            if click:
                self.log.debug("User clicked in link: %s", uri)

    def _on_load_changed(self, webview, event):
        uri = webview.get_uri()
        if event == WebKit.LoadEvent.STARTED:
            self.log.debug("Load started for url: %s", uri)
        elif event == WebKit.LoadEvent.COMMITTED:
            self.log.debug("Load committed for url: %s", uri)
        elif event == WebKit.LoadEvent.FINISHED:
            self.log.debug("Load finished for url: %s", uri)
            if len(uri) == 0:
                self.log.debug("Url not loaded")

    def _on_load_failed(self, webview, load_event, failing_uri, error):
        pass
