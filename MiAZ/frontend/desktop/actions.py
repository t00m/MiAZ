#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from gi.repository import GObject

from MiAZ.backend.log import get_logger
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog

class MiAZActions(GObject.GObject):
    def __init__(self, app):
        self.log = get_logger('MiAZActions')
        self.app = app
        self.workspace = self.app.get_workspace()
        self.backend = self.app.get_backend()

    def document_display(self, *args):
        selection = self.workspace.get_selection()
        model = self.workspace.get_model_filter()
        selected = selection.get_selection()
        pos = selected.get_nth(0)
        item = model.get_item(pos)
        filepath = item.id
        os.system("xdg-open '%s'" % filepath)

    def document_switch(self, switch, activated):
        selection = self.workspace.get_selection()
        selected = selection.get_selection()
        model = self.workspace.get_model_filter()
        switched = self.workspace.get_switched()
        pos = selected.get_nth(0)
        item = model.get_item(pos)
        if activated:
            switched.add(item.id)
        else:
            switched.remove(item.id)
        self.log.debug(switched)

    def document_rename(self, *args):
        item = self.workspace.get_item()
        source = item.id
        repodct = self.backend.get_repo_dict()
        if repodct[source]['valid']:
            basename = os.path.basename(source)
            filename = basename[:basename.rfind('.')]
            target = filename.split('-')
        else:
            target = repodct[source]['suggested'].split('-')
        dialog = MiAZRenameDialog(self.app, source, target)
        dialog.show()
