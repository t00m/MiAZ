
"""
# File: util.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: useful often low-level methods for this app
"""

import os
import re
import ast
import sys
import json
import gettext
import shutil
import tempfile
import threading
import functools
import subprocess
import mimetypes
import struct
import zipfile
import zlib
from datetime import datetime

from gi.repository import Gio
from gi.repository import GObject

from MiAZ.backend.log import MiAZLog

mimetypes.init()

REMOTE_SCHEMES = {
    "sftp", "smb", "ftp", "http", "https", "dav", "davs", "afp", "mtp", "obex", "ssh"
}

# The date MiAZ writes when it cannot read one from the document. It is a real
# date, so the entry validator, the calendar and the sort order take it without
# a special case, and it sorts last, so unknown dates group at the end of the
# workspace instead of hiding among the real ones.
UNKNOWN_DATE = '99991231'

# Years outside this range are not document dates, they are amounts, invoice
# numbers or account numbers that happen to be eight digits long.
YEAR_MIN = 1900
YEAR_MAX = 2100

# YYYY sep MM sep DD, or the same with no separator at all. The lookbehind and
# the {2} groups keep this from starting halfway through a longer run of digits.
_RE_DATE_YEAR_FIRST = re.compile(r'(?<!\d)(\d{4})([-_./])(\d{1,2})\2(\d{1,2})(?!\d)')
# D[D] sep M[M] sep YYYY, the year last. Which of the first two is the day is
# not written down, so the caller decides whether the reading is unambiguous.
_RE_DATE_YEAR_LAST = re.compile(r'(?<!\d)(\d{1,2})([-_./])(\d{1,2})\2(\d{4})(?!\d)')
# Eight solid digits: either YYYYMMDD or DDMMYYYY/MMDDYYYY.
_RE_DATE_SOLID = re.compile(r'(?<!\d)(\d{8})')

# A PDF Info dictionary date: /CreationDate (D:YYYYMMDDHHmmSS+HH'mm'). The D:
# prefix is required by the spec and omitted by plenty of generators anyway, and
# everything after the day is optional. The offset is deliberately ignored: the
# string already carries local time, and that is the day the document is dated.
_RE_PDF_INFO_DATE = re.compile(rb"/(?:CreationDate|CreateDate)\s*\(\s*D?:?\s*(\d{8})")
# The same date in the XMP packet, which many PDFs carry instead. JPEG, TIFF
# and PNG embed XMP as plain XML too, so one scan serves all of them.
_RE_PDF_XMP_DATE = re.compile(rb"<xmp:CreateDate>\s*(\d{4})-(\d{2})-(\d{2})")
# Office documents are ZIPs: OOXML keeps dcterms:created in docProps/core.xml,
# OpenDocument keeps meta:creation-date in meta.xml.
_RE_ZIP_DOC_DATE = re.compile(rb"<(?:dcterms:created|meta:creation-date)[^>]*>"
                              rb"\s*(\d{4})-(\d{2})-(\d{2})")
_ZIP_META_MEMBERS = ('docProps/core.xml', 'meta.xml')
_ZIP_MAGIC = b'PK\x03\x04'

# Reading a whole PDF to scan it is fine for a document and silly for a 500 MB
# scan, and the metadata sits near one end or the other, never in the middle of
# the page content. Files above the limit are read as a head and a tail.
_PDF_SCAN_WHOLE = 64 * 1024 * 1024
_PDF_SCAN_EDGE = 8 * 1024 * 1024
# Decompressing streams is the slow path, and it only runs when the plain scan
# found nothing. These keep it from turning into a scan of every embedded image.
_PDF_MAX_STREAMS = 64
_PDF_MAX_STREAM_BYTES = 4 * 1024 * 1024


def _as_date(year: int, month: int, day: int) -> str:
    """Return YYYYMMDD when the three numbers are a date in range, else ''."""
    if not YEAR_MIN <= year <= YEAR_MAX:
        return ''
    try:
        return datetime(year, month, day).strftime('%Y%m%d')
    except ValueError:
        return ''


