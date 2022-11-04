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
        # ~ self.workspace = self.app.get_workspace()
        self.backend = self.app.get_backend()

    def document_display(self, filepath):
        os.system("xdg-open '%s'" % filepath)

    def document_rename(self, source):
        repodct = self.backend.get_repo_dict()
        if repodct[source]['valid']:
            basename = os.path.basename(source)
            filename = basename[:basename.rfind('.')]
            target = filename.split('-')
        else:
            target = repodct[source]['suggested'].split('-')
        dialog = MiAZRenameDialog(self.app, source, target)
        dialog.show()

    def dropdown_populate(self, dropdown, item_type, conf):
        # Populate the model
        model = dropdown.get_model()
        config = self.app.get_config(conf)
        items = config.load()
        config_is = config.get_config_is()

        # foreign key is used when the local configuration is saved as a
        # list, but it gets the name from global dictionary (eg.: Countries)
        foreign = config.get_config_foreign()
        if foreign:
            gitems = config.load_global()

        items = config.load()
        if isinstance(items, list):
            items = sorted(items)
        self.log.debug("%s > %s", conf, type(items))

        model.remove_all()
        model.append(item_type(id='Any', name='Any'))
        for key in items:
            if config_is is dict:
                if foreign:
                    model.append(item_type(id=key, name="%s (%s)" % (gitems[key], key)))
                else:
                    model.append(item_type(id=key, name="%s (%s)" % (items[key], key)))
            else:
                model.append(item_type(id=key, name=key))
