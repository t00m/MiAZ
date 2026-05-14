#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: export2dir.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for exporting items to a given directory
"""

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin
from MiAZ.backend.models import Country, Date, Group
from MiAZ.backend.models import Purpose, SentBy, SentTo

plugin_info = {
        'Module':        'export2dir',
        'Name':          'MiAZExport2Dir',
        'Loader':        'Python3',
        'Description':   _('Export to directory'),
        'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
        'Copyright':     'Copyright © 2025 Tomás Vírseda',
        'Website':       'http://github.com/t00m/MiAZ',
        'Help':          'http://github.com/t00m/MiAZ/README.adoc',
        'Version':       '0.5',
        'Category':      'Data Management',
        'Subcategory':   'Export'
    }

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6

Patterns = {
    'Y': _('Year'),
    'm': _('Month'),
    'd': _('Day'),
    'C': _('Country'),
    'G': _('Group'),
    'P': _('Purpose'),
    'B': _('Sent by'),
    'T': _('Sent to'),
}

class Export2Dir(MiAZExtension):
    """Export selected documents to a directory"""

    __gtype_name__ = 'MiAZExport2DirPlugin'
    plugin = None

    def do_activate(self):
        """Plugin activation"""
        # Setup plugin
        ## Get pointer to app
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)

        ## Initialize plugin
        self.plugin.register(self, plugin_info)

        ## Get logger
        self.log = self.plugin.get_logger()

        # Connect startup signals
        self.workspace = self.app.get_widget('workspace')
        self.workspace.connect('workspace-loaded', self.startup)

        # Get services
        self.actions = self.app.get_service('actions')
        self.factory = self.app.get_service('factory')
        self.repository = self.app.get_service('repo')
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')

    def do_deactivate(self):
        self.log.warning("Deactivation not implemented")
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            # Create menu item for plugin
            mnuItemName = self.plugin.get_menu_item_name()
            menuitem = self.factory.create_menuitem(name=mnuItemName, label=_('Export to directory'), callback=self.export)

            # Add plugin to its default (sub)category
            self.plugin.install_menu_entry(menuitem)

            # Plugin configured
            self.plugin.set_started(started=True)

    def export(self, *args):
        self.items = self.workspace.get_selected_items()
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return
        self.target_dir = None
        # Options for the dialog
        frame = Gtk.Frame()
        listbox = Gtk.ListBox.new()

        ## Pattern row
        self.chkPattern = self.factory.create_button_check(title=_('Export with pattern'), callback=None)
        self.chkPattern.set_valign(Gtk.Align.CENTER)
        self.chkPattern.set_tooltip_text('Check this box to activate the pattern.\nOtherwise, all documents will be exported in the same folder.')
        self.app.add_widget('plugin-export2dir-chkpattern', self.chkPattern)
        self.etyPattern = self.app.add_widget('plugin-export2dir-etypattern', Gtk.Entry())
        self.etyPattern.set_valign(Gtk.Align.CENTER)
        self.etyPattern.set_text('CYmGP')  # /{target}/{Country}/{Year}/{month}/{Group}/{Purpose}
        widgets = []
        label = Gtk.Label.new(_('Each letter represent a directory:\n'))
        widgets.append(label)
        for key in Patterns:
            label = Gtk.Label()
            label.set_markup(f'<b>{key}</b> = {Patterns[key]}')
            label.set_xalign(0.0)
            widgets.append(label)
        btpPattern = self.factory.create_button_popover(icon_name='io.github.t00m.MiAZ-dialog-information-symbolic', widgets=widgets)
        btpPattern.set_valign(Gtk.Align.CENTER)
        hbox = self.factory.create_box_horizontal()
        hbox.append(self.chkPattern)
        hbox.append(self.etyPattern)
        hbox.append(btpPattern)
        self.row_pattern = Adw.ActionRow(title=_('Select pattern'))
        self.row_pattern.add_suffix(hbox)
        listbox.append(self.row_pattern)

        ## Target directory
        button = Gtk.Button()
        button.set_valign(Gtk.Align.CENTER)
        button.set_label('Select folder')
        button.connect('clicked', self._on_select_folder)
        self.row_target = Adw.ActionRow(title=_('Select target folder'))
        self.row_target.set_subtitle(_('No target folder set yet'))
        self.row_target.add_suffix(button)
        listbox.append(self.row_target)
        frame.set_child(listbox)

        # Dialog
        parent = self.app.get_widget('window')
        title = _('Export to directory')
        dialog = self.srvdlg.show_action(title=title, callback=self._on_dialog_response, widget=frame, width=800)
        dialog.present(parent)

    def _on_select_folder(self, *args):
        self.factory.create_filechooser_for_directories(self._on_select_folder_response)

    def _on_select_folder_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self.target_dir = folder.get_path()
            self.row_target.set_subtitle(self.target_dir)
        except Exception as error:
            self.srvdlg.show_error(title='Error selecting files', body=str(error))
            self.log.error(f"Error selecting files: {error}")

    def _on_dialog_response(self, dialog, response, data):
        def get_pattern_paths(item):
            fields = self.util.get_fields(item.id)
            paths = {}
            paths['Y'] = '%04d' % datetime.strptime(fields[0], '%Y%m%d').year
            paths['m'] = "%02d" % datetime.strptime(fields[0], '%Y%m%d').month
            paths['d'] = "%02d" % datetime.strptime(fields[0], '%Y%m%d').day
            paths['C'] = fields[Field[Country]]
            paths['G'] = fields[Field[Group]]
            paths['P'] = fields[Field[Purpose]]
            paths['B'] = fields[Field[SentBy]]
            paths['T'] = fields[Field[SentTo]]
            return paths

        if response == 'apply':
            target_dir_valid = os.path.exists(self.target_dir)
            if self.target_dir is not None and target_dir_valid:
                if self.chkPattern.get_active():
                    keys = [key for key in self.etyPattern.get_text()]
                    for item in self.items:
                        thispath = []
                        thispath.append(self.target_dir)
                        source = os.path.join(self.repository.docs, item.id)
                        try:
                            paths = get_pattern_paths(item)
                            for key in keys:
                                thispath.append(paths[key])
                            target = os.path.join(*thispath)
                            os.makedirs(target, exist_ok=True)
                            self.util.filename_export(source, target)
                        except ValueError as error:
                            self.log.error(f"{os.path.basename(source)} couldn't be exported.")
                            self.log.error("Reason: filename not compliant with MiAZ format")
                else:
                    for item in self.items:
                        source = os.path.join(self.repository.docs, item.id)
                        target = os.path.join(self.target_dir, os.path.basename(item.id))
                        self.util.filename_export(source, target)
                self.util.directory_open(self.target_dir)
                window = self.workspace.get_root()
                body = _('<big>Check your default file browser</big>')
                self.srvdlg.create(dtype='info', title=_('Export successful'), body=body).present()
        else:
            self.srvdlg.show_error(title=_('Action canceled'), body=_('No documents exported'))
