#!/usr/bin/python3

"""
# File: util.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: useful often low-level methods for this app
"""

import io
import os
import re
import ast
import sys
import glob
import json
import time
import shutil
import tempfile
import threading
import requests
import mimetypes
import zipfile
from datetime import datetime, timedelta

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

REMOTE_SCHEMES = {
    "sftp", "smb", "ftp", "http", "https", "dav", "davs", "afp", "mtp", "obex", "ssh"
}

class SafeDictExtractor(ast.NodeVisitor):
    def __init__(self, variable_name):
        self.variable_name = variable_name
        self.result = None

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == self.variable_name:
                self.result = self._safe_eval(node.value)

    def _safe_eval(self, node):
        if isinstance(node, ast.Dict):
            return {
                self._safe_eval(k): self._safe_eval(v)
                for k, v in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.List):
            return [self._safe_eval(elt) for elt in node.elts]
        elif isinstance(node, ast.Constant):  # str, int, float, etc.
            return node.value
        elif isinstance(node, ast.Call):
            # Handle gettext-style calls like _('Some text')
            if isinstance(node.func, ast.Name) and node.func.id == "_":
                if node.args and isinstance(node.args[0], ast.Constant):
                    return node.args[0].value
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")


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

    def extract_variable_from_python_module(self, filepath, variable_name):
        with open(filepath, "r") as f:
            tree = ast.parse(f.read(), filename=filepath)
        extractor = SafeDictExtractor(variable_name)
        extractor.visit(tree)
        if extractor.result is None:
            # ~ raise ValueError(f"Variable '{variable_name}' not found.")
            return None
        return extractor.result

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
                    self.log.debug(f"File renamed: '{source}' -> {target}'")
                    rename = True
                    self.emit('filename-renamed', source, target)
                except Exception as error:
                    self.log.error(f"Renaming doc from '{source}' to {target}' not possible. Error: {error}")
            else:
                # FIXME
                # ~ self.log.error(f"Renaming doc from '{source}' to {target}' not possible. Target already exist")
                pass
        else:
            # FIXME
            # ~ self.log.warning("FIXME: this might not be true in Windows systems")
            # ~ self.log.warning(f"Renaming doc from '{source}' to {target}' skipped. Source and target are the same")
            pass
        return rename

    def filename_delete(self, filepath):
        try:
            os.unlink(filepath)
            self.log.debug(f"File deleted: {filepath}")
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

    def unzip(self, target: str, install_dir) -> zipfile.ZipFile:
        """
        Unzip file to a given dir
        """
        zip_archive = zipfile.ZipFile(target, "r")
        zip_archive.extractall(path=install_dir)
        zip_archive.close()
        return zip_archive

    def zip_list(self, filepath: str) -> []:
        zip_archive = zipfile.ZipFile(filepath, "r")
        return zip_archive.namelist()

    def download_and_unzip(self, url:str, extract_to:str):
        """
        Download a zip file from a URL and extract it to a directory.

        Args:
            url (str): URL of the zip file to download
            extract_to (str): Directory to extract the files to (defaults to current directory)
        """
        try:
            self.log.debug(f"Downloading zip file from {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an error for bad status codes

            # Open the zip file from bytes
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                self.log.debug(f"Extracting files to {extract_to}")
                zip_ref.extractall(extract_to)

            self.log.debug("Download and extraction completed successfully!")
            return True

        except requests.exceptions.RequestException as e:
            self.log.error(f"Error downloading the file: {e}")
        except zipfile.BadZipFile:
            self.log.error("Error: The downloaded file is not a valid zip file")
        except Exception as e:
            self.log.error(f"An unexpected error occurred: {e}")
        return False

    def is_remote_path(self, path_or_uri: str) -> bool:
        # Convert to Gio.File using path or URI
        is_uri = "://" in path_or_uri
        file = Gio.File.new_for_uri(path_or_uri) if is_uri else Gio.File.new_for_path(path_or_uri)

        try:
            # Try to detect based on URI scheme
            scheme = file.get_uri_scheme()
            if scheme in REMOTE_SCHEMES:
                return True

            # Fallback: Ask the file system backend
            info = file.query_filesystem_info('filesystem::remote', None)
            return info.get_attribute_boolean('filesystem::remote')

        except Exception as e:
            print(f"Warning: Could not determine if file is remote: {e}")
            return False

    def check_remote_directory_sync(self, path, timeout_seconds=5):
        file = Gio.File.new_for_path(path)  # Use new_for_uri() for "sftp://..."
        cancellable = Gio.Cancellable()
        result = {"success": False, "error": None}

        def worker():
            try:
                info = file.query_info("standard::type", Gio.FileQueryInfoFlags.NONE, cancellable)
                result["success"] = True
            except GLib.Error as e:
                if cancellable.is_cancelled():
                    result["error"] = "Timeout"
                else:
                    result["error"] = str(e)

        thread = threading.Thread(target=worker)
        thread.start()

        # Wait with timeout
        thread.join(timeout_seconds)

        if thread.is_alive():
            cancellable.cancel()  # Cancel the operation
            thread.join()  # Wait for cleanup

        return result["success"], result["error"]

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

    # ~ fpath, fname = os.path.split(program)
    # ~ if fpath:
        # ~ if is_exe(program):
            # ~ return program
    # ~ else:
        # ~ for path in os.environ["PATH"].split(os.pathsep):
            # ~ path = path.strip('"')
            # ~ exe_file = os.path.join(path, program)
            # ~ if is_exe(exe_file):
                # ~ return exe_file
    # ~ return None
