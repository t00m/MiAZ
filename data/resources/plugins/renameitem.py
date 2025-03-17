#!/usr/bin/python3
# pylint: disable=E1101

"""
# File: renameitem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for rename documents
"""

import os
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog


class MiAZToolbarRenameItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarRenameItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = MiAZLog('Plugin.RenameItem')
        self.app = None

    def do_activate(self):
        self.app = self.object.app
        self.actions = self.app.get_service('actions')
        self.util = self.app.get_service('util')
        self.repository = self.app.get_service('repo')
        workspace = self.app.get_widget('workspace')
        workspace.connect('workspace-loaded', self.add_toolbar_button)
        workspace.connect('workspace-view-updated', self._on_selection_changed)
        view = self.app.get_widget('workspace-view')
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")

    def _on_selection_changed(self, *args):
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-rename')
        if button is not None:
            visible = len(items) == 1
            button.set_visible(visible)

    def add_toolbar_button(self, *args):
        if self.app.get_widget('toolbar-top-button-rename') is None:
            factory = self.app.get_service('factory')
            toolbar_top_right = self.app.get_widget('headerbar-right-box')
            button = factory.create_button(icon_name='io.github.t00m.MiAZ-text-editor-symbolic', callback=self.callback)
            button.set_visible(False)
            self.app.add_widget('toolbar-top-button-rename', button)
            toolbar_top_right.append(button)

    def callback(self, *args):
        try:
            workspace = self.app.get_widget('workspace')
            item = workspace.get_selected_items()[0]
            self.document_rename_single(item.id)
        except IndexError:
            self.log.debug("No item selected")

    def document_rename_single(self, doc):
        self.log.debug(f"Rename {doc}")
        srvdlg = self.app.get_service('dialogs')
        # ~ actions = self.app.get_service('actions')
        rename_widget = self.app.add_widget('rename-widget', MiAZRenameDialog(self.app))
        rename_widget.set_data(doc)
        dtype = "question"
        text = '' # _(f'<big>{i_title} {selected_item.id} is still being used</big>')
        window = self.app.get_widget('window')
        title = "Rename document"
        dialog = srvdlg.create(enable_response=True, dtype=dtype, title=title, body=text, widget=rename_widget)
        dialog.add_response("preview", _("Preview"))
        self.app.add_widget('dialog-rename', dialog)
        dialog.connect('response', self._on_rename_response, rename_widget)
        dialog.present(window)

    def _on_rename_response(self, dialog, response, rename_widget):
        if response == 'apply':
            window = self.app.get_widget('window')
            srvdlg = self.app.get_service('dialogs')
            body = _(f"\nYou are about to rename this document")
            title = _('Are you sure?')
            dialog_confirm = srvdlg.create(enable_response=True, dtype='question', title=title, body=body, callback=self.on_answer_question_rename, data=(rename_widget, dialog))
            dialog_confirm.present(window)
        elif response == 'preview':
            window = self.app.get_widget('window')
            doc = rename_widget.get_filepath_source()
            self.actions.document_display(doc)
            # ~ dialog.present(window)

    def on_answer_question_rename(self, dialog, response, data=tuple):
        rename_widget, parent_dialog = data
        srvdlg = self.app.get_service('dialogs')
        window = self.app.get_widget('window')
        if response == 'apply':
            bsource = rename_widget.get_filepath_source()
            source = os.path.join(self.repository.docs, bsource)
            btarget = rename_widget.get_filepath_target()
            target = os.path.join(self.repository.docs, btarget)
            renamed = self.util.filename_rename(source, target)
            if not renamed:
                text = f"<big>Another document with the same name already exists in this repository.</big>"
                title=_('Renaming not possible')
                dlgerror = srvdlg.create(enable_response=False, dtype='error', title=title, body=text)
                dlgerror.present(window)
        else:
            parent_dialog.present(window)
