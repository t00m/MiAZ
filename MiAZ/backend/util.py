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
from MiAZ.backend.models import Group, Subgroup, Person, Country
from MiAZ.backend.models import Purpose, Concept, SentBy, SentTo

Field = {}
Field[Country] = 1
Field[Group] = 2
Field[Subgroup] = 3
Field[SentBy] = 4
Field[Purpose] = 5
Field[SentTo] = 7


class MiAZUtil(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZUtil'

    def __init__(self, backend):
        self.log = get_logger('MiAZ.Backend.Util')
        self.backend = backend
        self.conf = self.backend.conf

    def guess_datetime(self, adate: str) -> datetime:
        """Return (guess) a datetime object for a given string."""
        if len(adate) != 8:
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

    def get_file_creation_date(self, filepath: str) -> datetime:
        created = os.stat(filepath).st_ctime
        adate = datetime.fromtimestamp(created)
        return adate #.strftime("%Y%m%d")

    def get_filename_details(self, filepath: str):
        basename = os.path.basename(filepath)
        dot = basename.rfind('.')
        if dot > 0:
            name = basename[:dot]
            ext = basename[dot+1:].lower()
        else:
            name = basename
            ext = ''
        return name, ext

    def is_normalized(self, name: str) -> bool:
        try:
            if len(name.split('-')) == 8:
                normalized = True
            else:
                normalized = False
        except:
            normalized = False
        return normalized

    def normalize_filename(self, filename: str) -> str:
        name, ext = self.get_filename_details(filename)
        if not self.is_normalized(name):
            fields = ['' for fields in range(8)]
            fields[6] = name.replace('-', '_')
            filename = "%s.%s" % ('-'.join(fields), ext)
        else:
            filename = "%s.%s" % (name, ext)
        return filename

    def valid_key(self, key: str) -> str:
        key = str(key).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', key)

    def suggest_filename(self, filepath: str, valid: bool = False) -> str:
        timestamp = ""
        country = ""
        group = ""
        subgroup = ""
        person = ""
        purpose = ""
        concept = ""
        extension = ""

        filename = os.path.basename(filepath)
        dot = filename.rfind('.')
        if dot > 0:
            name = filename[:dot]
            ext = filename[dot+1:].lower()
        else:
            name = filename
            ext = ''

        fields = name.split('-')

        # ~ self.log.debug(filename)
        # Field 0. Find and/or guess date field
        found_date = False
        for field in fields:
            # ~ self.log.debug(field)
            try:
                adate = self.guess_datetime(field[:8])
                timestamp = adate.strftime("%Y%m%d")
                if timestamp is not None:
                    found_date = True
                    # ~ self.log.debug("Found: %s", timestamp)
                    break
            except Exception as error:
                pass
        if not found_date:
            try:
                created = self.get_file_creation_date(filepath)
                timestamp = created.strftime("%Y%m%d")
                # ~ self.log.debug("Creation date: %s", timestamp)
            except Exception as error:
                # ~ self.log.error("%s -> %s" % (filepath, error))
                timestamp = ""
        # ~ self.log.debug(timestamp)

        # Field 1. Find and/or guess country field
        found_country = False
        for field in fields:
            if len(field) == 2:
                is_country = self.conf['Country'].exists(field)
                if is_country:
                    country = field
                    found_country = True
                    break
        if not found_country:
            country = ""

        # Field 2. Find and/or guess group field
        found_group = False
        for field in fields:
            if self.conf['Group'].exists(field):
                group = field
                found_group = True
                break
        if not found_group:
            group = ''

        # Field 3. Find and/or guess subgroup field
        found_subgroup = False
        for field in fields:
            if self.conf['Subgroup'].exists(field):
                subgroup = field
                found_subgroup = True
                break
        if not found_subgroup:
            subgroup = ''

        # Field 4. Find and/or guess SentBy field
        found_person = False
        for field in fields:
            if self.conf['Person'].exists(field):
                sentby = field
                found_person = True
                break
        if not found_person:
            sentby = ''

        # Field 5. Find and/or guess purpose field
        found_purpose = False
        for field in fields:
            if self.conf['Purpose'].exists(field):
                purpose = field
                found_purpose = True
                break
        if not found_purpose:
            purpose = ''

        # Field 6. Do NOT find and/or guess concept field. Free field.
        if not valid:
            concept = name.replace('-', '_')
        else:
            concept = fields[5]

        # Field 7. Find and/or guess SentTo field
        found_person = False
        for field in fields:
            if self.conf['Person'].exists(field):
                found_person = True
                sentto = field
                break
        if not found_person:
            sentto = ''

        suggested = "%s-%s-%s-%s-%s-%s-%s-%s" % (timestamp,
                                                country,
                                                group,
                                                subgroup,
                                                sentby,
                                                purpose,
                                                concept,
                                                sentto)
        # ~ self.log.debug("%s -> %s", filename, suggested)
        return suggested

    def validate_filename(self, filepath: str) -> tuple:
        filename = os.path.basename(filepath)
        reasons = "OK"
        valid = True
        reasons = []

        # Check fields partitioning
        partitioning = False
        fields = filename.split('-')
        if len(fields) != 8:
            filename = self.normalize_filename(filename)
            target = os.path.join(os.path.dirname(filepath), filename)
            shutil.move(filepath, target)
            self.log.debug("%s renamed to %s", filepath, filename)
        fields = filename.split('-')

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
                used = self.conf[fname].exists_available(key)
                available = self.conf[fname].exists_used(key)
                if not used and not available:
                    valid &= False
                    rc = False
                    message = "%s '%s' available? %s. Used? %s" % (fname, key, available, used)
                else:
                    rc = True
                    items = self.conf[fname].load_used()
                    value = self.conf[fname].get(key)
                    if len(value) > 0:
                        message = "%s key '%s (%s)' is available and ready to use" % (fname, key, value)
                    else:
                        message = "%s key '%s' is available and ready to use" % (fname, key)
            reasons.append((rc, message))
        return valid, reasons
