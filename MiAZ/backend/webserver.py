#!/usr/bin/python3

"""
# File: webserver.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Embedded HTTP server serving static files from
#              $HOME/.MiAZ/var/www/html. Runs in a background thread so it
#              does not block the GTK main loop. Plugins resolve it via
#              `app.get_service('webserver')` and read host/port from there.
"""

import functools
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class _MiAZHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Request handler that funnels stdlib access logs through MiAZLog.

    `_logger` is set by `MiAZWebServer.start` before the server is bound, so
    every handler instance the threaded server spawns reaches the same logger
    without needing per-request state.
    """
    _logger = None

    def log_message(self, fmt, *args):
        if self._logger is None:
            return
        try:
            self._logger.debug(fmt % args)
        except Exception:
            self._logger.debug(' '.join(str(a) for a in args))

    def log_error(self, fmt, *args):
        if self._logger is None:
            return
        try:
            self._logger.error(fmt % args)
        except Exception:
            self._logger.error(' '.join(str(a) for a in args))


class MiAZWebServer(GObject.GObject):
    """Embedded localhost HTTP server."""
    __gtype_name__ = 'MiAZWebServer'

    def __init__(self, app, host='127.0.0.1', port=0):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.WebServer')
        self._bind_host = host
        self._bind_port = port
        self._host = None
        self._port = None
        self._httpd = None
        self._thread = None
        self.app.connect('application-finished', self._on_application_finished)

    def get_root(self):
        """Return the directory served by the webserver."""
        ENV = self.app.get_env()
        return ENV['LPATH']['WWW']

    def get_host(self):
        """Return the host the server is bound to, or None if not running."""
        return self._host

    def get_port(self):
        """Return the TCP port assigned by the OS, or None if not running."""
        return self._port

    def get_url(self):
        """Return the base URL plugins can use, or None if not running."""
        if self._host is None or self._port is None:
            return None
        return f"http://{self._host}:{self._port}/"

    def is_running(self):
        return self._httpd is not None

    def start(self):
        """Bind the socket and start the serving thread. No-op if running."""
        if self._httpd is not None:
            return
        root = self.get_root()
        os.makedirs(root, exist_ok=True)
        _MiAZHTTPRequestHandler._logger = self.log
        handler = functools.partial(_MiAZHTTPRequestHandler, directory=root)
        try:
            self._httpd = ThreadingHTTPServer((self._bind_host, self._bind_port), handler)
        except OSError as error:
            self.log.error(f"WebServer: failed to bind {self._bind_host}:{self._bind_port}: {error}")
            self._httpd = None
            return
        self._host, self._port = self._httpd.server_address[:2]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name='MiAZ-WebServer',
            daemon=True,
        )
        self._thread.start()
        self.log.info(f"WebServer running at {self.get_url()} (root: {root})")

    def stop(self):
        """Shut down the server and join its thread. No-op if not running."""
        if self._httpd is None:
            return
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except Exception as error:
            self.log.warning(f"WebServer: error during shutdown: {error}")
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._httpd = None
        self._thread = None
        self._host = None
        self._port = None
        self.log.info("WebServer stopped")

    def _on_application_finished(self, *args):
        self.stop()
