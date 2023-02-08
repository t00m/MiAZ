#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import glob
import json
import time

from datetime import datetime
from dateutil.parser import parse as dateparser

from gi.repository import GObject

from MiAZ.backend.env import ENV
from MiAZ.backend.log import get_logger

class MiAZUtil(GObject.GObject):
    """Backend class"""
    __gtype_name__ = 'MiAZUtil'

    def __init__(self, backend):
        self.log = get_logger('MiAZ.Backend.Util')
        self.backend = backend
        self.conf = self.backend.conf
        self.log.debug("Utils initialized")

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
                adate = guess_datetime(field[:8])
                timestamp = adate.strftime("%Y%m%d")
                if timestamp is not None:
                    found_date = True
                    # ~ self.log.debug("Found: %s", timestamp)
                    break
            except Exception as error:
                pass
        if not found_date:
            try:
                created = get_file_creation_date(filepath)
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

        # Check filename
        dot = filename.rfind('.')
        if dot > 0:
            name = filename[:dot]
            ext = filename[dot+1:]

            # Check extension
            valid &= True
            reasons.append((True, "File extension '%s' is valid" % ext))
        else:
            name = filename
            ext = ''
            valid &= False
            reasons.append((False, "File extension missing."))

        # Check fields partitioning
        partitioning = False
        fields = name.split('-')
        if len(fields) != 8:
            valid &= False
            reasons.append((False, "Wrong number of fields (%d/8)" %
                                                        len(fields)))
        else:
            reasons.append((True, "Right number of fields (%d/8)" %
                                                        len(fields)))
            partitioning = True

        # Validate fields
        # Check timestamp (1st field)
        try:
            timestamp = fields[0]
            if guess_datetime(timestamp) is None:
                valid &= False
                reasons.append((False, "Timestamp '%s' not valid" %
                                                            timestamp))
            else:
                reasons.append((True, "Timestamp '%s' is valid" %
                                                            timestamp))
        except IndexError:
            valid &= False
            reasons.append((False, "Timestamp couldn't be checked"))

        # Check country (2nd field)
        try:
            code = fields[1]
            is_country = self.conf['Country'].exists(code)
            if not is_country:
                valid &= False
                reasons.append((False,
                                "Country code '%s' doesn't exist" %
                                                                code))
            else:
                default = self.conf['Country'].default
                country = self.conf['Country'].load(default)
                name = country[code]
                reasons.append((True,
                                "Country code '%s' corresponds to %s" %
                                                        (code, name)))
        except IndexError:
            valid &= False
            reasons.append((False,
                            "Country code couldn't be checked"))

        # Check group (3th field)
        try:
            code = fields[2]
            is_group = self.conf['Group'].exists(code)
            if not is_group:
                valid &= False
                reasons.append((False,
                                "Group '%s' is not in your list." \
                                " Please, add it first." % code))
            else:
                reasons.append((True,
                                "Group '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Group couldn't be checked"))

        # Check subgroup (4th field)
        try:
            code = fields[3]
            is_subgroup = self.conf['Subgroup'].exists(code)
            if not is_subgroup:
                valid &= False
                reasons.append((False,
                                "Subgroup '%s' is not in your list." \
                                " Please, add it first." % code))
            else:
                reasons.append((True,
                                "Subgroup '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Subgroup couldn't be checked"))

        # Check SentBy (5th field)
        try:
            code = fields[4]
            is_people = self.conf['Person'].exists(code)
            if not is_people:
                valid &= False
                reasons.append((False,
                                "Person '%s' is not in your list. " \
                                "Please, add it first." % code))
            else:
                reasons.append((True, "Person '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Person couldn't be checked"))

        # Check purpose (6th field)
        try:
            code = fields[5]
            is_purpose = self.conf['Purpose'].exists(code)
            if not is_purpose:
                valid &= False
                reasons.append((False,
                                "Purpose '%s' is not in your list. " \
                                "Please, add it first." % code))
            else:
                reasons.append((True, "Purpose '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Purpose couldn't be checked"))

        # Check Concept (7th field)
        try:
            code = fields[6]
            reasons.append((True, "Concept '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Concept couldn't be checked"))

        # Check SentTo (8th field)
        try:
            code = fields[7]
            is_people = self.conf['Person'].exists(code)
            if not is_people:
                valid &= False
                reasons.append((False,
                                "Person '%s' is not in your list. " \
                                "Please, add it first." % code))
            else:
                reasons.append((True, "Person '%s' accepted" % code))
        except IndexError:
            valid &= False
            reasons.append((False, "Person couldn't be checked"))

        # ~ if partitioning is True:
            # ~ self.conf['Group'].add_available(fields[2])
            # ~ self.conf['Subgroup'].add_available(fields[3])
            # ~ self.conf['SentBy'].add_available(fields[4])
            # ~ self.conf['Purpose'].add_available(fields[5])
            # ~ self.conf['SentTo'].add_available(fields[7])

        return valid, reasons

