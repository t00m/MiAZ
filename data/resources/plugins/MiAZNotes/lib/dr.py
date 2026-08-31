# pylint: disable=E1101

"""
# File: dr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Backup / restore for MiAZNotes data directory
"""

import os
import shutil
import zipfile
from datetime import datetime

from MiAZ.backend.util import check_zip_members


def _report(progress, message: str, fraction: float = None):
    """Send one progress update, when the caller asked for them.

    Called from wherever the backup runs, a worker thread included: this module
    knows nothing about the UI, so marshalling is the caller's job.
    """
    if progress is not None:
        progress(message, fraction)


class NotesBackup:
    """Zip/unzip the plugin's notes data directory."""

    def __init__(self, data_dir: str, log):
        self.data_dir = data_dir
        self.log = log

    @staticmethod
    def default_backup_name() -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"MiAZNotes-backup-{timestamp}.zip"

    def backup(self, dest_zip: str, progress=None) -> int:
        """Zip the data directory. progress(message, fraction) is optional and
        is called once per note, so the caller can drive a progress bar."""
        if not os.path.exists(self.data_dir):
            self.log.warning(f"Notes data dir does not exist: {self.data_dir}")
            return 0

        # Listed before writing anything: the total is what makes the caller's
        # progress bar a bar rather than a spinner.
        entries = []
        for root, _dirs, files in os.walk(self.data_dir):
            for filename in files:
                absolute = os.path.join(root, filename)
                entries.append((absolute, os.path.relpath(absolute, self.data_dir)))

        count = 0
        try:
            with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zfile:
                for absolute, relative in entries:
                    zfile.write(absolute, relative)
                    count += 1
                    _report(progress, relative, count / len(entries))
        except Exception as error:
            self.log.error(f"Backup failed ({dest_zip}): {error}")
            return 0
        self.log.info(f"Backed up {count} notes to {dest_zip}")
        return count

    def restore(self, source_zip: str, merge: bool = True, progress=None) -> int:
        if not os.path.exists(source_zip):
            self.log.error(f"Backup file not found: {source_zip}")
            return 0

        if not merge and os.path.exists(self.data_dir):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_dir = f"{self.data_dir}.bak-{timestamp}"
            try:
                os.rename(self.data_dir, backup_dir)
                self.log.info(f"Existing notes preserved at {backup_dir}")
            except OSError as error:
                self.log.error(f"Could not rename '{self.data_dir}': {error}")
                return 0

        os.makedirs(self.data_dir, exist_ok=True)

        count = 0
        try:
            with zipfile.ZipFile(source_zip, 'r') as zfile:
                # A restore archive is a file the user picked, so it is as
                # untrusted as an imported plugin zip. Same check, and it runs
                # over the whole listing before anything is written.
                check_zip_members(zfile.namelist(), self.data_dir)
                members = [info for info in zfile.infolist() if not info.is_dir()]
                for info in members:
                    zfile.extract(info, self.data_dir)
                    count += 1
                    _report(progress, info.filename, count / len(members))
        except Exception as error:
            self.log.error(f"Restore failed ({source_zip}): {error}")
            return 0
        self.log.info(f"Restored {count} notes from {source_zip}")
        return count

    def reset_data_dir(self) -> None:
        if os.path.exists(self.data_dir):
            try:
                shutil.rmtree(self.data_dir)
            except OSError as error:
                self.log.error(f"Could not remove '{self.data_dir}': {error}")
        os.makedirs(self.data_dir, exist_ok=True)
