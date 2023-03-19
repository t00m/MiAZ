#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: renameitem.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Plugin for rename documents
"""

from datetime import datetime

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import MiAZItem, File, Group, Person, Country, Purpose, Concept, SentBy, SentTo, Date, Extension, Project, Repository
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries, MiAZGroups, MiAZPeople, MiAZPurposes, MiAZPeopleSentBy, MiAZPeopleSentTo, MiAZProjects
from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewWorkspace
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassDelete
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassProject


class MiAZToolbarRenameItemPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = 'MiAZToolbarRenameItemPlugin'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        self.log = get_logger('Plugin.RenameItem')

    def do_activate(self):
        API = self.object
        self.app = API.app
        self.actions = self.app.get_actions()
        self.backend = self.app.get_backend()
        self.factory = self.app.get_factory()
        self.util = self.backend.util
        self.workspace = API.app.get_widget('workspace')
        self.workspace.connect("extend-toolbar-top", self.add_toolbar_button)
        view = self.app.get_widget('workspace-view')
        selection = view.get_selection()
        selection.connect('selection-changed', self._on_selection_changed)

    def do_deactivate(self):
        self.log.debug("Plugin deactivation not implemented")
        API = self.object

    def _on_selection_changed(self, *args):
        items = self.workspace.get_selected_items()
        button = self.app.get_widget('toolbar-top-button-rename')
        visible = len(items) == 1
        button.set_visible(visible)

    def add_toolbar_button(self, *args):
        toolbar_top_right = self.app.get_widget('workspace-toolbar-top-right')
        button = self.factory.create_button(icon_name='miaz-res-manage', callback=self.callback)
        button.set_visible(False)
        self.app.add_widget('toolbar-top-button-rename', button)
        toolbar_top_right.prepend(button)

    def callback(self, *args):
        try:
            item = self.workspace.get_selected_items()[0]
            self.document_rename_single(item.id)
        except IndexError:
            self.log.debug("No item selected")

    def document_rename_single(self, doc):
        self.log.debug("Rename %s", doc)
        rename = self.app.get_widget('rename')
        rename.set_data(doc)
        self.app.show_stack_page_by_name('rename')

    # ~ def document_rename(self, items):

        # ~ def update_columnview(dropdown, gparamobj, columnview, dropdowns, items):
            # ~ citems = []
            # ~ for item in items:
                # ~ try:
                    # ~ source = item.id
                    # ~ name, ext = self.util.filename_details(source)
                    # ~ tmpfile = name.split('-')
                    # ~ for item_type in dropdowns:
                        # ~ n = Field[item_type]
                        # ~ value = dropdowns[item_type].get_selected_item().id
                        # ~ if value != 'None':
                            # ~ tmpfile[n] = value
                    # ~ filename = "%s.%s" % ('-'.join(tmpfile), ext)
                    # ~ target = os.path.join(os.path.dirname(source), filename)
                    # ~ txtId = "<small>%s</small>" % os.path.basename(source)
                    # ~ txtTitle = "<small>%s</small>" % os.path.basename(target)
                    # ~ citems.append(File(id=txtId, title=txtTitle))
                # ~ except Exception as error:
                    # ~ # FIXME: AtributeError: 'NoneType' object has no attribute 'id'
                    # ~ # It happens when managing resources from inside the dialog
                    # ~ # Non critical
                    # ~ pass
            # ~ columnview.update(citems)

        # ~ def calendar_day_selected(calendar, label, columnview, items):
            # ~ adate = calendar.get_date()
            # ~ y = "%04d" % adate.get_year()
            # ~ m = "%02d" % adate.get_month()
            # ~ d = "%02d" % adate.get_day_of_month()
            # ~ sdate = "%s%s%s" % (y, m, d)
            # ~ ddate = datetime.strptime(sdate, '%Y%m%d')
            # ~ label.set_text(ddate.strftime('%A, %B %d %Y'))
            # ~ citems = []
            # ~ for item in items:
                # ~ source = os.path.basename(item.id)
                # ~ name, ext = self.util.filename_details(source)
                # ~ lname = name.split('-')
                # ~ lname[0] = sdate
                # ~ target = "%s.%s" % ('-'.join(lname), ext)
                # ~ citems.append(File(id=source, title=target))
            # ~ columnview.update(citems)

        # ~ def dialog_response(dialog, response, dropdown, dropdowns, items):
            # ~ if response == Gtk.ResponseType.ACCEPT:
                # ~ for item in items:
                    # ~ source = item.id
                    # ~ name, ext = self.util.filename_details(source)
                    # ~ tmpfile = name.split('-')
                    # ~ for item_type in dropdowns:
                        # ~ n = Field[item_type]
                        # ~ value = dropdowns[item_type].get_selected_item().id
                        # ~ if value != 'None':
                            # ~ tmpfile[n] = value
                        # ~ filename = "%s.%s" % ('-'.join(tmpfile), ext)
                    # ~ target = os.path.join(os.path.dirname(source), filename)
                    # ~ self.util.filename_rename(source, target)
            # ~ dialog.destroy()

        # ~ def dialog_response_date(dialog, response, calendar, items):
            # ~ if response == Gtk.ResponseType.ACCEPT:
                # ~ adate = calendar.get_date()
                # ~ y = "%04d" % adate.get_year()
                # ~ m = "%02d" % adate.get_month()
                # ~ d = "%02d" % adate.get_day_of_month()
                # ~ sdate = "%s%s%s" % (y, m, d)
                # ~ for item in items:
                    # ~ source = os.path.basename(item.id)
                    # ~ name, ext = self.util.filename_details(source)
                    # ~ lname = name.split('-')
                    # ~ lname[0] = sdate
                    # ~ target = "%s.%s" % ('-'.join(lname), ext)
                    # ~ self.util.filename_rename(source, target)
            # ~ dialog.destroy()

        # ~ self.factory = self.app.get_factory()
        # ~ self.config = self.backend.conf

        # ~ box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        # ~ frame = Gtk.Frame()
        # ~ cv = MiAZColumnViewMassRename(self.app)
        # ~ cv.get_style_context().add_class(class_name='caption')
        # ~ cv.set_hexpand(True)
        # ~ cv.set_vexpand(True)
        # ~ frame.set_child(cv)
        # ~ dropdowns = {}
        # ~ for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            # ~ i_type = item_type.__gtype_name__
            # ~ i_title = item_type.__title__
            # ~ label = self.factory.create_label('Rename %d files by setting the field <b>%s</b> to:\n' % (len(items), i_title))
            # ~ label.set_yalign(0.5)
            # ~ dropdown = self.factory.create_dropdown_generic(item_type=item_type)
            # ~ dropdowns[item_type] = dropdown
            # ~ btnManage = self.factory.create_button('miaz-res-manage', '')
            # ~ btnManage.connect('clicked', self.manage_resource, Configview[i_type](self.app))
            # ~ self.actions.dropdown_populate(self.config[i_type], dropdown, item_type, any_value=False, none_value=True)
            # ~ dropdown.connect("notify::selected-item", update_columnview, cv, dropdowns, items)
            # ~ self.config[i_type].connect('used-updated', self.actions.dropdown_populate, dropdown, item_type, False)
            # ~ hbox = self.factory.create_box_horizontal(hexpand=False)
            # ~ hbox.append(label)
            # ~ hbox.append(dropdown)
            # ~ hbox.append(btnManage)
            # ~ box.append(hbox)
        # ~ box.append(frame)
        # ~ dialog = self.factory.create_dialog_question(self.app.win, 'Mass renaming', box, width=1024, height=600)
        # ~ dialog.connect('response', dialog_response, dropdown, dropdowns, items)
        # ~ dialog.show()