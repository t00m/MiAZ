#!/usr/bin/python3

"""
# File: dr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Disaster Recovery (Backup & Restore) backend module
"""

import os
import shutil
import tempfile

from gi.repository import GObject

from MiAZ.backend.log import MiAZLog


class MiAZDR(GObject.GObject):
    """Disaster Recovery backend service."""
    __gtype_name__ = 'MiAZDR'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.DR')
        self.util = app.get_service('util')

    def backup_files(self, repo_dir: str, dest_dir: str) -> int:
        """Copy all non-hidden files from repo into dest_dir.

        Returns the number of files copied.
        """
        count = 0
        for name in os.listdir(repo_dir):
            src = os.path.join(repo_dir, name)
            dst = os.path.join(dest_dir, name)
            if os.path.isfile(src) and not name.startswith('.'):
                shutil.copy2(src, dst)
                count += 1
        self.log.info(f"Backup files: {count} files copied to {dest_dir}")
        return count

    def backup_config(self, repo_conf_dir: str, dest_dir: str, repo_key: str = '') -> str:
        """Zip the .conf directory and save to dest_dir.

        Returns the path to the created zip archive.
        """
        ts = self.util.timestamp()
        key = f"-{repo_key}" if repo_key else ''
        zip_name = os.path.join(dest_dir, f"miaz-config{key}-{ts}")
        result = self.util.zip(zip_name, repo_conf_dir)
        self.log.info(f"Backup config: saved to {result}")
        return result

    def backup_repository(self, repo_dir: str, dest_dir: str, repo_key: str = '') -> str:
        """Zip the entire repository (files + .conf) to dest_dir.

        Returns the path to the created zip archive.
        """
        ts = self.util.timestamp()
        key = f"-{repo_key}" if repo_key else ''
        zip_name = os.path.join(dest_dir, f"miaz-repo{key}-{ts}")
        result = self.util.zip(zip_name, repo_dir)
        self.log.info(f"Backup repository: saved to {result}")
        return result

    def restore_files(self, repo_dir: str, src_dir: str) -> int:
        """Copy all non-hidden files from src_dir into repo_dir.

        Returns the number of files restored.
        """
        count = 0
        for name in os.listdir(src_dir):
            src = os.path.join(src_dir, name)
            dst = os.path.join(repo_dir, name)
            if os.path.isfile(src) and not name.startswith('.'):
                shutil.copy2(src, dst)
                count += 1
        self.log.info(f"Restore files: {count} files copied to {repo_dir}")
        return count

    def restore_config(self, repo_conf_dir: str, zip_path: str):
        """Replace the .conf directory with contents from a zip archive."""
        tmpdir = tempfile.mkdtemp()
        try:
            self.util.unzip(zip_path, tmpdir)

            old_conf = repo_conf_dir + '.old'
            if os.path.exists(old_conf):
                shutil.rmtree(old_conf)

            if os.path.exists(repo_conf_dir):
                shutil.move(repo_conf_dir, old_conf)

            os.makedirs(repo_conf_dir, exist_ok=True)
            for item in os.listdir(tmpdir):
                src = os.path.join(tmpdir, item)
                dst = os.path.join(repo_conf_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)

            if os.path.exists(old_conf):
                shutil.rmtree(old_conf)

            self.log.info(f"Restore config: replaced {repo_conf_dir} from {zip_path}")
        except Exception:
            if os.path.exists(old_conf):
                if os.path.exists(repo_conf_dir):
                    shutil.rmtree(repo_conf_dir)
                shutil.move(old_conf, repo_conf_dir)
            raise
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def restore_repository(self, repo_dir: str, zip_path: str):
        """Replace the entire repository with contents from a zip archive."""
        tmpdir = tempfile.mkdtemp()
        try:
            self.util.unzip(zip_path, tmpdir)

            old_repo = repo_dir + '.old'
            if os.path.exists(old_repo):
                shutil.rmtree(old_repo)

            if os.path.exists(repo_dir):
                shutil.move(repo_dir, old_repo)

            os.makedirs(repo_dir, exist_ok=True)
            for item in os.listdir(tmpdir):
                src = os.path.join(tmpdir, item)
                dst = os.path.join(repo_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)

            if os.path.exists(old_repo):
                shutil.rmtree(old_repo)

            self.log.info(f"Restore repository: replaced {repo_dir} from {zip_path}")
        except Exception:
            if os.path.exists(old_repo):
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir)
                shutil.move(old_repo, repo_dir)
            raise
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
