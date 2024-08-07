#!/usr/bin/python3

"""
# File: util.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: useful often low-level methods for this app
"""

import os
import re
import sys
import glob
import json
import shutil
import tempfile
import traceback
import mimetypes
import zipfile
from datetime import datetime, timedelta
# ~ from dateutil.parser import parse as dateparser

from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country
from MiAZ.backend.models import Purpose, SentBy
from MiAZ.backend.models import SentTo, Date

mimetypes.init()

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6


class MiAZUtil(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZUtil'

    def __init__(self, app):
        GObject.GObject.__init__(self)
        GObject.signal_new('filename-added',
                            MiAZUtil,
                            GObject.SignalFlags.RUN_LAST,
                            GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,))
        GObject.signal_new('filename-deleted',
                            MiAZUtil,
                            GObject.SignalFlags.RUN_LAST,
                            GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,))
        GObject.signal_new('filename-renamed',
                            MiAZUtil,
                            GObject.SignalFlags.RUN_LAST,
                            GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,))
        self.log = MiAZLog('MiAZ.Backend.Util')
        self.app = app

    def display_traceback(self):
        self.log.error("Traceback:", exc_info=True)

    def directory_open(self, dirpath: str):
        if sys.platform in ['linux', 'linux2']:
            os.system(f"xdg-open '{dirpath}'")
        elif sys.platform in ['win32', 'cygwin', 'msys']:
            os.startfile(dirpath)


        self.log.debug(f"Directory {dirpath} opened in file browser")

    def directory_remove(self, dirpath: str):
        shutil.rmtree(dirpath)
        self.log.debug(f"Directory {dirpath} deleted")

    def directory_create(self, dirpath: str):
        os.makedirs(dirpath, exist_ok=True)
        self.log.debug(f"Directory {dirpath} created")

    def json_load(self, filepath: str) -> {}:
        """Load into a dictionary a file in json format"""
        with open(filepath) as fin:
            adict = json.load(fin)
        return adict

    def json_save(self, filepath: str, adict: {}) -> {}:
        """Save dictionary into a file in json format"""
        with open(filepath, 'w') as fout:
            json.dump(adict, fout, sort_keys=True, indent=4)

    def field_used(self, repo_dir, item_type, value):
        used = False
        docs = []
        for doc in self.get_files(repo_dir):
            fields = self.get_fields(doc)
            fn = Field[item_type]
            if fields[fn] == value:
                docs.append(doc)
        if len(docs) > 0:
            used = True
        return used, docs

    def get_mimetype(self, filename: str) -> str:
        if sys.platform == 'win32':
            name, ext = self.filename_details(filename)
            mimetype = f'.{ext}'
        else:
            url = f"file://{filename}"
            mimetype, encoding = mimetypes.guess_type(url)
        return mimetype


    def get_temp_dir(self):
        ENV = self.app.get_env()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(ENV['LPATH']['TMP'], f"{ts}_miaz-export")

    def get_temp_file(self, dir_tmp, suffix='.txt'):
        return tempfile.mkstemp(dir=dir_tmp, suffix=suffix)

    def get_fields(self, filename: str) -> []:
        filename = os.path.basename(filename)
        dot = filename.rfind('.')
        if dot > 0:
            filename = filename[:dot]
        return filename.split('-')

    def get_files(self, dirpath: str) -> []:
        """Get all files from a given directory."""
        # ~ FIXME: validate root_dir
        return glob.glob(os.path.join(dirpath, '*'))

    def get_files_recursively(self, root_dir: str) -> []:
        """Get documents from a given directory recursively
        Avoid hidden documents and documents from hidden directories.
        """
        documents = set()
        hidden = set()
        subdirs = set()

        subdirs.add(os.path.abspath(root_dir))
        for root, _dirs, files in os.walk(os.path.abspath(root_dir)):
            thisdir = os.path.abspath(root)
            if os.path.basename(thisdir).startswith('.'):
                hidden.add(thisdir)
            else:
                found = False
                for hidden_dir in hidden:
                    if hidden_dir in thisdir:
                        found = True
                if not found:
                    subdirs.add(thisdir)
        for directory in subdirs:
            files = glob.glob(os.path.join(directory, '*'))
            for thisfile in files:
                if not os.path.isdir(thisfile):
                    if not os.path.basename(thisfile).startswith('.'):
                        documents.add(thisfile)
        return documents

    def filename_get_creation_date(self, filepath: str) -> datetime:
        lastmod = os.stat(filepath).st_mtime
        return datetime.fromtimestamp(lastmod)

    def filename_get_mimetype(self, filepath: str) -> str:
        mimetype, val = Gio.content_type_guess(f"filename={filepath}", data=None)
        return mimetype

    def filename_details(self, filepath: str):
        basename = os.path.basename(filepath)
        dot = basename.rfind('.')
        if dot > 0:
            name = basename[:dot]
            ext = basename[dot + 1:].lower()
        else:
            name = basename
            ext = ''
        return name, ext

    def filename_is_normalized(self, name: str) -> bool:
        try:
            return len(name.split('-')) == 7
        except Exception:
            return False

    def filename_normalize(self, filename: str) -> str:
        name, ext = self.filename_details(filename)
        if not self.filename_is_normalized(name):
            fields = ['' for fields in range(7)]
            fields[5] = self.valid_key(name)
            filename = f"{'-'.join(fields)}.{ext}"
        else:
            filename = f"{name}.{ext}"
        return filename

    def valid_key(self, key: str) -> str:
        key = str(key).strip().replace('-', '_')
        key = str(key).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', key)

    def filename_rename(self, source, target) -> bool:
        rename = False
        if source != target:
            if not os.path.exists(target):
                try:
                    shutil.move(source, target)
                    self.log.debug(f"Renaming doc from '{source}' to {target}' successful")
                    rename = True
                    self.emit('filename-renamed', source, target)
                except Exception as error:
                    self.log.error(f"Renaming doc from '{source}' to {target}' not possible. Error: {error}")
            else:
                self.log.error(f"Renaming doc from '{source}' to {target}' not possible. Target already exist")
        else:
            # FIXME
            self.log.warning("FIXME: this might not be true in Windows systems")
            self.log.warning(f"Renaming doc from '{source}' to {target}' skipped. Source and target are the same")
        return rename

    def filename_delete(self, filepath):
        try:
            os.unlink(filepath)
            self.log.debug(f"File {filepath} deleted")
            self.emit('filename-deleted', filepath)
        except IsADirectoryError as error:
            self.log.error(error)

    def filename_import(self, source: str, target: str):
        """Import file into repository

        Normally, only the source filename would be necessary, but
        as it is renamed according MiAZ rules, target is also needed.
        """
        self.filename_copy(source, target)
        self.emit('filename-added', target)

    def filename_export(self, source: str, target: str):
        self.filename_copy(source, target)

    def filename_copy(self, source, target, overwrite=True):
        if source != target:
            if overwrite:
                try:
                    # preserve metadata
                    shutil.copy2(source, target)
                    self.log.info(f"{source} copied to {target}")
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.debug(f"Target file {target} exists. Copy operation skipped")
        else:
            self.log.error("Source and Target are the same. Skip rename")

    def filename_date_human(self, value: str = '') -> str:
        try:
            adate = datetime.strptime(value, "%Y%m%d")
            date_dsc = adate.strftime("%A, %B %d %Y")
        except ValueError:
            date_dsc = ''
        return date_dsc

    def filename_date_human_simple(self, value: str = '') -> str:
        try:
            adate = datetime.strptime(value, "%Y%m%d")
            date_dsc = adate.strftime("%d/%m/%Y")
        except ValueError:
            date_dsc = None
        return date_dsc

    def filename_display(self, filepath):
        # ~ self.log.debug(f"OS Platform: {sys.platform}")
        if sys.platform in ['linux', 'linux2']:
            os.system(f"xdg-open \"{filepath}\"")
        elif sys.platform in ['win32', 'cygwin', 'msys']:
            os.startfile(filepath)

    def filename_validate(self, doc: str) -> bool:
        if len(doc.split('-')) == 7:
            return True
        return False

    def since_date_this_year(self, adate: datetime) -> datetime:
        year = adate.year
        return datetime.strptime("%4d0101" % year, "%Y%m%d")

    def since_date_past_n_years_ago(self, adate: datetime, n: int) -> datetime:
        year = adate.year - n
        return datetime.strptime("%4d0101" % year, "%Y%m%d")

    def since_date_this_month(self, adate: datetime) -> datetime:
        year = adate.year
        month = adate.month
        return datetime.strptime("%4d%02d01" % (year, month), "%Y%m%d")

    def since_date_this_day(self, adate: datetime) -> datetime:
        return datetime.strptime("%4d%02d%02d" % (adate.year, adate.month, adate.day), "%Y%m%d")

    def since_date_last_n_months(self, adate: datetime, nm: int) -> datetime:
        return (adate - timedelta(days=30 * nm)).replace(day=1)

    def since_date_last_six_months(self, adate: datetime) -> datetime:
        return (adate - timedelta(days=30 * 6)).replace(day=1).date()

    def datetime_to_string(self, adate: datetime) -> str:
        return adate.strftime("%Y%m%d")

    def string_to_datetime(self, adate: str) -> datetime:
        try:
            return datetime.strptime(adate, "%Y%m%d").date()
        except ValueError:
            return None

    def zip(self, filename: str, directory: str):
        """ Zip directory into a file """
        # ~ self.log.debug(f"Target: {filename}")
        sourcename = os.path.basename(filename)
        dot = sourcename.find('.')
        if dot == -1:
            basename = sourcename
        else:
            basename = sourcename[:dot]
        sourcedir = os.path.dirname(filename)
        source = os.path.join(sourcedir, basename)
        zip_file = shutil.make_archive(source, 'zip', directory)
        target = source + '.zip'
        shutil.move(zip_file, target)
        return target

    def timestamp(self):
        """Get timestamp (YYYYmmdd_hhmmss)"""
        now = datetime.now()
        return "%4d%02d%02d_%02d%02d%02d" % (now.year, now.month, now.day,
                                             now.hour, now.minute, now.second)

    def unzip(self, target: str, install_dir):
        """
        Unzip file to a given dir
        """
        zip_archive = zipfile.ZipFile(target, "r")
        zip_archive.extractall(path=install_dir)
        zip_archive.close()

    def zip_list(self, filepath: str) -> []:
        zip_archive = zipfile.ZipFile(filepath, "r")
        return zip_archive.namelist()


def which(program):
    """
    Check if a program is available in $PATH
    """
    if sys.platform == 'win32':
        program = program + '.exe'

    def is_exe(fpath):
        """
        Missing method docstring (missing-docstring)
        """
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None
