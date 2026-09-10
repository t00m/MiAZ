"""
# File: ocr.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: reading text out of a document, with no frontend attached

This is what MiAZOCR does, separated from how it is asked for. The plugin
renders it as a menu entry, a language dialog and a toast; the command line
renders it as `miaz ocr`. Both call the functions here, so the two cannot
drift apart.

Nothing here imports Gtk, Adw or Gdk, and nothing here writes to the document
it reads: OCR produces a note, and the repository's copy of a document is the
document.
"""

import os
import shutil
import subprocess
import tempfile
from gettext import gettext as _

from MiAZ.backend.log import MiAZLog

log = MiAZLog('MiAZ.OCR')

# Command line tools this needs. ocrmypdf is mandatory (it wraps tesseract and
# ghostscript); without it there is no OCR to do. pdftotext is optional and
# only used to skip the OCR entirely when a PDF already carries its text.
REQUIRED_TOOLS = ('ocrmypdf',)

# How long a single document may take. Rasterising and recognising a long
# document is slow, and a scanner feeding a 200 page bundle is not unusual.
OCR_TIMEOUT = 1800

# Reading an existing text layer is not slow. If it is, something is wrong
# with the file and the OCR path is the better answer anyway.
TEXT_LAYER_TIMEOUT = 120


def missing_tools(tools=REQUIRED_TOOLS):
    """Which of `tools` are not on PATH, in the order given."""
    return [tool for tool in tools if shutil.which(tool) is None]


def available_languages():
    """The languages tesseract has data for, or English as a fallback.

    'osd' is dropped: it is orientation and script detection, not a language,
    and offering it in a language list is offering a wrong answer.
    """
    try:
        result = subprocess.run(['tesseract', '--list-langs'],
                                capture_output=True, text=True, timeout=10)
        # The first line is a header ("List of available languages (n):").
        langs = [line.strip() for line in result.stdout.splitlines()[1:]
                 if line.strip() and line.strip() != 'osd']
        if langs:
            return sorted(langs)
    except (OSError, subprocess.SubprocessError) as error:
        log.debug(f"Could not list tesseract languages: {error}")
    return ['eng']


def default_language(langs, preferred=None):
    """The language to start from: what was chosen last, else English.

    `preferred` is whatever the plugin remembered. It is ignored when the
    installed language data no longer includes it, which is what happens when
    a tesseract language pack is removed.
    """
    if preferred and preferred in langs:
        return preferred
    if 'eng' in langs:
        return 'eng'
    return langs[0] if langs else 'eng'


def extract_text(source, lang='eng', force=False, logger=None):
    """The text of `source`, read from its text layer or by OCR.

    Returns '' when there is nothing to read, which covers a document that is
    not there, one that is not a PDF, and a scan the engine could make nothing
    of. None of those is exceptional enough to raise: a batch of documents has
    to survive one bad file.

    `force` skips the text layer and recognises the page as an image, which is
    what a PDF with a wrong or partial text layer needs.
    """
    logger = logger or log
    if not os.path.isfile(source):
        logger.warning(f"Nothing to extract, no such file: {source}")
        return ''

    if not force:
        text = _read_text_layer(source, logger)
        if text:
            return text

    return _run_ocr(source, lang, force, logger)


def _read_text_layer(source, logger):
    """What pdftotext can read without recognising anything, or ''.

    Most documents in a repository were born digital and already carry their
    text. Rasterising one of those to read what it is already telling you
    costs seconds per document and can only make the text worse.
    """
    if shutil.which('pdftotext') is None:
        return ''
    try:
        result = subprocess.run(['pdftotext', source, '-'],
                                capture_output=True, text=True,
                                timeout=TEXT_LAYER_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as error:
        logger.debug(f"pdftotext failed for '{source}': {error}")
        return ''
    if result.returncode == 0 and result.stdout.strip():
        logger.debug(f"Text layer read from '{source}', no OCR needed")
        return result.stdout
    return ''


def _run_ocr(source, lang, force, logger):
    """Recognise the pages of `source` and return what was read.

    ocrmypdf insists on writing a PDF, so it writes one into a temporary
    directory that is thrown away, and the text is taken from the sidecar it
    writes alongside. The document itself is only ever read.
    """
    if missing_tools():
        logger.error(f"Cannot OCR '{source}': "
                     f"{', '.join(missing_tools())} not installed")
        return ''
    with tempfile.TemporaryDirectory(prefix='miaz-ocr-') as tmpdir:
        sidecar = os.path.join(tmpdir, 'out.txt')
        command = ['ocrmypdf', '-l', lang, '--sidecar', sidecar,
                   '--force-ocr' if force else '--skip-text',
                   source, os.path.join(tmpdir, 'out.pdf')]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=OCR_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as error:
            logger.error(f"ocrmypdf failed for '{source}': {error}")
            return ''
        if result.returncode != 0:
            logger.error(f"ocrmypdf error for '{source}': "
                         f"{result.stderr.strip()}")
        if os.path.exists(sidecar):
            with open(sidecar, 'r', encoding='utf-8') as handler:
                return handler.read()
    return ''


def note_body(text, lang):
    """The note an extraction becomes.

    The language is written into it because text recognised as the wrong
    language is wrong in ways that read like a bad scan, and a note that does
    not say how it was made cannot be judged later.
    """
    return _('# OCR extraction\n\nLanguage: {lang}\n\n{text}').format(
        lang=lang, text=(text or '').strip())
