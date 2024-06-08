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
import shutil
import zipfile
from inspect import currentframe, getframeinfo
from datetime import datetime, timedelta
# ~ from dateutil.parser import parse as dateparser

from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import Group, Country
from MiAZ.backend.models import Purpose, SentBy
from MiAZ.backend.models import SentTo, Date

Field = {}
Field[Date] = 0
Field[Country] = 1
Field[Group] = 2
Field[SentBy] = 3
Field[Purpose] = 4
Field[SentTo] = 6

def HERE(do_print=False):
    ''' Get the current file and line number in Python script. The line
    number is taken from the caller, i.e. where this function is called.
    Via: https://stackoverflow.com/a/67663308/2013690

    Parameters
    ----------
    do_print : boolean
        If True, print the file name and line number to stdout.

    Returns
    -------
    String with file name and line number if do_print is False.

    Examples
    --------
    >>> HERE() # Prints to stdout

    >>> print(HERE(do_print=False))
    '''
    frameinfo = getframeinfo(currentframe().f_back)
    filename = frameinfo.filename.split('/')[-1]
    linenumber = frameinfo.lineno
    loc_str = 'File: %s, line: %d >' % (filename, linenumber)
    if do_print:
        print('HERE AT %s' % (loc_str))
    else:
        return loc_str

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

    def field_used(self, repo_dir, item_type, value):
        used = False
        docs = []
        for doc in self.get_files(repo_dir):
            fields = self.get_fields(doc)
            fn = Field[item_type]
            if fields[fn] == value:
                docs.append(doc)
                # ~ used = True
                # ~ self.log.warning("Value %s of type %s is still being used in %s", value, _(item_type.__title__), doc)
                # ~ break
        if len(docs) > 0:
            used = True
        return used, docs

    def get_temp_dir(self):
        ENV = self.app.get_env()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(ENV['LPATH']['TMP'], "%s_%s" % (ts, 'miaz-export'))

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

    def filename_get_creation_date(self, filepath: str) -> datetime:
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

    def filename_rename(self, source, target) -> bool:
        rename = False
        if source != target:
            if not os.path.exists(target):
                try:
                    shutil.move(source, target)
                    self.log.debug("Document renamed:")
                    self.log.debug("\tFrom: '%s'", source)
                    self.log.debug("\t  To: '%s'", target)
                    rename = True
                    self.emit('filename-renamed', source, target)
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.debug("Document NOT renamed:")
                self.log.error("\tTarget '%s' already exist", target)
        # ~ else:
            # ~ self.log.error("Source and Target are the same. Skip rename")
        return rename

    def filename_delete(self, filepath):
        try:
            os.unlink(filepath)
            self.log.debug("File %s deleted", filepath)
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
            date_dsc = None
        return date_dsc

    def filename_display(self, filepath):
        if sys.platform in ['linux', 'linux2']:
            os.system("xdg-open \"%s\"" % filepath)
        elif sys.platform in ['win32', 'cygwin', 'msys']:
            os.startfile(filepath)

    def filename_validate(self, doc:str) -> bool:
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

    def get_line_code_info(self):
        frameinfo = getframeinfo(currentframe())
        return frameinfo.filename, frameinfo.lineno
