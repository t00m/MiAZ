#!/usr/bin/python3
# File: assistant.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: First-run assistant to create and configure a repository

import os
from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Country, Group, Purpose, SentBy, SentTo
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo


# Property pages, built only after the repository exists (their config objects
# are created by MiAZRepository.load). The order mirrors the filename fields the
# user is about to configure: country, group, purpose, sender, recipient.
PROPERTY_PAGES = [
    ('Country', MiAZCountries, Country),
    ('Group', MiAZGroups, Group),
    ('Purpose', MiAZPurposes, Purpose),
    ('SentBy', MiAZPeopleSentBy, SentBy),
    ('SentTo', MiAZPeopleSentTo, SentTo),
]

# Short, plain instructions shown above each property selector.
PROPERTY_HELP = {
    'Country': _('Enable the countries you exchange documents with. '
                 'Move them from the left list to the right one.'),
    'Group': _('Groups classify documents by area, for example banking, '
               'health or work. Enable the ones you need; you can add your own.'),
    'Purpose': _('The purpose says what a document is for, for example invoice, '
                 'contract or report. Enable the ones you use; you can add more.'),
    'SentBy': _('Senders are the people or organisations that send you '
                'documents. Enable the ones you have; you can add your own.'),
    'SentTo': _('Recipients are the people or organisations you send documents '
                'to. Enable the ones you have; you can add your own.'),
}


