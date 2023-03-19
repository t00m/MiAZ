#!/usr/bin/python3
# -*- coding: utf-8 -*-

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
import time
import shutil
import zipfile
from datetime import datetime, timedelta
# ~ from dateutil.parser import parse as dateparser

from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy
from MiAZ.backend.models import SentTo, Date, Extension

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

    def __init__(self, backend):
        self.log = get_logger('MiAZ.Backend.Util')
        self.backend = backend
        self.conf = self.backend.conf

    def directory_open(self, dirpath: str):
        os.system("xdg-open '%s'" % dirpath)
        self.log.debug("Directory %s opened in file browser" % dirpath)

    def directory_remove(self, dirpath: str):
        shutil.rmtree(dirpath)
        self.log.debug("Directory %s deleted" % dirpath)

    def directory_create(self, dirpath: str):
        os.makedirs(dirpath, exist_ok = True)
        self.log.debug("Directory %s created" % dirpath)

    # ~ def guess_datetime(self, adate: str) -> datetime:
        # ~ """Return (guess) a datetime object for a given string."""
        # ~ if len(adate) != 7:
            # ~ return None

        # ~ try:
            # ~ timestamp = dateparser(adate)
        # ~ except Exception as error:
            # ~ timestamp = None

        # ~ return timestamp

    def json_load(self, filepath: str) -> {}:
        """Load into a dictionary a file in json format"""
        with open(filepath, 'r') as fin:
            adict = json.load(fin)
        return adict

    def json_save(self, filepath: str, adict: {}) -> {}:
        """Save dictionary into a file in json format"""
        with open(filepath, 'w') as fout:
            json.dump(adict, fout, sort_keys=True, indent=4)

    def field_used(self, item_type, value):
        used = False
        for doc in self.get_files():
            fields = self.get_fields(doc)
            fn = Field[item_type]
            if fields[fn] == value:
                used = True
                self.log.warning("Value %s of type %s is still being used in %s", value, item_type.__title__, doc)
                break
        return used

    def get_temp_dir(self):
        repo = self.backend.repo_config()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = self.valid_key(repo['dir_docs'])
        return os.path.join(ENV['LPATH']['TMP'], "%s_%s" % (ts, name))

    def get_temp_file(self, dir_tmp, suffix='.txt'):
        return tempfile.mkstemp(dir=dir_tmp, suffix=suffix)


    def get_fields(self, filename: str) -> []:
            filename = os.path.basename(filename)
            dot = filename.rfind('.')
            if dot > 0:
                filename = filename[:dot]
            return filename.split('-')

    def get_files(self, root_dir: str = '') -> []:
        if len(root_dir) == 0:
            repo = self.backend.repo_config()
            root_dir = repo['dir_docs']
        return glob.glob(os.path.join(root_dir, '*'))

    def get_files_recursively(self, root_dir: str) -> []:
        """Get documents from a given directory recursively
        Avoid hidden documents and documents from hidden directories.
        """
        documents = set()
        hidden = set()
        subdirs = set()

        subdirs.add(os.path.abspath(root_dir))
        for root, dirs, files in os.walk(os.path.abspath(root_dir)):
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

    def filename_get_creation_date(self, doc: str) -> datetime:
        repo = self.backend.repo_config()
        dir_repo = repo['dir_docs']
        filepath = os.path.join(dir_repo, doc)
        lastmod = os.stat(filepath).st_mtime
        return datetime.fromtimestamp(lastmod)

    def filename_get_mimetype(self, filepath: str) -> str:
        mimetype, val = Gio.content_type_guess('filename=%s' % filepath, data=None)
        return mimetype

    def filename_details(self, filepath: str):
        basename = os.path.basename(filepath)
        dot = basename.rfind('.')
        if dot > 0:
            name = basename[:dot]
            ext = basename[dot+1:].lower()
        else:
            name = basename
            ext = ''
        return name, ext

    def filename_is_normalized(self, name: str) -> bool:
        try:
            if len(name.split('-')) == 7:
                normalized = True
            else:
                normalized = False
        except:
            normalized = False
        return normalized

    def filename_normalize(self, filename: str) -> str:
        name, ext = self.filename_details(filename)
        if not self.filename_is_normalized(name):
            fields = ['' for fields in range(7)]
            fields[5] = self.valid_key(name)
            filename = "%s.%s" % ('-'.join(fields), ext)
        else:
            filename = "%s.%s" % (name, ext)
        return filename

    def valid_key(self, key: str) -> str:
        key = str(key).strip().replace('-', '_')
        key = str(key).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', key)

    def filename_rename(self, doc_source, doc_target):
        repo = self.backend.repo_config()
        dir_repo = repo['dir_docs']
        source = os.path.join(dir_repo, doc_source)
        target = os.path.join(dir_repo, doc_target)
        if source != target:
            if not os.path.exists(target):
                try:
                    shutil.move(source, target)
                    self.log.info("%s renamed to %s", source, target)
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.error("Target '%s' already exist. Skip rename", doc_target)
        else:
            self.log.error("Source and Target are the same. Skip rename")

    def filename_delete(self, filepath):
        try:
            os.unlink(filepath)
            self.log.debug("File %s deleted", filepath)
        except IsADirectoryError as error:
            self.log.error(error)

    def filename_import(self, source: str, target: str):
        """Import file into repository

        Normally, only the source filename would be necessary, but
        as it is renamed according MiAZ rules, target is also needed.
        """
        repo = self.backend.repo_config()
        target = repo['dir_docs']
        self.filename_copy(source, target)

    def filename_export(self, doc: str, target: str):
        repo = self.backend.repo_config()
        source = os.path.join(repo['dir_docs'], doc)
        self.filename_copy(source, target)

    def filename_copy(self, source, target, overwrite=True):
        # ~ repo = self.backend.repo_config()
        # ~ dir_repo = repo['dir_docs']
        # ~ target = os.path.join(dir_repo, doc_target)
        if source != target:
            if overwrite:
                try:
                    # preserve metadata
                    shutil.copy2(source, target)
                    self.log.info("%s copied to %s", source, target)
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.debug("Target file %s exists. Copy operation skipped", target)
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
            date_dsc = ''
        return date_dsc

    def filename_display(self, doc):
        filepath = self.filename_path(doc)
        if sys.platform in ['linux', 'linux2']:
            os.system("xdg-open \"%s\"" % filepath)
        elif sys.platform in ['win32', 'cygwin', 'msys']:
            os.startfile(filepath)

    def filename_open_location(self, doc):
        repo = self.backend.repo_config()
        dir_docs = repo['dir_docs']
        filepath = os.path.join(dir_docs, doc)
        # FIXME: only works if nautilus is present
        if sys.platform in ['linux', 'linux2']:
            CMD = "nautilus \"%s\"" % filepath
        elif sys.platform in['win32', 'cygwin', 'msys']:
            CMD = r"""explorer /select,%s""" % filepath
        self.log.debug(CMD)
        os.system(CMD)

    def filename_path(self, doc):
        repo = self.backend.repo_config()
        dirpath = repo['dir_docs']
        return os.path.join(dirpath, doc)

    def filename_validate(self, doc:str) -> bool:
        if len(doc.split('-')) == 7:
            return True
        return False

    def filename_validate_complex(self, filepath: str) -> tuple:
        repo = self.backend.repo_config()
        dir_repo = repo['dir_docs']
        filename = os.path.basename(filepath)
        reasons = "OK"
        valid = True
        reasons = []

        # Check fields partitioning
        partitioning = False
        fields = filename.split('-')
        if len(fields) != 7:
            source = filename
            target = self.filename_normalize(filename)
            if source != target:
                self.filename_rename(source, target)
            else:
                self.log.debug("Target normalized filename is the same than source")
        name, ext = self.filename_details(filename)
        fields = name.split('-')

        # Check extension
        item_type = Extension
        gtype = Date.__gtype_name__
        dot = filename.rfind('.')
        if dot > 0:
            name = filename[:dot]
            ext = filename[dot+1:]
            message = "File extension '%s' is valid" % ext
            rc = True
        else:
            name = filename
            ext = ''
            rc = False
            valid &= False
            message = "File extension missing. Please, check this document!"
        reasons.append((rc, gtype, ext, message))

        # Validate fields
        for item_type in [Date, Country, Group, SentBy, Purpose, SentTo]:
            gtype = item_type.__gtype_name__
            fn = Field[item_type] # Field number
            fname = item_type.__gtype_name__
            title = item_type.__title__
            key = fields[fn]
            value = None
            if len(key) == 0:
                valid &= False
                rc = False
                message = "<i>%s</i> field is empty" % title
            else:
                if item_type != Date:
                    available = self.conf[fname].exists_available(key)
                    used = self.conf[fname].exists_used(key)
                    if available and used:
                        rc = True
                        items = self.conf[fname].load_used()
                        value = self.conf[fname].get(key)
                        if len(value) > 0:
                            message = "%s %s (%s) is available and ready to use" % (fname, key, value)
                        else:
                            message = "%s %s is available and ready to use" % (fname, key)
                    else:
                        valid &= False
                        rc = False
                        message = "%s %s available? %s. Used? %s" % (title, key, available, used)
            reasons.append((rc, gtype, value, message))
        return valid, reasons

    def since_date_this_year(self, adate: datetime) -> datetime:
        year = adate.year
        return datetime.strptime("%4d0101" % year, "%Y%m%d")

    def since_date_past_year(self, adate: datetime) -> datetime:
        year = adate.year - 1
        return datetime.strptime("%4d0101" % year, "%Y%m%d")

    def since_date_three_years(self, adate: datetime) -> datetime:
        year = adate.year - 2
        return datetime.strptime("%4d0101" % year, "%Y%m%d")

    def since_date_five_years(self, adate: datetime) -> datetime:
        year = adate.year - 4
        return datetime.strptime("%4d0101" % year, "%Y%m%d")

    def since_date_this_month(self, adate: datetime) -> datetime:
        year = adate.year
        month = adate.month
        return datetime.strptime("%4d%02d01" % (year, month), "%Y%m%d")

    def since_date_this_day(self, adate: datetime) -> datetime:
        return datetime.strptime("%4d%02d%02d" % (adate.year, adate.month, adate.day), "%Y%m%d")

    def since_date_last_n_months(self, adate: datetime, nm: int) -> datetime:
        return (adate - timedelta(days=30*nm)).replace(day=1)

    def since_date_last_six_months(self, adate: datetime) -> datetime:
        return (adate - timedelta(days=30*6)).replace(day=1).date()

    def datetime_to_string(self, adate: datetime) -> str:
        return adate.strftime("%Y%m%d")

    def string_to_datetime(self, adate: str) -> datetime:
        try:
            return datetime.strptime(adate, "%Y%m%d").date()
        except ValueError:
            return None

    def zip(self, filename: str, directory: str):
        """ Zip directory into a file """
        self.log.debug("Target: %s", filename)
        sourcename = os.path.basename(filename)
        dot = sourcename.find('.')
        if dot == -1:
            basename = sourcename
        else:
            basename = sourcename[:dot]
        sourcedir = os.path.dirname(filename)
        source = os.path.join(sourcedir, basename)
        zipfile = shutil.make_archive(source, 'zip', directory)
        target = source + '.zip'
        shutil.move(zipfile, target)
        return target

    def unzip(self, target: str, install_dir):
        """
        Unzip file to a given dir
        """
        zip_archive = zipfile.ZipFile(target, "r")
        zip_archive.extractall(path=install_dir)
        zip_archive.close()
