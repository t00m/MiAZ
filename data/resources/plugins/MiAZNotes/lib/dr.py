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


class NotesBackup:
    """Zip/unzip the plugin's notes data directory."""

    def __init__(self, data_dir: str, log):
        self.data_dir = data_dir
        self.log = log

    @staticmethod
    def default_backup_name() -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"MiAZNotes-backup-{timestamp}.zip"

    def backup(self, dest_zip: str) -> int:
        if not os.path.exists(self.data_dir):
            self.log.warning(f"Notes data dir does not exist: {self.data_dir}")
            return 0

        count = 0
        try:
            with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zfile:
                for root, _dirs, files in os.walk(self.data_dir):
                    for filename in files:
                        absolute = os.path.join(root, filename)
                        relative = os.path.relpath(absolute, self.data_dir)
                        zfile.write(absolute, relative)
                        count += 1
        except Exception as error:
            self.log.error(f"Backup failed ({dest_zip}): {error}")
            return 0
        self.log.info(f"Backed up {count} notes to {dest_zip}")
        return count

    def restore(self, source_zip: str, merge: bool = True) -> int:
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
                for info in zfile.infolist():
                    if info.is_dir():
                        continue
                    zfile.extract(info, self.data_dir)
                    count += 1
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
