#!/usr/bin/python3
"""
# File: extlibs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Frontend helper for the optional external-libraries venv.

Centralises the GTK side of the venv feature so the first-run prompt, the
settings page and the AI error dialogs all install libraries the same way:
collect the requirements of the enabled plugins, run the backend venv service
and show a small progress dialog. The heavy lifting (venv creation, pip) lives
in MiAZ.backend.venv; this only drives it and reports progress.
"""

import os
from gettext import gettext as _

from gi.repository import Adw, Gtk, Pango

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.venv import requirement_name


class MiAZExtLibs:
    """Collect plugin requirements and install them into the venv with a dialog."""

    def __init__(self, app):
        self.app = app
        self.log = MiAZLog('MiAZ.ExtLibs')

    def is_enabled(self):
        """True when the external-libraries venv already exists."""
        return self.app.get_service('venv').exists()

    # First-run prompt (shown once)

    def _marker(self):
        etc = self.app.get_env()['LPATH']['ETC']
        return os.path.join(etc, 'extlibs-prompted')

    def already_prompted(self):
        return os.path.exists(self._marker())

    def mark_prompted(self):
        try:
            os.makedirs(os.path.dirname(self._marker()), exist_ok=True)
            with open(self._marker(), 'w', encoding='utf-8') as fh:
                fh.write('1')
        except OSError as error:
            self.log.warning(f'Cannot write extlibs marker: {error}')

    def maybe_prompt_first_run(self):
        """Offer to download external libraries once, after the first repo.

        Shown only when the feature is off, was never offered, and at least one
        enabled plugin declares requirements. Does nothing otherwise.
        """
        if self.already_prompted() or self.is_enabled():
            return
        if self.app.get_service('venv').is_busy():
            return
        reqs = self.collect_enabled_requirements()
        if not reqs:
            return
        window = self.app.get_widget('window')
        self.mark_prompted()
        dialog = Adw.AlertDialog(
            heading=_('Enable AI features'),
            body=_('Some enabled plugins can use AI providers that need extra '
                   'Python libraries. MiAZ can download them into a private '
                   'folder in your home directory. Nothing is installed into '
                   'the system Python.'))
        dialog.add_response('later', _('Not now'))
        dialog.add_response('enable', _('Download libraries'))
        dialog.set_response_appearance('enable', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('enable')
        dialog.set_close_response('later')
        dialog.connect('response', self._on_first_run_response, window, reqs)
        dialog.present(window)

    def _on_first_run_response(self, dialog, response, window, reqs):
        if response == 'enable':
            self.install(window, requirements=reqs)

    def enabled_plugin_dirs(self):
        plugin_system = self.app.get_service('plugin-system')
        if plugin_system is None:
            return []
        dirs = []
        for plugin in plugin_system.plugins:
            try:
                if plugin.is_loaded():
                    pdir = plugin.get_module_dir()
                    if pdir:
                        dirs.append(pdir)
            except Exception:
                continue
        return dirs

    def collect_enabled_requirements(self):
        """Requirements declared by every currently enabled plugin."""
        venv = self.app.get_service('venv')
        return venv.requirements_for(self.enabled_plugin_dirs())

    def requirements_for_plugin(self, module_name):
        """Requirements declared by a single plugin (by module name)."""
        plugin_system = self.app.get_service('plugin-system')
        info = plugin_system.get_plugin_info(module_name) if plugin_system else None
        pdir = info.get_module_dir() if info is not None else None
        venv = self.app.get_service('venv')
        return venv.requirements_for([pdir]) if pdir else []

    def plugins_by_library(self):
        """Map a library name to the enabled plugins that require it.

        Keys are normalized like requirement and distribution names, so they
        match venv.installed_details(). Values are sorted plugin display names.
        """
        venv = self.app.get_service('venv')
        plugin_system = self.app.get_service('plugin-system')
        result = {}
        if plugin_system is None:
            return result
        for plugin in plugin_system.plugins:
            try:
                if not plugin.is_loaded():
                    continue
                pdir = plugin.get_module_dir()
                if not pdir:
                    continue
                label = plugin.get_name() or plugin.get_module_name()
                for req in venv.requirements_for([pdir]):
                    name = requirement_name(req).lower().replace('_', '-')
                    if name:
                        result.setdefault(name, set()).add(label)
            except Exception:
                continue
        return {name: sorted(labels) for name, labels in result.items()}

    def install(self, parent, requirements=None, on_done=None):
        """Install requirements into the venv, showing a progress dialog.

        When requirements is None, the requirements of the enabled plugins are
        used. on_done(ok) is called after the install finishes.
        """
        venv = self.app.get_service('venv')
        if venv.is_busy():
            return
        reqs = requirements if requirements is not None \
            else self.collect_enabled_requirements()

        dialog = Adw.AlertDialog(
            heading=_('External libraries'),
            body=_('Preparing…'))
        # Lock the dialog size: the pip detail line changes on every output
        # line, and letting it wrap made the dialog grow and shrink constantly.
        dialog.set_content_width(500)
        dialog.set_content_height(260)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        # Determinate progress: the venv service emits install-fraction at each
        # package boundary (pip reports no percentages through a pipe, so the
        # package is the honest unit). Until the first boundary the bar pulses
        # to show activity (venv creation, first download).
        progress = Gtk.ProgressBar()
        progress.set_show_text(True)
        progress.set_text(_('Preparing…'))
        progress.set_hexpand(True)
        box.append(progress)
        line = Gtk.Label()
        line.add_css_class('caption')
        line.add_css_class('dim-label')
        # One ellipsized row, never wrapped: a fixed-height detail line so the
        # dialog geometry stays put regardless of how long pip's output is.
        line.set_wrap(False)
        line.set_single_line_mode(True)
        line.set_ellipsize(Pango.EllipsizeMode.END)
        line.set_xalign(0.0)
        box.append(line)
        dialog.set_extra_child(box)

        dialog.add_response('close', _('Close'))
        dialog.set_close_response('close')
        dialog.set_response_enabled('close', False)

        handlers = []
        state = {'determinate': False}

        def _on_progress(_venv, text):
            line.set_text(text)
            if text.startswith('Installing '):
                progress.set_text(text)
            # Pulse only while no fraction has arrived; pulsing after
            # set_fraction would flip the bar back to activity mode.
            if not state['determinate']:
                progress.pulse()

        def _on_fraction(_venv, fraction):
            state['determinate'] = True
            progress.set_fraction(fraction)

        def _on_finished(_venv, ok, message):
            progress.set_fraction(1.0 if ok else progress.get_fraction())
            progress.set_text(_('Done') if ok else _('Failed'))
            dialog.set_body(message if message else (
                _('Done.') if ok else _('Something went wrong.')))
            dialog.set_response_enabled('close', True)
            for handler_id in handlers:
                venv.disconnect(handler_id)
            if on_done is not None:
                on_done(ok)

        handlers.append(venv.connect('install-progress', _on_progress))
        handlers.append(venv.connect('install-fraction', _on_fraction))
        handlers.append(venv.connect('install-finished', _on_finished))

        dialog.present(parent)
        venv.install_async(reqs)
