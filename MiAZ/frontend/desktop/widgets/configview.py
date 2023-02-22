#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from gi.repository import Gtk

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
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

    def __init__(self, app, config=None):
        super(MiAZSelector, self).__init__(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.log = get_logger('MiAZConfigView')
        self.backend = self.app.get_backend()
        self.conf = self.backend.conf
        self.config = self.conf[config]
        self.config.connect('used-updated', self.update)
        self.config.connect('available-updated', self.update)
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
        super().__init__(app, 'Country')

    def _setup_view_finish(self):
        # Setup Available and Used Column Views
        self.viewAv = MiAZColumnViewCountry(self.app)
        self.add_columnview_available(self.viewAv)
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
        super().__init__(app, 'Group')

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
        super().__init__(app, 'People')

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
        super().__init__(app, 'SentBy')
        # Trick to keep People sync for SentBy/SentTo
        self.config_paired = self.conf['SentTo']
        self.config_paired.connect('available-updated', self.update)

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
        super().__init__(app, 'SentTo')
        # Trick to keep People sync for SentBy/SentTo
        self.config_paired = self.conf['SentBy']
        self.config_paired.connect('available-updated', self.update)

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
        super().__init__(app, 'Purpose')

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
        super().__init__(app, 'Project')

    def _setup_view_finish(self):
        # Setup Available and Used Columns Views
        self.viewAv = MiAZColumnViewProject(self.app)
        self.add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewProject(self.app)
        self.add_columnview_used(self.viewSl)
