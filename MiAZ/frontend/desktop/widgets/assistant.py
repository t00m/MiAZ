#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from abc import abstractmethod

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository.GdkPixbuf import Pixbuf
from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger

# ~ from MiAZ.frontend.desktop.settings import MiAZSettings
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries

class MiAZAssistant(Gtk.Assistant):
    """ Start up Assistant"""

    def __init__(self, app):
        super(MiAZAssistant, self).__init__()
        self.log = get_logger('MiAZAssistant')
        self.app = app
        self.factory = self.app.get_factory()
        self.backend = self.app.get_backend()
        self.config = self.backend.get_conf()
        self.set_size_request(1024, 728)
        self.set_title("MiAZ Assistant")
        self.completed = False


class MiAZAssistantRepo(MiAZAssistant):
    """"""
    __gtype_name__ = 'MiAZAssistantRepo'
    current = None

    def __init__(self, app):
        super(MiAZAssistant, self).__init__()
        super().__init__(app)

        # Pages
        for title in ['Welcome', 'Repository', 'Summary']:
            vbox = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_margin_top(margin=12)
            vbox.set_margin_end(margin=12)
            vbox.set_margin_bottom(margin=12)
            vbox.set_margin_start(margin=12)
            self.append_page(vbox)
            self.set_page_title(vbox, title)

        # Page 0 - Welcome
        page = self.get_nth_page(0)
        lblWelcome = Gtk.Label.new(str='%s repository assistant' % (ENV['APP']['shortname']))
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
        lblTitle.set_markup('Select a directory')
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        listbox = Gtk.ListBox()
        btnRepoSource = self.factory.create_button('document-edit-symbolic', '', self.show_filechooser_source, css_classes=['flat'])
        self.row_repo_source = self.factory.create_actionrow(title='Directory not set', suffix=btnRepoSource)
        listbox.append(self.row_repo_source)
        box.append(listbox)
        page.set_start_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, False)

        # ~ # Page 3 - Summary
        page = self.get_nth_page(2)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblTitle = Gtk.Label()
        lblTitle.set_markup('Summary')
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        page.set_start_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.SUMMARY)
        self.connect('cancel', self.on_assistant_cancel)
        self.connect('close', self.on_assistant_close)
        self.log.debug("Repository Assistant ready")

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
                    title='Choose target directory',
                    target = 'FOLDER',
                    callback = self.on_filechooser_response_source
                    )
        filechooser.show()

    def on_filechooser_response_source(self, dialog, response):
        use_repo = False
        if response == Gtk.ResponseType.ACCEPT:
            content_area = dialog.get_content_area()
            filechooser = content_area.get_first_child()
            try:
                gfile = filechooser.get_file()
            except AttributeError as error:
                self.log.error(error)
                raise
            if gfile is None:
                self.log.debug("No directory set. Do nothing.")
                # FIXME: Show warning message. Priority: low
                return
            self.repopath = gfile.get_path()
            page = self.get_nth_page(1)
            if self.repopath is not None:
                self.row_repo_source.set_title(os.path.basename(self.repopath))
                self.row_repo_source.set_subtitle(self.repopath)
                self.set_page_complete(page, True)
            else:
                self.row_repo_source.set_title('Directory not set')
                self.row_repo_source.set_subtitle('')
                self.set_page_complete(page, False)

        dialog.destroy()

    def on_assistant_cancel(self, *args):
        if self.completed:
            self.log.debug("Configuration finished sucessfully")
            self.destroy()
            self.app.win.present()
        else:
            self.log.debug("Configuration incomplete. MiAZ app will exit now")
            self.app.quit()

    def on_assistant_close(self, *args):
        backend = self.app.get_backend()
        dirpath = self.repopath
        if backend.is_repo(dirpath):
            self.log.debug("Directory '%s' is a MiAZ Repository", dirpath)
            backend.load_repo(dirpath)
        else:
            self.log.debug("Directory '%s' is not a MiAZ repository", dirpath)
            backend.init_repo(dirpath)

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

        # Pages
        for title in ['Welcome', 'Country', 'Summary']:
            vbox = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_margin_top(margin=12)
            vbox.set_margin_end(margin=12)
            vbox.set_margin_bottom(margin=12)
            vbox.set_margin_start(margin=12)
            self.append_page(vbox)
            self.set_page_title(vbox, title)


        # Page 0 - Welcome
        page = self.get_nth_page(0)
        lblWelcome = Gtk.Label.new(str='%s repository settings assistant' % (ENV['APP']['shortname']))
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

        # Page 1 - Country settings
        page = self.get_nth_page(1)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblTitle = Gtk.Label()
        lblTitle.set_markup('Select countries')
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        lblDesc = Gtk.Label()
        lblDesc.set_markup('')
        lblDesc.set_xalign(0.0)
        box.append(lblDesc)
        self.vcountries = MiAZCountries(self.app)
        self.vcountries.set_vexpand(True)
        self.vcountries.update()
        box.append(self.vcountries)
        page.set_start_widget(box)
        self.lblInfo = Gtk.Label()
        self.lblInfo.set_markup("Choose one or more countries")
        self.ifb_country = Gtk.InfoBar()
        self.ifb_country.set_revealed(True)
        self.ifb_country.set_hexpand(True)
        self.ifb_country.set_message_type(Gtk.MessageType.WARNING)
        self.ifb_country.set_show_close_button(False)
        self.ifb_country.add_child(self.lblInfo)
        page.set_end_widget(self.ifb_country)
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(page, True)


        # ~ # Page 2 - Confirm
        page = self.get_nth_page(2)
        box = self.factory.create_box_vertical(spacing=12, vexpand=True, hexpand=True)
        lblTitle = Gtk.Label()
        lblTitle.set_markup('Summary')
        lblTitle.get_style_context().add_class(class_name='title-2')
        box.append(lblTitle)
        page.set_start_widget(box)
        self.set_page_type(page, Gtk.AssistantPageType.SUMMARY)
        self.connect('cancel', self.on_assistant_cancel)
        self.connect('close', self.on_assistant_close)

    def on_assistant_cancel(self, *args):
        if self.completed:
            self.log.debug("Configuration finished sucessfully")
            self.destroy()
            self.app.win.present()
        else:
            self.log.debug("Configuration incomplete. MiAZ app will exit now")
            self.app.quit()

    def on_assistant_close(self, *args):
        conf_country = self.app.get_config('Country')
        countries = conf_country.load(conf_country.config_local)
        if len(countries) > 0:
            rename = self.app.get_rename_widget()
            rename.update_dropdowns()
            self.destroy()
        else:
            self.previous_page()
