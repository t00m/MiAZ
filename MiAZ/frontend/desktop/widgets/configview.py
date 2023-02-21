#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import gi
from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import File, Group, Person, Country, Purpose, Concept
from MiAZ.backend.config import MiAZConfigGroups
from MiAZ.backend.config import MiAZConfigPeople
from MiAZ.backend.config import MiAZConfigSentBy
from MiAZ.backend.config import MiAZConfigSentTo
from MiAZ.backend.config import MiAZConfigCountries
from MiAZ.backend.config import MiAZConfigPurposes
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView, ColIcon
from MiAZ.frontend.desktop.widgets.dialogs import MiAZDialogAdd
from MiAZ.frontend.desktop.widgets.selector import MiAZSelector
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnView
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewCountry
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewGroup
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPurpose
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewPerson
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewProject


class MiAZConfigView(MiAZSelector):
    """"""
    __gtype_name__ = 'MiAZConfigView'
    config_for = None

    def __init__(self, app):
        super(MiAZSelector, self).__init__(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = get_logger('MiAZConfigView')
        self.backend = self.app.get_backend()
        self.conf = self.backend.conf
        self.set_vexpand(True)

    def get_config_for(self):
        return self.config.config_for

    def _setup_view(self):
        selector = MiAZSelector(self.app)
        frmView = Gtk.Frame()
        self.view = MiAZColumnView(self.app)
        self.view.set_filter(self._do_filter_view)
        frmView.set_child(self.view)
        return selector


class MiAZCountries(MiAZConfigView):
    """Manage countries from Repo Settings. Edit disabled"""
    __gtype_name__ = 'MiAZCountries'
    current = None

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=False)
        super().__init__(app)
        self.config = self.conf['Country']

    def _setup_view_finish(self):
        # Setup Available Column View
        self.viewAv = MiAZColumnViewCountry(self.app)
        self.add_columnview_available(self.viewAv)

        # Setup Used Column View
        self.viewSl = MiAZColumnViewCountry(self.app)
        self.add_columnview_used(self.viewSl)

    def _update_view_available(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_available()
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewAv.update(items)

    def _update_view_used(self):
        items = []
        item_type = self.config.model
        countries = self.config.load_used()
        for code in countries:
            items.append(item_type(id=code, title=countries[code], icon='%s.svg' % code))
        self.viewSl.update(items)


class MiAZGroups(MiAZConfigView):
    """Manage groups from Repo Settings"""
    __gtype_name__ = 'MiAZGroups'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Group']

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewGroup(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewGroup(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPeople(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZPeople'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Person']

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPeopleSentBy(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZSentBy'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['SentBy']

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPeopleSentTo(MiAZConfigView):
    """Class for managing People from Settings"""
    __gtype_name__ = 'MiAZSentTo'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['SentTo']

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPerson(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPerson(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZPurposes(MiAZConfigView):
    """Manage purposes from Repo Settings"""
    __gtype_name__ = 'MiAZPurposes'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Purpose']

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewPurpose(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewPurpose(self.app)
        self.add_columnview_used(self.viewSl)

class MiAZProjects(MiAZConfigView):
    """Manage projects from Repo Settings"""
    __gtype_name__ = 'MiAZProjects'

    def __init__(self, app):
        super(MiAZConfigView, self).__init__(app, edit=True)
        super().__init__(app)
        self.config = self.conf['Project']

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewProject(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewProject(self.app)
        self.add_columnview_used(self.viewSl)
