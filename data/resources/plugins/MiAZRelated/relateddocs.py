# pylint: disable=E1101

"""
# File: relateddocs.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Show the documents belonging to the same case
"""

import os
import sys
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':        'relateddocs',
    'Name':          'MiAZRelated',
    'Loader':        'Python3',
    'Description':   _('Show the documents belonging to the same case'),
    'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2026 Tomás Vírseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
    'Version':       '0.3.0',
    'Category':      'Organise',
    'Subcategory':   'Search'
}


class Related(MiAZExtension):
    """Read one document as the case it belongs to.

    A cancellation has a request before it and a receipt after it. They share
    a concept, and the parties tell apart the side that kept the case from the
    side that answered it.
    """
    __gtype_name__ = 'MiAZRelatedPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.util = self.app.get_service('util')
        self.actions = self.app.get_service('actions')
        self.srvdlg = self.app.get_service('dialogs')
        self.repository = self.app.get_service('repo')

        source_dir = os.path.dirname(os.path.abspath(__file__))
        if source_dir not in sys.path:
            sys.path.insert(0, source_dir)

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
            menuitem = self.plugin.get_menu_item(callback=self.show_related)
            self.plugin.install_menu_entry(menuitem)
            self.plugin.set_started(started=True)

    def find_related(self, document):
        """The case the given document belongs to."""
        from related.chain import related
        filenames = [os.path.basename(path)
                     for path in self.util.get_files(self.repository.docs)]
        return related(filenames, os.path.basename(document))

    def show_related(self, *args):
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return
        items = self.workspace.get_selected_items()
        document = os.path.basename(items[0].id)
        report = self.find_related(document)
        found = len(report['same_party']) + len(report['other_party'])
        if not found:
            self.srvdlg.show_toast(_('No other document shares this concept'))
            return
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_noop(
            title=_('Documents in this case'),
            body=_('{count} documents share the concept of {document}').format(
                count=found, document=document),
            widget=self._build_page(report),
            width=760, height=560)
        self.app.add_widget('related-dialog', dialog)
        dialog.present(window)

    def _build_page(self, report):
        page = Adw.PreferencesPage()
        page.set_hexpand(True)
        page.set_vexpand(True)
        sections = (
            ('same_party', _('The same parties'),
             _('The case as one side of it kept it.')),
            ('other_party', _('Somebody else'),
             _('The same concept involving other parties, which is how a '
               'request and its answer find each other.')),
        )
        for key, title, explanation in sections:
            if not report[key]:
                continue
            group = Adw.PreferencesGroup()
            group.set_title(title)
            group.set_description(explanation)
            for filename in report[key]:
                group.add(self._build_row(filename))
            page.add(group)
        return page

    def _build_row(self, filename):
        from related.chain import fields
        parts = fields(filename)
        row = Adw.ActionRow()
        row.set_title(self.util.filename_date_human_simple(parts[0]) or _('No date'))
        row.set_subtitle(_('{purpose}, from {sender} to {recipient}').format(
            purpose=parts[4], sender=parts[3], recipient=parts[6]))
        row.set_tooltip_text(filename)
        button = Gtk.Button(label=_('Open'))
        button.set_valign(Gtk.Align.CENTER)
        button.connect('clicked', lambda *_a, doc=filename: self.actions.document_display(doc))
        row.add_suffix(button)
        return row