def _exif_original_date(raw: bytes) -> str:
    """Return YYYYMMDD from EXIF DateTimeOriginal, or '' when there is none.

    Walks the TIFF block by hand rather than through Pillow, which is not a
    dependency of MiAZ. Only two tags are followed: 0x8769, the pointer to the
    Exif sub-IFD, and 0x9003, DateTimeOriginal, whose value is the ASCII string
    "YYYY:MM:DD HH:MM:SS". Anything unexpected returns '' rather than raising:
    a malformed photo must not stop a rename.
    """
    start = raw.find(b'Exif\x00\x00')
    if start < 0:
        return ''
    tiff = start + 6
    order = raw[tiff:tiff + 2]
    if order == b'II':
        endian = '<'
    elif order == b'MM':
        endian = '>'
    else:
        return ''
    try:
        offset, = struct.unpack_from(endian + 'I', raw, tiff + 4)
        for tag, value in _exif_entries(raw, tiff, offset, endian):
            # 0x8769 points at the sub-IFD, which is where 0x9003 lives.
            if tag != 0x8769:
                continue
            for sub_tag, sub_value in _exif_entries(raw, tiff, value, endian):
                if sub_tag != 0x9003:
                    continue
                stamp = raw[tiff + sub_value:tiff + sub_value + 19].decode('ascii', 'ignore')
                return _as_date(int(stamp[0:4]), int(stamp[5:7]), int(stamp[8:10]))
    except (struct.error, ValueError, IndexError):
        return ''
    return ''


def _exif_entries(raw: bytes, tiff: int, offset: int, endian: str):
    """Yield (tag, value) for each entry of the IFD at this offset.

    The value is the raw 4-byte field, which for the two tags of interest is
    either an offset (0x8769, 0x9003) or nothing worth reading.
    """
    at = tiff + offset
    if at + 2 > len(raw):
        return
    count, = struct.unpack_from(endian + 'H', raw, at)
    for index in range(count):
        entry = at + 2 + index * 12
        if entry + 12 > len(raw):
            return
        tag, = struct.unpack_from(endian + 'H', raw, entry)
        value, = struct.unpack_from(endian + 'I', raw, entry + 8)
        yield tag, value


def _as_unambiguous_date(first: int, second: int, year: int) -> str:
    """Return YYYYMMDD for a year-last date, or '' when the order is a guess.

    With the year last, 03/04/2024 is 3 April to most of the world and 4 March
    to the United States, and the filename does not say which. MiAZ reads such
    a date only when one of the two numbers is over 12, which leaves a single
    reading; otherwise it reports nothing rather than a date that may be wrong.
    """
    day_first = _as_date(year, second, first)
    month_first = _as_date(year, first, second)
    if day_first and month_first:
        return ''
    return day_first or month_first


def date_is_valid(value: str) -> bool:
    """True when value is a date in the eight-digit form a filename carries.

    strptime('%Y%m%d') is not that test. It takes one or two digits for month
    and for day, so '202613' reads as 3 January 2026 and '2026131' as 31
    January 2026. Typing a date passes through both, so the rename dialog kept
    accepting a half-typed one and writing the completed date back into the
    field the user was still in.

    The check is pure: no widget, no calendar, no message. Callers that have to
    show the verdict do the showing themselves.
    """
    if len(value) != 8 or not value.isdigit():
        return False
    try:
        datetime.strptime(value, '%Y%m%d')
        return True
    except ValueError:
        return False


def check_zip_members(names, install_dir: str) -> None:
    """Raise RuntimeError if any member would be written outside install_dir.

    CPython's zipfile already strips '..' and leading separators, so a member
    named '../evil' is quietly rewritten to sit inside the target rather than
    escaping. Nothing is written outside either way, but the file lands
    somewhere the archive did not ask for and nobody is told. Refusing says so.

    It is also the check that has to exist if extraction ever moves to tarfile,
    which does not sanitise anything and really does escape.
    """
    target_path = os.path.realpath(install_dir)
    for member in names:
        member_path = os.path.realpath(os.path.join(install_dir, member))
        if member_path != target_path and not member_path.startswith(target_path + os.sep):
            raise RuntimeError(
                f"Refusing to extract '{member}' outside target directory")


def humanize_value(gtype_name: str, description: str) -> str:
    """Return the localized display label for a controlled-vocabulary value.

    The stored value and the on-disk filename keep the original code; only the
    label shown to the user is translated:

      - Country: through the iso-codes 'iso_3166-1' gettext domain, so every
        language iso-codes ships is covered with no per-language work here.
      - Group / Purpose: through the app 'miaz' catalog (their default labels
        are listed in vocabulary.py so they are extracted for translation).
      - Anything else (user-typed values like people or concepts): unchanged.

    The original string is always the fallback, so untranslated or user
    customized values display as-is.
    """
    if not description:
        return description
    if gtype_name == 'Country':
        return gettext.dgettext('iso_3166-1', description)
    if gtype_name in ('Group', 'Purpose'):
        return gettext.dgettext('miaz', description)
    return description


