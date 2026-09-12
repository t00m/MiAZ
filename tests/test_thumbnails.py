#!/usr/bin/python3

"""The thumbnail backend: what gets a preview image and what does not."""

import os
import shutil

import cairo
import pytest

from MiAZ.backend.thumbnails import thumbnail_for


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
def test_broken_pdf_has_no_preview(tmp_path):
    pdf = tmp_path / 'broken.pdf'
    pdf.write_text('this is not a pdf')
    assert thumbnail_for(str(pdf), str(tmp_path / 'cache')) is None
