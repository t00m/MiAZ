#!/usr/bin/python3

"""
# File: dr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Disaster Recovery (Backup & Restore) preferences page
"""

import os

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Repository
from MiAZ.backend.config import MiAZConfigRepositories


class MiAZDRPage(Adw.PreferencesPage):
    __gtype_name__ = 'MiAZDRPage'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.DR')
        self.factory = self.app.get_service('factory')
        self.srvdlg = self.app.get_service('dialogs')
        self.actions = self.app.get_service('actions')
        self.srvrepo = self.app.get_service('repo')
        self.srvdr = self.app.get_service('dr')
        self._build_ui()

    def _build_ui(self):
        self.set_title(_('Backup & Restore'))
        self.set_icon_name('io.github.t00m.MiAZ-backup-restore-symbolic')
        self._build_group_repository()
        self._build_group_operation()
        self._build_group_scope()
        self._build_group_action()

    def _build_group_repository(self):
        group = Adw.PreferencesGroup()
        group.set_title(_('Repository'))
        self.add(group)

        row = Adw.ActionRow(title=_('Target repository'))
        group.add(row)

        dd_repo = self.factory.create_dropdown_generic(
            item_type=Repository, ellipsize=False, enable_search=True
        )
        dd_repo.set_valign(Gtk.Align.CENTER)
        dd_repo.set_hexpand(False)
        self.actions.dropdown_populate(
            MiAZConfigRepositories, dd_repo, Repository,
            any_value=False, none_value=False
        )
        row.add_suffix(dd_repo)
        self._dd_repo = dd_repo

    def _build_group_operation(self):
        group = Adw.PreferencesGroup()
        group.set_title(_('Operation type'))
        self.add(group)

        self._radio_backup = Gtk.CheckButton()
        self._radio_backup.set_active(True)
        self._radio_backup.connect('toggled', self._on_operation_toggled)
        row_bu = Adw.ActionRow(title=_('Backup'))
        row_bu.add_prefix(self._radio_backup)
        group.add(row_bu)

        self._radio_restore = Gtk.CheckButton(group=self._radio_backup)
        self._radio_restore.connect('toggled', self._on_operation_toggled)
        row_re = Adw.ActionRow(title=_('Restore'))
        row_re.add_prefix(self._radio_restore)
        group.add(row_re)

    def _on_operation_toggled(self, button):
        if not hasattr(self, '_row_files'):
            return
        is_backup = self._radio_backup.get_active()
        if is_backup:
            labels = [
                _('Backup files'),
                _('Backup configuration'),
                _('Backup repository'),
            ]
        else:
            labels = [
                _('Restore files'),
                _('Restore configuration'),
                _('Restore repository'),
            ]
        self._row_files.set_title(labels[0])
        self._row_config.set_title(labels[1])
        self._row_repo.set_title(labels[2])

    def _build_group_scope(self):
        group = Adw.PreferencesGroup()
        group.set_title(_('What to process'))
        self.add(group)

        self._scope_files = Gtk.CheckButton()
        self._scope_files.set_active(True)
        self._row_files = Adw.ActionRow(title=_('Backup files'))
        self._row_files.add_prefix(self._scope_files)
        group.add(self._row_files)

        self._scope_config = Gtk.CheckButton(group=self._scope_files)
        self._row_config = Adw.ActionRow(title=_('Backup configuration'))
        self._row_config.add_prefix(self._scope_config)
        group.add(self._row_config)

        self._scope_repo = Gtk.CheckButton(group=self._scope_files)
        self._row_repo = Adw.ActionRow(title=_('Backup repository'))
        self._row_repo.add_prefix(self._scope_repo)
        group.add(self._row_repo)

    def _build_group_action(self):
        group = Adw.PreferencesGroup()
        self.add(group)

        btn = self.factory.create_button(
            icon_name='io.github.t00m.MiAZ-study-symbolic',
            title=_('Proceed'),
            callback=self._on_proceed,
        )
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_valign(Gtk.Align.CENTER)
        btn.add_css_class('suggested-action')
        row = Adw.ActionRow()
        row.add_suffix(btn)
        group.add(row)

    def _get_selected_repo(self):
        item = self._dd_repo.get_selected_item()
        if item is None or item.id in ('Any', 'None'):
            self.srvdlg.show_toast(_('Select a repository first'))
            return None
        return item

    def _get_repo_dirs(self, repo_item):
        repos_used = self.app.get_config('Repository').load_used()
        repo_path = repos_used.get(repo_item.id)
        if not repo_path:
            self.srvdlg.show_toast(_('Repository path not found'))
            return None, None
        return repo_path, os.path.join(repo_path, '.conf')

    def _get_selected_scope(self):
        if self._scope_files.get_active():
            return 'files'
        if self._scope_config.get_active():
            return 'config'
        if self._scope_repo.get_active():
            return 'repo'
        return None

    def _restart_app(self):
        self.actions.application_restart()

    def _on_proceed(self, button, data=None):
        repo_item = self._get_selected_repo()
        if repo_item is None:
            return

        parent = self.get_root()
        if self._radio_backup.get_active():
            dialog = Gtk.FileDialog.new()
            dialog.set_title(_('Select backup destination folder'))
            dialog.select_folder(parent, None, self._on_backup_dest_selected)
        else:
            scope = self._get_selected_scope()
            if scope == 'files':
                dialog = Gtk.FileDialog.new()
                dialog.set_title(_('Select folder with files to restore'))
                dialog.select_folder(parent, None, self._on_restore_files_source_selected)
            elif scope == 'config':
                self._warn_then_restore_config()
            elif scope == 'repo':
                self._warn_then_restore_repo()

    def _on_backup_dest_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark':
                self.log.error(f"Backup folder selection failed: {e.message}")
            return

        repo_item = self._get_selected_repo()
        if repo_item is None:
            return
        repo_dir, repo_conf = self._get_repo_dirs(repo_item)
        if repo_dir is None:
            return
        dest_dir = folder.get_path()

        try:
            scope = self._get_selected_scope()
            repo_key = repo_item.id.replace(' ', '_')
            if scope == 'files':
                n = self.srvdr.backup_files(repo_dir, dest_dir)
                self.srvdlg.show_toast(_('Backup completed: {n} files').format(n=n))
            elif scope == 'config':
                path = self.srvdr.backup_config(repo_conf, dest_dir, repo_key)
                self.srvdlg.show_toast(_('Backup completed: {name}').format(name=os.path.basename(path)))
            elif scope == 'repo':
                path = self.srvdr.backup_repository(repo_dir, dest_dir, repo_key)
                self.srvdlg.show_toast(_('Backup completed: {name}').format(name=os.path.basename(path)))
        except Exception as e:
            self.log.error(f"Backup failed: {e}")
            self.srvdlg.show_toast(_('Backup failed: ') + str(e))

    def _on_restore_files_source_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark':
                self.log.error(f"Restore files selection failed: {e.message}")
            return

        repo_item = self._get_selected_repo()
        if repo_item is None:
            return
        repo_dir, _unused = self._get_repo_dirs(repo_item)
        if repo_dir is None:
            return

        try:
            n = self.srvdr.restore_files(repo_dir, folder.get_path())
            self.srvdlg.show_toast(_('Restored {n} files').format(n=n))
            self._restart_app()
        except Exception as e:
            self.log.error(f"Restore files failed: {e}")
            self.srvdlg.show_toast(_('Restore files failed: ') + str(e))

    def _warn_then_restore_config(self):
        title = _('Destructive operation')
        body = _('Restoring a configuration will replace all current settings for this repository. This action cannot be undone. Proceed?')
        parent = self.get_root()
        dialog = self.srvdlg.show_question(title=title, body=body)
        dialog.connect('response', self._on_config_restore_warning_response)
        dialog.present(parent)

    def _on_config_restore_warning_response(self, dialog, response):
        if response != 'apply':
            return
        parent = self.get_root()
        file_dialog = Gtk.FileDialog.new()
        file_dialog.set_title(_('Select configuration backup file'))
        filter_zip = Gtk.FileFilter()
        filter_zip.set_name(_('Zip archives'))
        filter_zip.add_pattern('*.zip')
        file_dialog.set_default_filter(filter_zip)
        file_dialog.open(parent, None, self._on_config_zip_selected)

    def _on_config_zip_selected(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark':
                self.log.error(f"Config zip selection failed: {e.message}")
            return

        repo_item = self._get_selected_repo()
        if repo_item is None:
            return
        _unused, repo_conf = self._get_repo_dirs(repo_item)
        if repo_conf is None:
            return

        try:
            self.srvdr.restore_config(repo_conf, gfile.get_path())
            self.srvrepo.reset()
            self.srvdlg.show_toast(_('Configuration restored successfully'))
            self._restart_app()
        except Exception as e:
            self.log.error(f"Restore config failed: {e}")
            self.srvdlg.show_toast(_('Restore configuration failed: ') + str(e))

    def _warn_then_restore_repo(self):
        title = _('Destructive operation')
        body = _('Restoring a repository will replace all documents and settings for this repository. This action cannot be undone. Proceed?')
        parent = self.get_root()
        dialog = self.srvdlg.show_question(title=title, body=body)
        dialog.connect('response', self._on_repo_restore_warning_response)
        dialog.present(parent)

    def _on_repo_restore_warning_response(self, dialog, response):
        if response != 'apply':
            return
        parent = self.get_root()
        file_dialog = Gtk.FileDialog.new()
        file_dialog.set_title(_('Select repository backup file'))
        filter_zip = Gtk.FileFilter()
        filter_zip.set_name(_('Zip archives'))
        filter_zip.add_pattern('*.zip')
        file_dialog.set_default_filter(filter_zip)
        file_dialog.open(parent, None, self._on_repo_zip_selected)

    def _on_repo_zip_selected(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error as e:
            if e.domain != 'gtk-dialog-error-quark':
                self.log.error(f"Repo zip selection failed: {e.message}")
            return

        repo_item = self._get_selected_repo()
        if repo_item is None:
            return
        repo_dir, _unused = self._get_repo_dirs(repo_item)
        if repo_dir is None:
            return

        try:
            self.srvdr.restore_repository(repo_dir, gfile.get_path())
            self.srvrepo.reset()
            self.srvdlg.show_toast(_('Repository restored successfully'))
            self._restart_app()
        except Exception as e:
            self.log.error(f"Restore repo failed: {e}")
            self.srvdlg.show_toast(_('Restore repository failed: ') + str(e))
