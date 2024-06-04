#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
# File: assistant.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Repository creation assistant
"""

import os
import sys
from enum import IntEnum
from abc import abstractmethod
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf

from MiAZ.backend.log import MiAZLog
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo


class PAGE(IntEnum):
    WELCOME = 0
    COUNTRIES = 1
    GROUPS = 2
    PURPOSES = 3
    SENTBY = 4
    SENTTO = 5
    CONFIRMATION = 6
    SUMMARY = 7

class MiAZAssistant(Gtk.Assistant):
    """ Start up Assistant"""

    def __init__(self, app):
        super(MiAZAssistant, self).__init__()
        self.log = MiAZLog('MiAZAssistant')
        self.app = app
        self.factory = self.app.get_service('factory')
        self.config = self.app.get_config()
        self.set_size_request(1024, 728)
        self.set_title(_('MiAZ Assistant'))
        self.completed = False


class MiAZAssistantRepo(MiAZAssistant):
    """"""
    __gtype_name__ = 'MiAZAssistantRepo'
    current = None

    def __init__(self, app):
        super(MiAZAssistant, self).__init__()
        super().__init__(app)

        # Pages
        for title in [_('Welcome'), _('Repository'), _('Summary')]:
            vbox = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_margin_top(margin=12)
            vbox.set_margin_end(margin=12)
            vbox.set_margin_bottom(margin=12)
            vbox.set_margin_start(margin=12)
            self.append_page(vbox)
            self.set_page_title(vbox, title)

        # Page 0 - Welcome
        page = self.get_nth_page(0)
        lblWelcome = Gtk.Label.new(str=_('%s repository assistant') % (ENV['APP']['shortname']))
        lblWelcome.get_style_context().add_class(class_name='title-1')
        lblWelcome.set_margin_top(24)
        imgWelcome = Gtk.Image.new_from_icon_name('MiAZ-big')
        imgWelcome.set_pixel_size(128)
        box = self.factory.create_box_vertical(spacing=12)
        box.append(imgWelcome)
        box.append(lblWelcome)
        page.set_center_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.INTRO)
        self.set_page_complete(page, True)

        # Page 1 - Repository
        page = self.get_nth_page(1)
        box = self.factory.create_box_vertical(spacing=12)
        lblTitle = Gtk.Label()
        lblTitle.set_markup(_('Select a directory'))
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        listbox = Gtk.ListBox()
        btnRepoSource = self.factory.create_button('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        self.row_repo_source = self.factory.create_actionrow(title='Directory not set', suffix=btnRepoSource)
        listbox.append(self.row_repo_source)
        box.append(listbox)
        page.set_center_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, False)

        # ~ # Page 3 - Summary
        page = self.get_nth_page(2)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblTitle = Gtk.Label()
        lblTitle.set_markup(_('Summary'))
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        page.set_start_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.SUMMARY)
        self.connect('cancel', self.on_assistant_cancel)
        self.connect('close', self.on_assistant_close)
        self.log.debug('Repository Assistant ready')

    def validate_repo(self, *args):
        self.log.debug(args)

    def _update_action_row_repo_source(self, name, dirpath):
        self.row_repo_source.set_title(name)
        self.row_repo_source.set_subtitle(dirpath)
        self.repo_is_set = True

    def is_repo_set(self):
        return self.repo_is_set

    def show_filechooser_source(self, *args):
        filechooser = self.factory.create_filechooser(
                    parent=self,
                    title=_('Choose target directory'),
                    target = 'FOLDER',
                    callback = self.on_filechooser_response_source
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response, data=None):
        use_repo = False
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            box = content_area.get_first_child()
            filechooser = box.get_first_child()
            gfile = filechooser.get_file()
            if gfile is None:
                self.log.debug('No directory set. Do nothing.')
                # FIXME: Show warning message. Priority: low
                return
            self.repopath = gfile.get_path()
            page = self.get_nth_page(1)
            if self.repopath is not None:
                self.row_repo_source.set_title(os.path.basename(self.repopath))
                self.row_repo_source.set_subtitle(self.repopath)
                self.set_page_complete(page, True)
            else:
                self.row_repo_source.set_title(_('Directory not set'))
                self.row_repo_source.set_subtitle('')
                self.set_page_complete(page, False)

        dialog.destroy()

    def on_assistant_cancel(self, *args):
        if self.completed:
            self.log.debug('Configuration finished sucessfully')
            self.destroy()
            self.app.win.present()
        else:
            self.log.debug('Configuration incomplete. MiAZ app will exit now')
            self.app.quit()

    def on_assistant_close(self, *args):
        repository = self.app.get_service('repo')
        conf_app = self.app.get_config('App')
        dirpath = self.repopath
        if repo.validate(dirpath):
            self.log.debug("Directory '%s' is a MiAZ Repository", dirpath)
            if len(conf_app.get('source')) == 0:
                conf_app.set('source', dirpath)
            repo.load(dirpath)
        else:
            self.log.debug("Directory '%s' is not a MiAZ repository", dirpath)
            repo.init(dirpath)

        # ~ conf_app = self.app.get_config('App')
        # ~ conf_app.set('source', dirpath)
        self.destroy()
        self.app.check_repository()

class MiAZAssistantRepoSettings(MiAZAssistant):
    """"""
    __gtype_name__ = 'MiAZAssistantRepoSettings'
    current = None

    def __init__(self, app):
        super(MiAZAssistant, self).__init__()
        super().__init__(app)

        self.connect('cancel', self.on_assistant_cancel)
        # ~ self.connect('close', self.on_assistant_close)
        self.connect('apply', self.on_assistant_close)

        # Pages
        for title in [_('Welcome'), _('Countries'), _('Groups'), _('Purposes'), _('Sent by'), _('Sent to'), _('Summary')]:
            vbox = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_margin_top(margin=12)
            vbox.set_margin_end(margin=12)
            vbox.set_margin_bottom(margin=12)
            vbox.set_margin_start(margin=12)
            self.append_page(vbox)
            self.set_page_title(vbox, title)

        # Page Welcome
        page = self.get_nth_page(PAGE.WELCOME)
        lblWelcome = Gtk.Label.new(_('Repository settings assistant'))
        lblWelcome.get_style_context().add_class(class_name='title-1')
        lblWelcome.set_margin_top(24)
        imgWelcome = Gtk.Image.new_from_icon_name('MiAZ-big')
        imgWelcome.set_pixel_size(128)
        box = self.factory.create_box_vertical(spacing=12)
        box.append(imgWelcome)
        box.append(lblWelcome)
        page.set_center_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.INTRO)
        self.set_page_complete(page, True)

        # Page Countries
        page = self.get_nth_page(PAGE.COUNTRIES)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblDesc = Gtk.Label()
        lblDesc.set_markup('')
        lblDesc.set_xalign(0.0)
        box.append(lblDesc)
        selector = MiAZCountries(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        page.set_start_widget(box)
        lblInfo = Gtk.Label()
        lblInfo.set_markup(_('Manage countries'))
        page.set_end_widget(lblInfo)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)

        # Page Groups
        page = self.get_nth_page(PAGE.GROUPS)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblDesc = Gtk.Label()
        lblDesc.set_markup('')
        lblDesc.set_xalign(0.0)
        box.append(lblDesc)
        selector = MiAZGroups(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        page.set_start_widget(box)
        lblInfo = Gtk.Label()
        lblInfo.set_markup(_('Manage groups'))
        page.set_end_widget(lblInfo)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)

        # Page Purposes
        page = self.get_nth_page(PAGE.PURPOSES)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblDesc = Gtk.Label()
        lblDesc.set_markup('')
        lblDesc.set_xalign(0.0)
        box.append(lblDesc)
        selector = MiAZPurposes(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        page.set_start_widget(box)
        lblInfo = Gtk.Label()
        lblInfo.set_markup(_('Manage purposes'))
        page.set_end_widget(lblInfo)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)

        # Page People Sent To
        page = self.get_nth_page(PAGE.SENTTO)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblDesc = Gtk.Label()
        lblDesc.set_markup('')
        lblDesc.set_xalign(0.0)
        box.append(lblDesc)
        selector = MiAZPeopleSentTo(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        page.set_start_widget(box)
        lblInfo = Gtk.Label()
        lblInfo.set_markup(_('Manage people receiving documents'))
        page.set_end_widget(lblInfo)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)

        # Page People Sent By
        page = self.get_nth_page(PAGE.SENTBY)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblDesc = Gtk.Label()
        lblDesc.set_markup('')
        lblDesc.set_xalign(0.0)
        box.append(lblDesc)
        selector = MiAZPeopleSentBy(self.app)
        selector.set_vexpand(True)
        selector.update()
        box.append(selector)
        page.set_start_widget(box)
        lblInfo = Gtk.Label()
        lblInfo.set_markup(_('Manage people sending documents'))
        page.set_end_widget(lblInfo)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)

        # Page Confirm
        page = self.get_nth_page(PAGE.CONFIRMATION)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblTitle = Gtk.Label()
        lblTitle.set_markup(_('You are set!'))
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        page.set_start_widget(box)
        text = _('You can continue using the application now')
        label = self.factory.create_label(text=text)
        page.set_center_widget(label)
        self.set_page_type(page, Gtk.AssistantPageType.CONFIRM)
        self.set_page_complete(page, True)

    def on_assistant_cancel(self, *args):
        if self.completed:
            self.log.debug('Configuration finished sucessfully')
            self.destroy()
            self.app.win.present()
        else:
            self.log.debug('Settings assistant canceled by user')
            self.destroy()
            self.app.win.present()

    def on_assistant_close(self, *args):
        conf_country = self.app.get_config('Country')
        countries = conf_country.load(conf_country.used)
        if len(countries) > 0:
            self.destroy()
        else:
            self.previous_page()
