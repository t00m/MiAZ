#!/usr/bin/python3

"""
Tests for the OCR work, which has no frontend in it.

MiAZOCR used to keep the extraction inside the plugin class, tangled with the
dialogs that asked for the language and the toasts that reported the result.
Moving it to the backend is what lets `miaz ocr` and the menu entry run the
same code instead of two copies that drift.

The PDFs here are written by hand rather than taken from a fixture directory:
a one page PDF with a real text layer is a few hundred bytes, and building it
in the test keeps what is being extracted visible next to the assertion.
"""

import os
import shutil

import pytest

from MiAZ.backend.ocr import (REQUIRED_TOOLS, available_languages,
                              extract_text, missing_tools, note_body)


def write_pdf(path, text):
    """A one page PDF carrying `text` as a real text layer."""
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n").encode()
    path.write_bytes(bytes(out))
    return str(path)


needs_pdftotext = pytest.mark.skipif(
    shutil.which('pdftotext') is None, reason='pdftotext is not installed')
needs_ocrmypdf = pytest.mark.skipif(
    shutil.which('ocrmypdf') is None, reason='ocrmypdf is not installed')


def test_the_note_body_says_which_language_was_used():
    """A note that does not say how it was made cannot be judged later: text
    read as the wrong language is wrong in ways that look like a bad scan."""
    body = note_body('  Hello OCR  ', 'spa')

    assert 'spa' in body
    assert 'Hello OCR' in body
    assert '  Hello OCR  ' not in body, 'the extracted text should be stripped'


def test_missing_tools_names_what_is_not_installed():
    """The plugin refuses to activate without these, and the command has to
    say the same thing rather than failing inside a subprocess call."""
    missing = missing_tools()

    assert isinstance(missing, list)
    for tool in missing:
        assert tool in REQUIRED_TOOLS
        assert shutil.which(tool) is None


def test_missing_tools_reports_a_tool_that_is_not_there():
    """Asked about something that does not exist, it says so."""
    assert missing_tools(('a-tool-that-does-not-exist',)) == \
        ['a-tool-that-does-not-exist']


def test_available_languages_always_offers_something():
    """The dialog and the --language flag both pick from this list, so an
    empty one would leave neither with a usable default."""
    langs = available_languages()

    assert langs, 'no language offered at all'
    assert all(isinstance(lang, str) for lang in langs)
    assert 'osd' not in langs, 'osd is orientation detection, not a language'


@needs_pdftotext
def test_a_pdf_that_already_has_text_is_read_without_ocr(tmp_path):
    """The fast path. Most PDFs in a repository were born digital, and
    rasterising one to read text it already carries wastes seconds per file."""
    source = write_pdf(tmp_path / 'invoice.pdf', 'Hello OCR from MiAZ')

    text = extract_text(source)

    assert 'Hello OCR from MiAZ' in text


@needs_ocrmypdf
def test_forcing_ocr_reads_the_page_as_an_image(tmp_path):
    """The slow path, which is the one the plugin exists for. Takes a couple
    of seconds because it really does rasterise and recognise the page."""
    source = write_pdf(tmp_path / 'invoice.pdf', 'Hello OCR from MiAZ')

    text = extract_text(source, lang='eng', force=True)

    assert 'Hello' in text, f'OCR returned {text!r}'


@needs_ocrmypdf
def test_the_source_document_is_never_modified(tmp_path):
    """The repository holds the document itself, not a working copy. OCR reads
    it and writes a note; it must not rewrite the file it read."""
    source = write_pdf(tmp_path / 'invoice.pdf', 'Hello OCR from MiAZ')
    before = open(source, 'rb').read()

    extract_text(source, lang='eng', force=True)

    assert open(source, 'rb').read() == before, 'OCR modified the document'


def test_a_document_that_is_not_there_gives_back_nothing(tmp_path):
    """A stale index, or a document deleted since. Nothing to extract is not
    a crash, and the caller reports it as a document with no text."""
    assert extract_text(str(tmp_path / 'gone.pdf')) == ''


def test_a_file_that_is_not_a_pdf_gives_back_nothing(tmp_path):
    """Eligibility is the caller's business, but a wrong file must not raise
    out of here and take a batch down with it."""
    not_a_pdf = tmp_path / 'notes.txt'
    not_a_pdf.write_text('this is not a pdf', encoding='utf-8')

    assert extract_text(str(not_a_pdf)) == ''


def test_extraction_leaves_no_temporary_files_behind(tmp_path):
    """ocrmypdf writes a PDF and a sidecar. Both are working files and belong
    in a directory that goes away."""
    source = write_pdf(tmp_path / 'invoice.pdf', 'Hello OCR from MiAZ')

    extract_text(source)

    assert sorted(os.listdir(tmp_path)) == ['invoice.pdf']


def test_the_plugin_and_the_backend_want_the_same_tools():
    """MiAZOCR declares REQUIRED_TOOLS as a literal because packaging reads it
    without importing the module (tests/test_packaging_tools.py AST-parses it,
    and an attribute reference is not a literal). The backend needs the same
    list to decide whether it can work at all, so the two are written twice and
    checked here rather than left to drift.
    """
    import ast

    plugin = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'resources', 'plugins', 'MiAZOCR', 'ocr.py')
    tree = ast.parse(open(plugin, encoding='utf-8').read())
    declared = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'REQUIRED_TOOLS':
                    declared = ast.literal_eval(node.value)

    assert declared is not None, 'MiAZOCR declares no REQUIRED_TOOLS'
    assert tuple(declared) == tuple(REQUIRED_TOOLS)
