
"""
# File: dr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Disaster Recovery (Backup & Restore) preferences page
"""

import os

from gettext import gettext as _

from gi.repository import Adw
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
        repo_path = self.app.get_config('Repository').get_path(repo_item.id, used=True)
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

    def _start(self, title, work, restart=False):
        """Run one backup or restore behind the progress dialog.

        Everything here moves files underneath the running application, so it
        goes to a worker thread with the UI held back: see services/progress.py.
        A restore ends in a restart, but only once the user has closed the
        dialog and read what happened.
        """
        progress = self.app.get_service('progress')
        started = progress.run(
            work, title=title, parent=self.get_root(),
            on_close=self._on_restore_closed if restart else None)
        if not started:
            self.srvdlg.show_toast(_('Another operation is already running'))

    def _on_restore_closed(self, ok, _result):
        # The configuration the app is holding describes what was just
        # replaced, so it is dropped before the restart reads the new one.
        if not ok:
            return
        self.srvrepo.reset()
        self._restart_app()

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
        scope = self._get_selected_scope()
        repo_key = repo_item.id.replace(' ', '_')
        srvdr = self.srvdr

        if scope == 'files':
            title = _('Backing up documents')

            def work(report):
                total = srvdr.backup_files(repo_dir, dest_dir, progress=report)
                return _('{n} documents copied to {path}.').format(
                    n=total, path=dest_dir)
        elif scope == 'config':
            title = _('Backing up the configuration')

            def work(report):
                path = srvdr.backup_config(repo_conf, dest_dir, repo_key,
                                           progress=report)
                return _('Saved as {name} in {path}.').format(
                    name=os.path.basename(path), path=dest_dir)
        elif scope == 'repo':
            title = _('Backing up the repository')

            def work(report):
                path = srvdr.backup_repository(repo_dir, dest_dir, repo_key,
                                               progress=report)
                return _('Saved as {name} in {path}.').format(
                    name=os.path.basename(path), path=dest_dir)
        else:
            return
        self._start(title, work)

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

        src_dir = folder.get_path()
        srvdr = self.srvdr

        def work(report):
            total = srvdr.restore_files(repo_dir, src_dir, progress=report)
            return _('{n} documents restored from {path}. MiAZ restarts when '
                     'you close this.').format(n=total, path=src_dir)

        self._start(_('Restoring documents'), work, restart=True)

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

        zip_path = gfile.get_path()
        srvdr = self.srvdr

        def work(report):
            srvdr.restore_config(repo_conf, zip_path, progress=report)
            return _('The configuration was restored from {name}. MiAZ '
                     'restarts when you close this.').format(
                         name=os.path.basename(zip_path))

        self._start(_('Restoring the configuration'), work, restart=True)

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

        zip_path = gfile.get_path()
        srvdr = self.srvdr

        def work(report):
            srvdr.restore_repository(repo_dir, zip_path, progress=report)
            return _('The repository was restored from {name}. MiAZ restarts '
                     'when you close this.').format(
                         name=os.path.basename(zip_path))

        self._start(_('Restoring the repository'), work, restart=True)
