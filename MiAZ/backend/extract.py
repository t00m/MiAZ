
"""
# File: extract.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Local, non-AI text extraction and vocabulary matching for the
#              rename dialog's "Detect" menu. No GTK/Adw/Gdk imports (backend
#              layer): only pdftotext/pdftoppm (poppler-utils) and tesseract,
#              which are core package dependencies (see miaz.spec,
#              debian/control), are shelled out to. No AI/network involved.
"""

import shutil
import pathlib
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Literal

ExtractMethod = Literal['pdftotext', 'tesseract', 'plain', 'none']

# Below this many characters, extracted text is not worth matching against
# the repository vocabulary: a title page or a mostly-blank scan produces a
# handful of characters that would otherwise match by pure chance.
MIN_USEFUL_TEXT_CHARS = 200

# poppler-utils (pdftotext, pdftoppm) and tesseract are core dependencies,
# declared as hard Requires/Depends in the deb and rpm packages. This list is
# still checked at call time: a manual/dev install, or an AppImage (which has
# no dependency resolution of its own), can still be missing them.
REQUIRED_TOOLS = ('pdftotext', 'pdftoppm', 'tesseract')


@dataclass
class ExtractResult:
    text: str
    method: ExtractMethod

    @property
    def is_useful(self) -> bool:
        return (
            self.method != 'none'
            and len(self.text) >= MIN_USEFUL_TEXT_CHARS
            and any(c.isalpha() for c in self.text)
        )


def missing_tools():
    """Required command line tools not found on PATH, or [] when all are."""
    return [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]


def extract(path) -> ExtractResult:
    """Try local text extraction: pdftotext, falling back to OCR for a PDF
    with no text layer; tesseract directly for an image; the file itself for
    plain text. Caller checks is_useful before trusting the result."""
    path = pathlib.Path(path)
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        text = _pdftotext(path)
        if text and len(text) >= MIN_USEFUL_TEXT_CHARS:
            return ExtractResult(text, 'pdftotext')
        text = _ocr_pdf(path)
        return ExtractResult(text, 'tesseract' if text else 'none')
    if suffix in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp'}:
        return ExtractResult(_ocr_image(path), 'tesseract')
    if suffix in {'.txt', '.md', '.markdown'}:
        try:
            return ExtractResult(path.read_text(errors='replace'), 'plain')
        except Exception:
            return ExtractResult('', 'none')
    return ExtractResult('', 'none')


def match_vocab(text: str, used: dict) -> str:
    """The key of the repository's used vocabulary (key -> description) whose
    description occurs in text, or '' when none does.

    Descriptions are checked longest first, so a specific match ("Bank of
    America") wins over a shorter, coincidental one ("America") that also
    happens to be a used value. Matching is a plain case-insensitive
    substring test: good enough for a scanned invoice's letterhead or a bank
    statement's issuer line, not a general NLP match.
    """
    if not text or not used:
        return ''
    haystack = text.upper()
    for key, description in sorted(used.items(), key=lambda kv: -len(kv[1] or '')):
        needle = (description or '').strip().upper()
        if needle and needle in haystack:
            return key
    return ''


def _pdftotext(path: pathlib.Path) -> str:
    if not shutil.which('pdftotext'):
        return ''
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', '-q', str(path), '-'],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return result.stdout
    except Exception:
        return ''


def _ocr_image(path: pathlib.Path) -> str:
    if not shutil.which('tesseract'):
        return ''
    try:
        result = subprocess.run(
            ['tesseract', str(path), '-', '-l', 'eng'],
            capture_output=True, text=True, timeout=60, check=False,
        )
        return result.stdout
    except Exception:
        return ''


def _ocr_pdf(path: pathlib.Path) -> str:
    if not (shutil.which('pdftoppm') and shutil.which('tesseract')):
        return ''
    with tempfile.TemporaryDirectory() as td:
        out_prefix = pathlib.Path(td) / 'page'
        try:
            subprocess.run(
                ['pdftoppm', '-r', '200', str(path), str(out_prefix)],
                timeout=60, check=False,
            )
        except Exception:
            return ''
        pages = sorted(pathlib.Path(td).glob('page-*.ppm'))
        chunks = [_ocr_image(img) for img in pages[:10]]
        return '\n'.join(chunks)
