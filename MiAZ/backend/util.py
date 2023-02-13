#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import glob
import json
import time
import shutil
from datetime import datetime
from dateutil.parser import parse as dateparser

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger
from MiAZ.backend.models import Group, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy, SentTo

Field = {}
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

    def guess_datetime(self, adate: str) -> datetime:
        """Return (guess) a datetime object for a given string."""
        if len(adate) != 7:
            return None

        try:
            timestamp = dateparser(adate)
        except Exception as error:
            timestamp = None

        return timestamp

    def json_load(self, filepath: str) -> {}:
        """Load into a dictionary a file in json format"""
        with open(filepath, 'r') as fin:
            adict = json.load(fin)
        return adict

    def json_save(self, filepath: str, adict: {}) -> {}:
        """Save dictionary into a file in json format"""
        with open(filepath, 'w') as fout:
            json.dump(adict, fout, sort_keys=True, indent=4)


    def get_fields(self, filename: str) -> []:
            filename = os.path.basename(filename)
            dot = filename.rfind('.')
            if dot > 0:
                filename = filename[:dot]
            return filename.split('-')

    def get_files(self, root_dir: str) -> []:
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
        created = os.stat(filepath).st_ctime
        adate = datetime.fromtimestamp(created)
        return adate #.strftime("%Y%m%d")

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
            fields[5] = name.replace('-', '_')
            filename = "%s.%s" % ('-'.join(fields), ext)
        else:
            filename = "%s.%s" % (name, ext)
        return filename

    def valid_key(self, key: str) -> str:
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

    def filename_copy(self, source, doc_target):
        repo = self.backend.repo_config()
        dir_repo = repo['dir_docs']
        target = os.path.join(dir_repo, doc_target)
        if source != target:
            if not os.path.exists(target):
                try:
                    shutil.copy(source, target)
                    self.log.info("%s renamed to %s", source, target)
                except Exception as error:
                    self.log.error(error)
            else:
                self.log.error("Target '%s' already exist. Skip rename", doc_target)
        else:
            self.log.error("Source and Target are the same. Skip rename")

    def filename_delete(self, doc):
        pass

    def filename_display(self, doc):
        filepath = self.filename_path(doc)
        os.system("xdg-open '%s'" % filepath)

    def filename_path(self, doc):
        repo = self.backend.repo_config()
        dirpath = repo['dir_docs']
        return os.path.join(dirpath, doc)

    def filename_validate(self, filepath: str) -> tuple:
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
        item_type = None
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
        reasons.append((rc, message))

        # Validate fields
        for item_type in [Country, Group, SentBy, Purpose, SentTo]:
            fn = Field[item_type] # Field number
            fname = item_type.__gtype_name__
            key = fields[fn]
            if len(key) == 0:
                valid &= False
                rc = False
                message = "%s field is empty" % fname
            else:
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
                    message = "%s %s available? %s. Used? %s" % (fname, key, available, used)
            reasons.append((rc, message))
        return valid, reasons
