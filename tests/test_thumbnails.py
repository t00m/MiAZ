#!/usr/bin/python3

"""The thumbnail backend: what gets a preview image and what does not."""

import os
import shutil

import cairo
import pytest

from MiAZ.backend import thumbnails
from MiAZ.backend.thumbnails import thumbnail_for


@pytest.fixture
def count_reads(monkeypatch):
    """Count how often the document itself is read.

    file_digest is the only thing in thumbnail_for that opens the document, so
    counting it counts the reads.
    """
    reads = []
    original = thumbnails.file_digest

    def counting(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(thumbnails, 'file_digest', counting)
    return reads


def make_pdf(path):
    # cairo ships with PyGObject, so a real one-page PDF costs three lines.
    surface = cairo.PDFSurface(str(path), 200, 200)
    context = cairo.Context(surface)
    context.set_source_rgb(0.2, 0.4, 0.8)
    context.rectangle(20, 20, 160, 160)
    context.fill()
    surface.finish()


def test_image_is_returned_as_is(tmp_path):
    image = tmp_path / 'photo.png'
    image.write_bytes(b'fake image bytes')
    assert thumbnail_for(str(image), str(tmp_path / 'cache')) == str(image)


def test_unknown_extension_has_no_preview(tmp_path):
    doc = tmp_path / 'letter.docx'
    doc.write_text('x')
    assert thumbnail_for(str(doc), str(tmp_path / 'cache')) is None


def test_missing_file_has_no_preview(tmp_path):
    assert thumbnail_for(str(tmp_path / 'gone.pdf'), str(tmp_path / 'cache')) is None


@pytest.mark.skipif(shutil.which('pdftoppm') is None, reason='pdftoppm not installed')
def test_pdf_first_page_is_rendered_and_cached(tmp_path):
    pdf = tmp_path / 'doc.pdf'
    make_pdf(pdf)
    cache = tmp_path / 'cache'
    first = thumbnail_for(str(pdf), str(cache))
    assert first is not None
    assert first.endswith('.png')
    assert os.path.exists(first)
    mtime = os.path.getmtime(first)
    # A second call is served from the cache: same path, untouched file.
    again = thumbnail_for(str(pdf), str(cache))
    assert again == first
    assert os.path.getmtime(again) == mtime


@pytest.mark.skipif(shutil.which('pdftoppm') is None, reason='pdftoppm not installed')
def test_cached_render_is_found_without_reading_the_document(tmp_path, count_reads):
    """A render already on disk must not cost a full read of the source.

    The cache is keyed by content digest, and computing that digest reads the
    whole file, so asking for a thumbnail that already exists used to read
    every byte of the document to find out where it was.
    """
    pdf = tmp_path / 'doc.pdf'
    make_pdf(pdf)
    cache = tmp_path / 'cache'

    first = thumbnail_for(str(pdf), str(cache))
    again = thumbnail_for(str(pdf), str(cache))

    assert again == first is not None
    assert len(count_reads) == 1, 'the second call read the document again'


@pytest.mark.skipif(shutil.which('pdftoppm') is None, reason='pdftoppm not installed')
def test_renamed_document_keeps_its_render(tmp_path, count_reads):
    """Renaming is what MiAZ does most, and it must not throw the render away.

    This is the property the content digest was chosen for. A rename moves no
    bytes and leaves the inode alone, so the cached image still applies.
    """
    pdf = tmp_path / 'doc.pdf'
    make_pdf(pdf)
    cache = tmp_path / 'cache'
    first = thumbnail_for(str(pdf), str(cache))

    renamed = tmp_path / '20260101-ES-HOU-ACME-INV-power-JOHNDOE.pdf'
    pdf.rename(renamed)
    again = thumbnail_for(str(renamed), str(cache))

    assert again == first is not None
    assert len(count_reads) == 1, 'the rename cost a fresh read'


@pytest.mark.skipif(shutil.which('pdftoppm') is None, reason='pdftoppm not installed')
def test_edited_document_is_rendered_again(tmp_path, count_reads):
    """Different bytes must produce a different image, not the stale one."""
    pdf = tmp_path / 'doc.pdf'
    make_pdf(pdf)
    cache = tmp_path / 'cache'
    first = thumbnail_for(str(pdf), str(cache))

    # A second PDF with different contents, written over the first.
    other = tmp_path / 'other.pdf'
    surface = cairo.PDFSurface(str(other), 400, 400)
    context = cairo.Context(surface)
    context.set_source_rgb(0.9, 0.1, 0.1)
    context.rectangle(0, 0, 400, 400)
    context.fill()
    surface.finish()
    pdf.write_bytes(other.read_bytes())

    again = thumbnail_for(str(pdf), str(cache))

    assert again is not None
    assert again != first, 'the edited document kept the old image'
    assert len(count_reads) == 2


@pytest.mark.skipif(shutil.which('pdftoppm') is None, reason='pdftoppm not installed')
def test_broken_pdf_has_no_preview(tmp_path):
    pdf = tmp_path / 'broken.pdf'
    pdf.write_text('this is not a pdf')
    assert thumbnail_for(str(pdf), str(tmp_path / 'cache')) is None