# ~ from MiAZ.backend.log import get_logger

# ~ log = get_logger('Util')

def get_version() -> str:
    return open(ENV['FILE']['VERSION']).read().strip()

def json_load(filepath: str) -> {}:
    """Load into a dictionary a file in json format"""
    with open(filepath, 'r') as fin:
        adict = json.load(fin)
    return adict

def json_save(filepath: str, adict: {}) -> {}:
    """Save dictionary into a file in json format"""
    with open(filepath, 'w') as fout:
        json.dump(adict, fout, sort_keys=True, indent=4)

def get_filename_details(filepath: str):
    basename = os.path.basename(filepath)
    dot = basename.rfind('.')
    if dot > 0:
        name = basename[:dot]
        ext = basename[dot+1:].lower()
    else:
        name = basename
        ext = ''
    return name, ext

def guess_datetime(adate: str) -> datetime:
    """Return (guess) a datetime object for a given string."""
    if len(adate) != 8:
        return None

    try:
        timestamp = dateparser(adate)
    except Exception as error:
        timestamp = None

    return timestamp

def valid_key(key):
    key = str(key).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', key)

def get_fields(filename: str) -> []:
        filename = os.path.basename(filename)
        dot = filename.rfind('.')
        if dot > 0:
            filename = filename[:dot]
        return filename.split('-')

def get_files(root_dir: str) -> []:
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

def get_file_creation_date(filepath: str) -> datetime:
    created = os.stat(filepath).st_ctime
    adate = datetime.fromtimestamp(created)
    return adate #.strftime("%Y%m%d")

def dir_writable(dirpath: str) -> bool:
    try:
        filename = os.path.join(dirpath, 'test.txt')
        with open(filename, 'w') as fout:
            fout.write('test')
            writable = True
        os.unlink(filename)
    except IOError as error:
        writable = False
    except TypeError:
        writable = False
    return writable

def fuzzy_date_from_timestamp(timestamp):
    """
    Convert datetime object to fuzzy time string
    """
    d1 = guess_datetime(timestamp)
    d2 = datetime.now()
    rdate = d2 - d1 # DateTimeDelta
    if rdate.days > 0:
        if rdate.days <= 31:
            return "%d days ago" % int(rdate.days)

        if rdate.days > 31 and rdate.days < 365:
            return "%d months ago" % int((rdate.days/31))

        if rdate.days >= 365:
            return "%d years ago" % int((rdate.days/365))

    hours = rdate.seconds / 3600
    if int(hours) > 0:
        return "%d hours ago" % int(hours)

    minutes = rdate.seconds / 60
    if int(minutes) > 0:
        return "%d minutes ago" % int(minutes)

    if int(rdate.seconds) > 0:
        return "%d seconds ago" % int(rdate.seconds)

    if int(rdate.seconds) == 0:
        return "Right now"

def normalize_filename(filename: str) -> str:
    name, ext = get_filename_details(filename)
    if not is_normalized(name):
        fields = ['' for fields in range(8)]
        fields[6] = name.replace('-', '_')
        filename = "%s.%s" % ('-'.join(fields), ext)
    else:
        filename = "%s.%s" % (name, ext)
    return filename

def is_normalized(name: str) -> bool:
    try:
        if len(name.split('-')) == 8:
            normalized = True
        else:
            normalized = False
    except:
        normalized = False
    return normalized




# ~ def timerfunc(func):
    # ~ """
    # ~ A timer decorator
    # ~ """
    # ~ def function_timer(*args, **kwargs):
        # ~ """
        # ~ A nested function for timing other functions
        # ~ """
        # ~ start = time.time()
        # ~ value = func(*args, **kwargs)
        # ~ end = time.time()
        # ~ runtime = end - start
        # ~ msg = "The runtime for '{func}' took {time} seconds to complete"
        # ~ log.debug(msg.format(func=func.__name__, time=runtime))
        # ~ return value
    # ~ return function_timer


# ~ class MyTimer():
    # ~ def __init__(self):
        # ~ self.start = time.time()

    # ~ def __enter__(self):
        # ~ return self

    # ~ def __exit__(self, exc_type, exc_val, exc_tb):
        # ~ end = time.time()
        # ~ runtime = end - self.start
        # ~ msg = 'The function took {time} seconds to complete'
        # ~ log.debug(msg.format(time=runtime))