class MiAZRepoAssistant(Adw.Window):
    """Guided first-run setup: explain MiAZ, create a repository and enable the
    properties (countries, groups, purposes, senders, recipients) needed to file
    documents. Pages can be revisited with Back to amend any choice."""
    __gtype_name__ = 'MiAZRepoAssistant'

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.log = MiAZLog('MiAZ.RepoAssistant')
        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')
        self.util = self.app.get_service('util')

        self._order = []        # ordered page names currently in the stack
        self._titles = {}       # page name -> heading shown in the header bar
        self._index = 0
        self._repo_created = False
        self._finishing = False
        self._location = GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_DOCUMENTS) or GLib.get_home_dir()

        ENV = self.app.get_env()
        self.set_title(_('Set up {shortname}').format(shortname=ENV['APP']['shortname']))
        self.set_default_size(960, 720)
        self.set_modal(True)
        self.app.add_widget('window-repo-assistant', self)
        self.connect('close-request', self._on_close_request)

        self._build_ui()
        self._show_index(0)

    # UI scaffolding -------------------------------------------------------

    def _build_ui(self):
        self.title = Adw.WindowTitle()
        headerbar = Adw.HeaderBar()
        headerbar.set_title_widget(self.title)

        self.progress = Gtk.ProgressBar()
        self.progress.add_css_class('osd')

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(headerbar)
        toolbar_view.add_top_bar(self.progress)
        toolbar_view.set_content(self.stack)
        toolbar_view.add_bottom_bar(self._build_action_bar())

        toast_overlay = Adw.ToastOverlay()
        toast_overlay.set_child(toolbar_view)
        self.set_content(toast_overlay)

        # The two pages that exist before a repository is created.
        self._add_page('welcome', self._build_page_welcome(), _('Welcome'))
        self._add_page('create', self._build_page_create(), _('Create a repository'))

    def _build_action_bar(self):
        bar = self.factory.create_box_horizontal(margin=12, spacing=6, hexpand=True)
        self.btn_back = Gtk.Button(label=_('Back'))
        self.btn_back.connect('clicked', self._on_back)
        self.btn_next = Gtk.Button(label=_('Next'))
        self.btn_next.add_css_class('suggested-action')
        self.btn_next.connect('clicked', self._on_next)

        spacer = Gtk.Box(hexpand=True)
        bar.append(self.btn_back)
        bar.append(spacer)
        bar.append(self.btn_next)
        return bar

    def _add_page(self, name, widget, title):
        self.stack.add_named(widget, name)
        self._order.append(name)
        self._titles[name] = title

    # Pages ----------------------------------------------------------------

    def _build_page_welcome(self):
        ENV = self.app.get_env()

        # App icon on the left, all text left-aligned on the right.
        row = self.factory.create_box_horizontal(margin=24, spacing=24,
                                                 hexpand=True, vexpand=True)
        row.set_halign(Gtk.Align.CENTER)
        row.set_valign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name('io.github.t00m.MiAZ')
        icon.set_pixel_size(128)
        icon.set_valign(Gtk.Align.START)
        row.append(icon)

        body = self.factory.create_box_vertical(margin=0, spacing=12)
        body.set_halign(Gtk.Align.START)
        body.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label()
        title.set_xalign(0.0)
        title.set_markup(_('<big><b>Welcome to {name}</b></big>').format(
            name=ENV['APP']['name']))
        body.append(title)

        intro = Gtk.Label()
        intro.set_xalign(0.0)
        intro.set_wrap(True)
        intro.set_justify(Gtk.Justification.LEFT)
        intro.set_max_width_chars(64)
        intro.set_markup(_(
            'MiAZ organises your personal documents by renaming them with a '
            'consistent, meaningful name. There is no database: the directory '
            'itself is the database, and everything is derived from the '
            'filenames.'))
        body.append(intro)

        # The seven-field pattern and the example are kept on their own
        # non-wrapping lines so the whole convention reads on a single line.
        # The window is wide enough to fit them; the explanatory sentences
        # around them still wrap normally.
        convention_intro = Gtk.Label()
        convention_intro.set_xalign(0.0)
        convention_intro.set_wrap(True)
        convention_intro.set_justify(Gtk.Justification.LEFT)
        convention_intro.set_max_width_chars(64)
        convention_intro.set_text(_('Each document is named with seven fields:'))
        body.append(convention_intro)

        pattern = Gtk.Label()
        pattern.set_xalign(0.0)
        pattern.set_wrap(False)
        pattern.set_selectable(True)
        pattern.set_markup(
            '<tt>{date}-{country}-{group}-{sender}-{purpose}-{concept}-{recipient}</tt>')
        body.append(pattern)

        example_intro = Gtk.Label()
        example_intro.set_xalign(0.0)
        example_intro.set_wrap(True)
        example_intro.set_justify(Gtk.Justification.LEFT)
        example_intro.set_max_width_chars(64)
        example_intro.set_text(_('For example:'))
        body.append(example_intro)

        example = Gtk.Label()
        example.set_xalign(0.0)
        example.set_wrap(False)
        example.set_selectable(True)
        example.set_markup(
            '<tt>20240315-ES-HOU-BANKNAME-INV-Q1invoice-JOHNDOE.pdf</tt>')
        body.append(example)

        steps = Gtk.Label()
        steps.set_xalign(0.0)
        steps.set_wrap(True)
        steps.set_justify(Gtk.Justification.LEFT)
        steps.set_max_width_chars(64)
        steps.set_markup(_(
            'This assistant will help you create your first repository and '
            'enable the values you want for each field. You can go back at any '
            'time to change your choices.'))
        steps.add_css_class('dim-label')
        body.append(steps)

        row.append(body)
        return row

    def _build_page_create(self):
        page = self.factory.create_box_vertical(margin=24, spacing=18,
                                                hexpand=True, vexpand=True)
        heading = Gtk.Label()
        heading.set_xalign(0.0)
        heading.set_markup(_('<big><b>Create a repository</b></big>'))
        page.append(heading)

        subtitle = Gtk.Label()
        subtitle.set_xalign(0.0)
        subtitle.set_wrap(True)
        subtitle.add_css_class('dim-label')
        subtitle.set_markup(_(
            'A repository is the folder where your documents live. Give it a '
            'name and choose the folder that will hold the files. The name can '
            'be anything you like; MiAZ derives the repository key from it.'))
        page.append(subtitle)

        group = Adw.PreferencesGroup()
        group.set_hexpand(True)

        # Free text: this is the human-readable name, stored as the repository
        # description. The repository key is derived from it with util.valid_key
        # at creation time. The row subtitle previews that key as the user types.
        self.row_name = Adw.EntryRow(title=_('Repository name'))
        self.row_name.connect('changed', self._on_name_changed)
        group.add(self.row_name)

        self.row_folder = Adw.ActionRow(title=_('Location'))
        self.row_folder.set_subtitle(self._location)
        btn_folder = Gtk.Button(icon_name='folder-symbolic')
        btn_folder.set_valign(Gtk.Align.CENTER)
        btn_folder.add_css_class('flat')
        btn_folder.connect('clicked', self._on_choose_folder)
        self.row_folder.add_suffix(btn_folder)
        self.row_folder.set_activatable_widget(btn_folder)
        self.btn_folder = btn_folder
        group.add(self.row_folder)

        page.append(group)

        # Live preview of the key derived from the name (empty until typed).
        self.lbl_key = Gtk.Label()
        self.lbl_key.set_xalign(0.0)
        self.lbl_key.set_wrap(True)
        self.lbl_key.add_css_class('dim-label')
        page.append(self.lbl_key)

        # Shown once the repository has been created. Creation is a one-off, so
        # the inputs above are locked afterwards: going back lets the user
        # review the choice without accidentally moving the files.
        self.lbl_created = Gtk.Label()
        self.lbl_created.set_xalign(0.0)
        self.lbl_created.set_wrap(True)
        self.lbl_created.add_css_class('success')
        self.lbl_created.set_visible(False)
        page.append(self.lbl_created)
        return page

    def _make_property_page(self, name, model, view):
        page = self.factory.create_box_vertical(margin=24, spacing=12,
                                                hexpand=True, vexpand=True)
        heading = Gtk.Label()
        heading.set_xalign(0.0)
        heading.set_markup(
            _('<big><b>{title}</b></big>').format(title=_(model.__title_plural__)))
        page.append(heading)

        help_text = PROPERTY_HELP.get(name, '')
        if help_text:
            lbl = Gtk.Label()
            lbl.set_xalign(0.0)
            lbl.set_wrap(True)
            lbl.add_css_class('dim-label')
            lbl.set_text(help_text)
            page.append(lbl)

        view.set_vexpand(True)
        view.set_hexpand(True)
        view.update_views()
        page.append(view)
        return page

    def _build_page_summary(self):
        page = self.factory.create_box_vertical(margin=24, spacing=12,
                                                hexpand=True, vexpand=True)
        heading = Gtk.Label()
        heading.set_xalign(0.0)
        heading.set_markup(_('<big><b>Summary</b></big>'))
        page.append(heading)

        subtitle = Gtk.Label()
        subtitle.set_xalign(0.0)
        subtitle.set_wrap(True)
        subtitle.add_css_class('dim-label')
        subtitle.set_markup(_(
            'Review your setup. Use Back to change anything, or finish to open '
            'your repository.'))
        page.append(subtitle)

        # Filled (and refilled) by _refresh_summary every time the page shows,
        # so it always reflects the latest selections.
        self._summary_group = Adw.PreferencesGroup()
        self._summary_group.set_hexpand(True)
        page.append(self._summary_group)
        return page

    # Navigation -----------------------------------------------------------

    def _show_index(self, index):
        index = max(0, min(index, len(self._order) - 1))
        self._index = index
        name = self._order[index]
        if name == 'summary':
            self._refresh_summary()
        self.stack.set_visible_child_name(name)
        self._update_nav()

    def _update_nav(self):
        i = self._index
        total = len(self._order)
        name = self._order[i]
        last = (i == total - 1)

        self.btn_back.set_sensitive(i > 0 and not self._finishing)
        self.btn_next.set_label(_('Finish') if last else _('Next'))

        if name == 'create' and not self._repo_created:
            valid = len(self._clean_name()) >= 2
            self.btn_next.set_sensitive(valid)
        else:
            self.btn_next.set_sensitive(True)

        self.title.set_title(self._titles[name])
        self.title.set_subtitle(_('Step {x} of {y}').format(x=i + 1, y=total))
        self.progress.set_fraction((i + 1) / total)

    def _on_back(self, *args):
        if self._index > 0:
            self._show_index(self._index - 1)

    def _on_next(self, *args):
        name = self._order[self._index]
        if name == 'create' and not self._repo_created:
            if not self._create_repository():
                return
            self._build_remaining_pages()
            self._update_nav()
        if self._index >= len(self._order) - 1:
            self._finish()
            return
        self._show_index(self._index + 1)

    # Repository creation --------------------------------------------------

    def _clean_name(self):
        # The repository key derived from the (free text) name.
        return self.util.valid_key(self.row_name.get_text())

    def _on_name_changed(self, entry):
        # The name is kept verbatim (it becomes the description). Only the key
        # preview is updated; it is computed from the name with util.valid_key.
        key = self._clean_name()
        if key:
            self.lbl_key.set_markup(
                _('Repository key: <tt>{key}</tt>').format(key=key))
        else:
            self.lbl_key.set_text('')
        self._update_nav()

    def _on_choose_folder(self, button):
        self.factory.create_filechooser_for_directories(
            callback=self._on_folder_selected,
            dirpath=self._location,
            parent=self)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            self._location = folder.get_path()
            self.row_folder.set_subtitle(self._location)
            self._update_nav()
        except GLib.Error as error:
            self.log.debug(f"Folder selection cancelled or failed: {error.message}")

    def _create_repository(self):
        # The typed name becomes the description; the key is derived from it.
        description = self.row_name.get_text().strip()
        key = self.util.valid_key(description)
        path = self._location

        if len(key) < 2:
            self.srvdlg.show_toast(_('Please enter a valid repository name'))
            return False
        if not path or not os.path.isdir(path):
            self.srvdlg.show_toast(_('Please choose an existing folder'))
            return False

        config = self.app.get_config_dict()
        repos = config['Repository']
        if repos.exists_used(key) or repos.exists_available(key):
            self.srvdlg.show_toast(
                _('A repository with key "{key}" already exists').format(key=key))
            return False

        try:
            repos.set_repo_available(key, path, description)
            repos.set_repo_used(key, path, description)
            config['App'].set('current', key)

            repository = self.app.get_service('repo')
            repository.reset()
            docs = repository.docs  # triggers setup() + init() (.conf, defaults)
            if not repository.validate(docs):
                raise RuntimeError(_('repository validation failed'))
            repository.load(docs)
        except Exception as error:
            self.log.error(f"Repository creation failed: {error}")
            self.srvdlg.show_toast(_('Could not create the repository'))
            return False

        self._repo_created = True
        self.row_name.set_sensitive(False)
        self.row_folder.set_sensitive(False)
        self.btn_folder.set_sensitive(False)
        self.lbl_created.set_markup(
            _('Repository created at <tt>{path}</tt>').format(path=path))
        self.lbl_created.set_visible(True)
        self.log.info(f"Repository '{key}' ('{description}') created at '{path}'")
        return True

    def _build_remaining_pages(self):
        """Build the property selectors and the summary once the repository (and
        therefore its per-property config objects) exists."""
        for name, viewcls, model in PROPERTY_PAGES:
            view = viewcls(self.app)
            page = self._make_property_page(name, model, view)
            self._add_page(name, page, _(model.__title_plural__))
        self._add_page('summary', self._build_page_summary(), _('Summary'))

    def _refresh_summary(self):
        # Adw.PreferencesGroup has no clear(), so track and remove the rows we
        # added on the previous visit before rebuilding from current state.
        for row in getattr(self, '_summary_rows', []):
            self._summary_group.remove(row)
        self._summary_rows = []

        config = self.app.get_config_dict()
        repo_id = config['App'].get('current')
        repos = config['Repository']
        repo_path = repos.get_path(repo_id, used=True)
        repo_desc = repos.get_description(repo_id, used=True) or repo_id

        # Title shows the human name (description); subtitle shows the derived
        # key and the location.
        row_repo = Adw.ActionRow(title=repo_desc)
        row_repo.set_subtitle(
            _('Key: {key} · {path}').format(key=repo_id, path=repo_path))
        self._summary_group.add(row_repo)
        self._summary_rows.append(row_repo)

        for name, _viewcls, model in PROPERTY_PAGES:
            cfg = self.app.get_config(name)
            count = len(cfg.load_used()) if cfg is not None else 0
            row = Adw.ActionRow(title=_(model.__title_plural__))
            row.set_subtitle(_('{n} enabled').format(n=count))
            self._summary_group.add(row)
            self._summary_rows.append(row)

    # Finish / cancel ------------------------------------------------------

    def _finish(self):
        if self._finishing:
            return
        self._finishing = True
        self.app.add_widget('window-repo-assistant', None)
        self.close()
        # Load the freshly configured repository into the workspace.
        GLib.idle_add(self._switch_once)

    def _on_close_request(self, *args):
        # Clear the registered reference so the assistant can be opened again.
        self.app.add_widget('window-repo-assistant', None)
        # If the user created a repository but closed before finishing, still
        # bring the workspace up for it instead of leaving the welcome page.
        if self._repo_created and not self._finishing:
            GLib.idle_add(self._switch_once)
        return False

    def _switch_once(self):
        # switch_start returns repo_loaded (True on success). Returning that
        # from an idle callback would reschedule it forever (GLib repeats while
        # the callback returns True), reloading the repo in a tight loop. Always
        # return GLib.SOURCE_REMOVE so it runs exactly once.
        self.app.get_service('workflow').switch_start()
        return GLib.SOURCE_REMOVE
