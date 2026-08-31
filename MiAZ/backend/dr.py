
"""
# File: dr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Disaster Recovery (Backup & Restore) backend module
"""

import os
import shutil
import tempfile

from gettext import gettext as _

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


def _report(progress, message: str, fraction: float = None):
    """Send one progress update, when the caller asked for them.

    The callback belongs to whoever started the operation and is called from
    wherever this code runs, a worker thread included. This module knows
    nothing about the UI: marshalling to the main loop is the caller's job.
    A fraction of None means "no idea how long this takes", which is the honest
    answer for the zip and unzip steps: shutil and zipfile report nothing while
    they work.
    """
    if progress is not None:
        progress(message, fraction)


class MiAZDR(GObject.GObject):
    """Disaster Recovery backend service."""
    __gtype_name__ = 'MiAZDR'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.DR')
        self.util = app.get_service('util')

    def backup_files(self, repo_dir: str, dest_dir: str, progress=None) -> int:
        """Copy all non-hidden files from repo into dest_dir.

        Returns the number of files copied.
        """
        names = self._plain_files(repo_dir)
        total = len(names)
        for count, name in enumerate(names, start=1):
            shutil.copy2(os.path.join(repo_dir, name),
                         os.path.join(dest_dir, name))
            _report(progress, _('Copying {name}').format(name=name), count / total)
        self.log.info(f"Backup files: {total} files copied to {dest_dir}")
        return total

    @staticmethod
    def _plain_files(directory: str) -> list:
        """The names a backup covers: files, no hidden entries, no directories.

        Listed up front rather than walked lazily, because the count is what
        makes the progress bar honest instead of a spinner with numbers.
        """
        return sorted(name for name in os.listdir(directory)
                      if os.path.isfile(os.path.join(directory, name))
                      and not name.startswith('.'))

    def backup_config(self, repo_conf_dir: str, dest_dir: str, repo_key: str = '',
                      progress=None) -> str:
        """Zip the .conf directory and save to dest_dir.

        Returns the path to the created zip archive.
        """
        ts = self.util.timestamp()
        key = f"-{repo_key}" if repo_key else ''
        zip_name = os.path.join(dest_dir, f"miaz-config{key}-{ts}")
        _report(progress, _('Compressing the configuration…'))
        result = self.util.zip(zip_name, repo_conf_dir)
        self.log.info(f"Backup config: saved to {result}")
        return result

    def backup_repository(self, repo_dir: str, dest_dir: str, repo_key: str = '',
                          progress=None) -> str:
        """Zip the entire repository (files + .conf) to dest_dir.

        Returns the path to the created zip archive.
        """
        ts = self.util.timestamp()
        key = f"-{repo_key}" if repo_key else ''
        zip_name = os.path.join(dest_dir, f"miaz-repo{key}-{ts}")
        _report(progress, _('Compressing the repository…'))
        result = self.util.zip(zip_name, repo_dir)
        self.log.info(f"Backup repository: saved to {result}")
        return result

    def restore_files(self, repo_dir: str, src_dir: str, progress=None) -> int:
        """Copy all non-hidden files from src_dir into repo_dir.

        Returns the number of files restored.
        """
        names = self._plain_files(src_dir)
        total = len(names)
        for count, name in enumerate(names, start=1):
            shutil.copy2(os.path.join(src_dir, name),
                         os.path.join(repo_dir, name))
            _report(progress, _('Restoring {name}').format(name=name), count / total)
        self.log.info(f"Restore files: {total} files copied to {repo_dir}")
        return total

    def restore_config(self, repo_conf_dir: str, zip_path: str, progress=None):
        """Replace the .conf directory with contents from a zip archive."""
        # Defined before the try so the rollback below can reference it even if
        # unzip fails before we get to move anything.
        old_conf = repo_conf_dir + '.old'
        tmpdir = tempfile.mkdtemp()
        try:
            _report(progress, _('Extracting the archive…'))
            self.util.unzip(zip_path, tmpdir)

            if os.path.exists(old_conf):
                shutil.rmtree(old_conf)

            if os.path.exists(repo_conf_dir):
                shutil.move(repo_conf_dir, old_conf)

            _report(progress, _('Replacing the configuration…'))
            os.makedirs(repo_conf_dir, exist_ok=True)
            for item in os.listdir(tmpdir):
                src = os.path.join(tmpdir, item)
                dst = os.path.join(repo_conf_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)

            if os.path.exists(old_conf):
                _report(progress, _('Cleaning up…'))
                shutil.rmtree(old_conf)

            self.log.info(f"Restore config: replaced {repo_conf_dir} from {zip_path}")
        except Exception as error:
            self.log.error(f"Restore config failed, rolling back: {error}")
            # A failure during rollback must not mask the original error, so it
            # is logged and swallowed while the original exception re-raises.
            try:
                if os.path.exists(old_conf):
                    if os.path.exists(repo_conf_dir):
                        shutil.rmtree(repo_conf_dir)
                    shutil.move(old_conf, repo_conf_dir)
            except OSError as rollback_error:
                self.log.error(f"Rollback of {repo_conf_dir} failed: {rollback_error}")
            raise
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def restore_repository(self, repo_dir: str, zip_path: str, progress=None):
        """Replace the entire repository with contents from a zip archive."""
        # Defined before the try so the rollback below can reference it even if
        # unzip fails before we get to move anything.
        old_repo = repo_dir + '.old'
        tmpdir = tempfile.mkdtemp()
        try:
            _report(progress, _('Extracting the archive…'))
            self.util.unzip(zip_path, tmpdir)

            if os.path.exists(old_repo):
                shutil.rmtree(old_repo)

            if os.path.exists(repo_dir):
                shutil.move(repo_dir, old_repo)

            _report(progress, _('Replacing the repository…'))
            os.makedirs(repo_dir, exist_ok=True)
            for item in os.listdir(tmpdir):
                src = os.path.join(tmpdir, item)
                dst = os.path.join(repo_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)

            if os.path.exists(old_repo):
                _report(progress, _('Cleaning up…'))
                shutil.rmtree(old_repo)

            self.log.info(f"Restore repository: replaced {repo_dir} from {zip_path}")
        except Exception as error:
            self.log.error(f"Restore repository failed, rolling back: {error}")
            # A failure during rollback must not mask the original error, so it
            # is logged and swallowed while the original exception re-raises.
            try:
                if os.path.exists(old_repo):
                    if os.path.exists(repo_dir):
                        shutil.rmtree(repo_dir)
                    shutil.move(old_repo, repo_dir)
            except OSError as rollback_error:
                self.log.error(f"Rollback of {repo_dir} failed: {rollback_error}")
            raise
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