def atomic_json_save(filepath: str, adict: dict) -> None:
    """Write adict as JSON to filepath atomically.

    Write to a temporary file in the same directory, flush it to disk, then
    os.replace() it onto the target. os.replace is atomic on the same
    filesystem, so a crash mid-write never leaves a half-written file. Module
    level so callers without the util service (e.g. repository bootstrap) can
    reuse the same implementation.
    """
    dirpath = os.path.dirname(filepath) or '.'
    fd, tmppath = tempfile.mkstemp(dir=dirpath, prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fout:
            json.dump(adict, fout, sort_keys=True, indent=4)
            fout.flush()
            os.fsync(fout.fileno())
        os.replace(tmppath, filepath)
    except BaseException:
        # Never leave the temp file behind on failure.
        try:
            os.unlink(tmppath)
        except OSError:
            pass
        raise


def clean_temp_dir(dirpath: str) -> int:
    """Delete everything inside dirpath, keeping the directory itself.

    var/tmp holds files that only make sense while the session that wrote them
    is running: scans waiting to be imported, exports being built, unzipped
    plugin bundles. Anything still there at startup is a leftover from a crash
    or from a workflow the user abandoned, so the directory is emptied.

    An entry that cannot be removed is logged and skipped: a locked or
    read-only leftover must never stop the application from starting. A
    missing directory is not an error either, it is created right after.
    Returns the number of entries removed.
    """
    log = MiAZLog('MiAZ.Util')
    removed = 0
    try:
        entries = list(os.scandir(dirpath))
    except FileNotFoundError:
        return 0
    except OSError as error:
        log.warning(f"Could not read temporary directory {dirpath}: {error}")
        return 0

    for entry in entries:
        try:
            # follow_symlinks=False: a symlink to a directory is unlinked, its
            # target is left alone.
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path)
            else:
                os.unlink(entry.path)
            removed += 1
        except OSError as error:
            log.warning(f"Could not delete temporary entry {entry.path}: {error}")
    return removed


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
        elif isinstance(node, ast.Tuple):
            # A menu entry is a tuple: ('doc', _('Create a note'), ['<Ctrl>N'])
            return tuple(self._safe_eval(elt) for elt in node.elts)
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
    __gsignals__ = {
        'filename-added':    (GObject.SignalFlags.RUN_LAST, GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,)),
        'filename-deleted':  (GObject.SignalFlags.RUN_LAST, GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,)),
        'filename-renamed':  (GObject.SignalFlags.RUN_LAST, GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
    }

    def __init__(self, app):
        super().__init__()
        self.log = MiAZLog('MiAZ.Backend.Util')
        self.app = app

    def extract_variable_from_python_module(self, filepath, variable_name):
        with open(filepath, "r", encoding='utf-8') as f:
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
            subprocess.Popen(['xdg-open', dirpath])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', dirpath])
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
        with open(filepath, encoding='utf-8') as fin:
            adict = json.load(fin)
        return adict

    def json_save(self, filepath: str, adict: {}) -> {}:
        """Save dictionary into a file in json format, atomically."""
        atomic_json_save(filepath, adict)

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
        parts = filename.split('-')
        if len(parts) > 7:
            # Excess parts most likely contain hyphens in Concept or SentTo;
            # merge them back into the last field (SentTo)
            parts[6] = '-'.join(parts[6:])
            parts = parts[:7]
        return parts

    def get_files(self, dirpath: str) -> []:
        """Get all files from a given directory.

        os.scandir's entry.is_file() uses the directory-entry type reported by
        the OS (d_type) when available, so most files skip a separate stat()
        syscall; glob.glob + os.path.isfile always stats every entry.
        """
        with os.scandir(dirpath) as it:
            return sorted(e.path for e in it if not e.name.startswith('.') and e.is_file())

    def get_files_recursively(self, root_dir: str) -> set:
        """Get documents from a given directory recursively
        Avoid hidden documents and documents from hidden directories.
        """
        documents = set()
        for root, dirs, files in os.walk(os.path.abspath(root_dir), topdown=True):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.startswith('.'):
                    documents.add(os.path.join(root, f))
        return documents

    def filename_get_modification_date(self, filepath: str) -> datetime:
        """When the file was last written, which is not when the document is
        dated.

        It was called filename_get_creation_date, and the name was a trap: it
        reads st_mtime, so for a bank statement downloaded today it answers
        today. filename_guess_date used to end its chain here, which is how
        every document without a date in its name came to be filed under the
        day it was imported. Use dates_from_metadata for a document date.

        Nothing in MiAZ calls it, and that is not a reason to remove it: it is
        a public method on a service plugins are given in full, and a plugin
        out of tree is free to ask when a file was written. Two analyses have
        now listed it as dead code, so this paragraph is here to stop a third.
        """
        lastmod = os.stat(filepath).st_mtime
        return datetime.fromtimestamp(lastmod)

    def filename_get_mimetype(self, filepath: str) -> str:
        mimetype, val = Gio.content_type_guess(filepath, data=None)
        return mimetype

    def dates_from_text(self, text: str) -> []:
        """Return every unambiguous date in a piece of text, as YYYYMMDD.

        The dates come back in the order they appear. A date whose field order
        cannot be told from the text itself (03/04/2024) is left out, as is a
        two-digit year, so what comes back is read rather than guessed.
        """
        if not text:
            return []
        found = []
        for match in _RE_DATE_YEAR_FIRST.finditer(text):
            year, _sep, month, day = match.groups()
            sdate = _as_date(int(year), int(month), int(day))
            if sdate:
                found.append((match.start(), match.end(), sdate))
        for match in _RE_DATE_YEAR_LAST.finditer(text):
            first, _sep, second, year = match.groups()
            sdate = _as_unambiguous_date(int(first), int(second), int(year))
            if sdate:
                found.append((match.start(), match.end(), sdate))
        for match in _RE_DATE_SOLID.finditer(text):
            run = match.group(1)
            sdate = (_as_date(int(run[:4]), int(run[4:6]), int(run[6:8]))
                     or _as_unambiguous_date(int(run[:2]), int(run[2:4]), int(run[4:])))
            if sdate:
                found.append((match.start(), match.end(), sdate))
        dates = []
        read_up_to = -1
        for start, end, sdate in sorted(found):
            if start < read_up_to:
                # These same digits were already read as a date.
                continue
            dates.append(sdate)
            read_up_to = end
        return dates

    def filename_guess_date(self, filepath: str, concept_hint: str = '') -> str:
        """Return a YYYYMMDD string read from the document, or UNKNOWN_DATE.

        Order: (1) the earliest creation date the file's own metadata carries;
        (2) the first unambiguous date in the concept hint, which is where
        filename_normalize keeps the original filename.

        Metadata comes first because a filename is not a reliable place to find
        a date. Invoice and policy numbers are digit runs that pass every
        shape check a date parser can apply: 24071988 inside RG240719880042
        reads as a perfectly valid 24 July 1988. Metadata cannot fail that way,
        because a field named CreationDate holds a date or holds nothing.

        Measured against 1257 documents whose dates their owner had chosen by
        hand, the metadata date agreed 46% of the time and the filename date
        26%, and where both existed and disagreed the metadata was right more
        often. Neither is authoritative, which is why both rename paths preview
        the result before applying it.

        The file mtime used to close the chain. It was dropped because it is not
        a fact about the document: a bank statement downloaded today has today's
        mtime, so every document that did not carry a date in its name was filed
        under the day it was imported. UNKNOWN_DATE says "not read" instead.
        """
        dates = self.dates_from_metadata(filepath) or self.dates_from_text(concept_hint)
        return dates[0] if dates else UNKNOWN_DATE

    def dates_from_metadata(self, filepath: str) -> []:
        """Return the creation dates the file itself carries, as YYYYMMDD.

        At most one entry, the earliest found, so the caller can treat this the
        same way as dates_from_text. Reading it needs no third-party library on
        purpose: this used to go through pypdf and Pillow behind `except
        ImportError: return ''`, and since neither is a dependency of MiAZ the
        whole branch was dead on any normal install. The date silently became
        the file mtime, which is the day the document was downloaded.
        """
        mime = self.filename_get_mimetype(filepath) or ''
        try:
            if mime == 'application/pdf':
                dates = self._dates_from_pdf(filepath)
            elif mime.startswith('image/'):
                dates = self._dates_from_image(filepath)
            elif self._is_zip(filepath):
                # Every OOXML and OpenDocument variant, found by magic number
                # rather than by listing a dozen mime types.
                dates = self._dates_from_zip_document(filepath)
            else:
                return []
        except OSError as error:
            self.log.debug(f"Could not read {filepath} for its date: {error}")
            return []
        return [min(dates)] if dates else []

    def _read_for_scan(self, filepath: str) -> bytes:
        """The bytes worth scanning for metadata: all of them, unless the file
        is big enough that reading it would be silly."""
        size = os.path.getsize(filepath)
        with open(filepath, 'rb') as fd:
            if size <= _PDF_SCAN_WHOLE:
                return fd.read()
            head = fd.read(_PDF_SCAN_EDGE)
            fd.seek(size - _PDF_SCAN_EDGE)
            return head + fd.read(_PDF_SCAN_EDGE)

    def _pdf_dates_in(self, raw: bytes) -> []:
        dates = []
        for match in _RE_PDF_INFO_DATE.finditer(raw):
            stamp = match.group(1).decode('ascii', 'ignore')
            sdate = _as_date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8]))
            if sdate:
                dates.append(sdate)
        for match in _RE_PDF_XMP_DATE.finditer(raw):
            year, month, day = (int(part) for part in match.groups())
            sdate = _as_date(year, month, day)
            if sdate:
                dates.append(sdate)
        return dates

    def _dates_from_pdf(self, filepath: str) -> []:
        """Creation dates from the PDF Info dictionary and the XMP packet."""
        raw = self._read_for_scan(filepath)
        dates = self._pdf_dates_in(raw)
        if dates:
            return dates
        # Nothing in the plain bytes. The XMP packet is normally Flate
        # compressed, so inflate what streams there are and look again.
        for count, match in enumerate(re.finditer(rb'stream\r?\n', raw)):
            if count >= _PDF_MAX_STREAMS:
                break
            start = match.end()
            end = raw.find(b'endstream', start)
            if end < 0 or end - start > _PDF_MAX_STREAM_BYTES:
                continue
            try:
                # decompressobj tolerates the truncated tail of a stream that
                # the head/tail read cut in half; decompress does not.
                plain = zlib.decompressobj().decompress(raw[start:end])
            except zlib.error:
                continue
            dates = self._pdf_dates_in(plain)
            if dates:
                return dates
        return []

    def _is_zip(self, filepath: str) -> bool:
        with open(filepath, 'rb') as fd:
            return fd.read(len(_ZIP_MAGIC)) == _ZIP_MAGIC

    def _dates_from_zip_document(self, filepath: str) -> []:
        """The creation date of an OOXML or OpenDocument file.

        Only the one metadata member of each format is read, so a plain ZIP is
        two lookups and no decompression.

        A document made from a template inherits the template's created date,
        which can be years off. It is still a date about the document rather
        than about when it was downloaded, and the rename preview shows it
        before anything is applied.
        """
        dates = []
        try:
            with zipfile.ZipFile(filepath) as archive:
                for member in _ZIP_META_MEMBERS:
                    try:
                        raw = archive.read(member)
                    except KeyError:
                        continue
                    for match in _RE_ZIP_DOC_DATE.finditer(raw):
                        year, month, day = (int(part) for part in match.groups())
                        sdate = _as_date(year, month, day)
                        if sdate:
                            dates.append(sdate)
        except (zipfile.BadZipFile, RuntimeError) as error:
            self.log.debug(f"Could not read {filepath} as an office document: {error}")
        return dates

    def _dates_from_image(self, filepath: str) -> []:
        """EXIF DateTimeOriginal, plus an XMP creation date if one is embedded.

        JPEG, TIFF and PNG all carry XMP as plain XML, so the same scan that
        reads a PDF's packet reads theirs.
        """
        raw = self._read_for_scan(filepath)
        dates = []
        stamp = _exif_original_date(raw)
        if stamp:
            dates.append(stamp)
        for match in _RE_PDF_XMP_DATE.finditer(raw):
            year, month, day = (int(part) for part in match.groups())
            sdate = _as_date(year, month, day)
            if sdate:
                dates.append(sdate)
        return dates

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

    def filename_upper(self, filename: str) -> str:
        """Uppercase a filename's name part, keeping the extension lowercase.

        MiAZ stores document filenames with the seven fields in uppercase and a
        lowercase extension. This enforces that casing for any rename target.
        """
        name, ext = self.filename_details(filename)
        if ext:
            return f"{name.upper()}.{ext}"
        return name.upper()

    def filename_is_normalized(self, name: str) -> bool:
        return len(name.split('-')) == 7

    def filename_validate(self, doc: str) -> bool:
        # A MiAZ filename has exactly 7 non-empty fields.
        fields = self.get_fields(doc)
        return len(fields) == 7 and all(field for field in fields)

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
        key = str(key).strip().replace('-', '_').replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', key)

    def _rename_target(self, target: str, upper=True) -> str:
        """The path filename_rename would really move to.

        MiAZ stores document filenames uppercase (with a lowercase extension),
        so every rename forces the target to that casing. Callers that rename a
        non-document file (e.g. a zip export) pass upper=False to opt out.
        """
        if not upper:
            return target
        directory = os.path.dirname(target)
        return os.path.join(directory, self.filename_upper(os.path.basename(target)))

    def filename_rename_needed(self, source, target, upper=True) -> bool:
        """False when source and target name the same file.

        Callers use this to tell "nothing to rename" apart from a rename that
        failed: filename_rename returns False for both, and the difference
        matters to anything that has work to do alongside the rename.
        """
        return source != self._rename_target(target, upper)

    def filename_rename(self, source, target, upper=True) -> bool:
        target = self._rename_target(target, upper)
        rename = False
        # Identical source and target mean there is nothing to do, and that is
        # common enough (a rename dialog closed without a field change) not to
        # be worth logging. On Linux the comparison is case-sensitive, which is
        # what we want; MiAZ targets Linux for the 0.2 release.
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
                # Target already exists. Do not overwrite it silently; the
                # caller sees rename=False and surfaces the skip (mass rename
                # counts skipped files in a toast).
                self.log.warning(
                    f"Rename skipped: target already exists: '{target}'")
        return rename

    def filename_delete(self, filepaths: set):
        self.log.debug(f"Deleting {len(filepaths)} documents")
        for filepath in filepaths:
            try:
                os.unlink(filepath)
                self.log.debug(f"Deleted: {filepath}")
            except OSError as error:
                self.log.error(f"Could not delete {filepath}: {error}")
        self.emit('filename-deleted', filepaths)

    def filename_import(self, source: str, target: str):
        """Import a file into the repository: copy it under the normalized
        target name, then announce it with filename-added."""
        self.filename_copy(source, target)
        self.emit('filename-added', target)

    def filename_export(self, source: str, target: str) -> bool:
        return self.filename_copy(source, target)

    def filename_copy(self, source, target, overwrite=True) -> bool:
        """Copy source to target. True when the file was written.

        The return value is what lets a caller count what it exported: a
        failure used to reach the log and nowhere else, so the export plugin
        reported success for documents it had never copied.
        """
        if source == target:
            self.log.error("Source and Target are the same. Skip copy")
            return False
        if not overwrite and os.path.exists(target):
            self.log.debug(f"Target file {target} exists. Copy operation skipped")
            return False
        try:
            # preserve metadata
            shutil.copy2(source, target)
            self.log.info(f"{source} copied to {target}")
            return True
        except Exception as error:
            self.log.error(error)
            return False

    def filename_date_human(self, value: str = '') -> str:
        if not date_is_valid(value):
            return ''
        return datetime.strptime(value, "%Y%m%d").strftime("%A, %B %d %Y")

    def filename_date_human_simple(self, value: str = ''):
        if not date_is_valid(value):
            return None
        return datetime.strptime(value, "%Y%m%d").strftime("%d/%m/%Y")

    def filename_display(self, filepath):
        if sys.platform in ['linux', 'linux2']:
            subprocess.Popen(['xdg-open', filepath])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', filepath])
        elif sys.platform in ['win32', 'cygwin', 'msys']:
            os.startfile(filepath)

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
        # First day of the month nm calendar months before adate. A fixed
        # 30-day delta drifts at month boundaries: on the 31st, 30 days back
        # stays in the same month (so "past month" on Jul 31 wrongly landed on
        # Jul 1 and hid June). Compute the month directly instead.
        month = adate.month - nm
        year = adate.year
        while month <= 0:
            month += 12
            year -= 1
        return datetime.strptime("%04d%02d01" % (year, month), "%Y%m%d")

    def since_date_last_six_months(self, adate: datetime) -> datetime:
        return self.since_date_last_n_months(adate, 6)

    def datetime_to_string(self, adate: datetime) -> str:
        return adate.strftime("%Y%m%d")

    @functools.lru_cache(maxsize=4096)
    def string_to_datetime(self, adate: str) -> datetime:
        try:
            return datetime.strptime(adate, "%Y%m%d").date()
        except ValueError:
            return None

    def zip(self, filename: str, directory: str, exclude: tuple = ()):
        """Zip directory into a file, skipping any entry named in `exclude`.

        `exclude` matches on the entry name at any depth, so ('.git',) drops
        that directory wherever it sits. Written out here rather than through
        shutil.make_archive, which archives everything and takes no exclusion.

        Returns the path of the archive, which always ends in .zip.
        """
        # ~ self.log.debug(f"Target: {filename}")
        sourcename = os.path.basename(filename)
        dot = sourcename.find('.')
        if dot == -1:
            basename = sourcename
        else:
            basename = sourcename[:dot]
        sourcedir = os.path.dirname(filename)
        target = os.path.join(sourcedir, basename) + '.zip'
        skip = set(exclude)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for root, dirs, files in os.walk(directory):
                dirs[:] = sorted(name for name in dirs if name not in skip)
                for name in dirs:
                    # Written explicitly so an empty directory survives the
                    # round trip, which make_archive also did.
                    path = os.path.join(root, name)
                    archive.write(path, os.path.relpath(path, directory))
                for name in sorted(files):
                    if name in skip:
                        continue
                    path = os.path.join(root, name)
                    archive.write(path, os.path.relpath(path, directory))
        return target

    def timestamp(self):
        """Get timestamp (YYYYmmdd_hhmmss)"""
        now = datetime.now()
        return "%4d%02d%02d_%02d%02d%02d" % (now.year, now.month, now.day,
                                             now.hour, now.minute, now.second)

    def unzip(self, target: str, install_dir) -> zipfile.ZipFile:
        """Extract an archive into install_dir, refusing anything that would
        land outside it. See check_zip_members for why.

        Returns the (closed) ZipFile, because callers read namelist() off it.
        """
        with zipfile.ZipFile(target, "r") as zip_archive:
            check_zip_members(zip_archive.namelist(), install_dir)
            zip_archive.extractall(path=install_dir)
        return zip_archive

    def zip_list(self, filepath: str) -> []:
        with zipfile.ZipFile(filepath, "r") as z:
            return z.namelist()

    @staticmethod
    def get_install_mode() -> str:
        """Return how this MiAZ instance is being run.

        One of:
          'flatpak'  : inside a Flatpak sandbox
          'snap'     : inside a Snap confinement
          'appimage' : from an AppImage FUSE mount
          'system'   : installed under /usr or /opt (system-wide)
          'user'     : installed under the user's home (e.g. ~/.local)
          'source'   : running from a source checkout (development)
        """
        if os.environ.get('FLATPAK_ID') or os.path.exists('/.flatpak-info'):
            return 'flatpak'
        if os.environ.get('SNAP') or os.environ.get('SNAP_NAME'):
            return 'snap'
        if os.environ.get('APPIMAGE') or os.environ.get('APPDIR'):
            return 'appimage'

        # _buildconfig.py is generated by Meson at install time, so its
        # absence means we are running from a source checkout.
        try:
            from MiAZ import _buildconfig  # noqa: F401
        except ImportError:
            return 'source'

        try:
            from MiAZ.env import ENV
            pkgdatadir = os.path.realpath(ENV['APP'].get('PGKDATADIR', '') or '')
        except Exception:
            pkgdatadir = ''
        home = os.path.realpath(os.path.expanduser('~'))

        if pkgdatadir.startswith(('/usr/', '/opt/')):
            return 'system'
        if home and pkgdatadir.startswith(home + os.sep):
            return 'user'
        return 'source'

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
            self.log.warning(f"Could not determine if file is remote: {e}")
            return False

    def check_remote_directory_sync(self, path, timeout_seconds=5):
        file = Gio.File.new_for_path(path)  # Use new_for_uri() for "sftp://..."
        cancellable = Gio.Cancellable()
        result = {"success": False, "error": None}

        def worker():
            try:
                info = file.query_info("standard::type", Gio.FileQueryInfoFlags.NONE, cancellable)
                result["success"] = True
            except Exception as e:
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
