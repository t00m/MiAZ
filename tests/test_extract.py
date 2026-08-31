#!/usr/bin/python3

"""
Tests for MiAZ.backend.extract — the local, non-AI text extraction and
vocabulary matching behind the rename dialog's Detect menu. No GTK/Adw/Gdk
import anywhere in the module under test, so this runs without a display.
"""

import subprocess

from MiAZ.backend.extract import (
    ExtractResult,
    extract,
    match_vocab,
    missing_tools,
)


# ExtractResult.is_useful

def test_is_useful_requires_enough_letters():
    assert ExtractResult('x' * 300, 'pdftotext').is_useful is True
    assert ExtractResult('1234567890' * 30, 'pdftotext').is_useful is False  # no letters
    assert ExtractResult('short text', 'pdftotext').is_useful is False  # too short
    assert ExtractResult('irrelevant', 'none').is_useful is False  # method 'none'


# extract(): formats needing no external tool

def test_extract_reads_plain_text_file(tmp_path):
    path = tmp_path / 'note.txt'
    path.write_text('Invoice from Bank of America dated 2024-03-15.')
    result = extract(path)
    assert result.method == 'plain'
    assert 'Bank of America' in result.text


def test_extract_unknown_suffix_returns_none_method(tmp_path):
    path = tmp_path / 'archive.zip'
    path.write_bytes(b'PK\x03\x04')
    result = extract(path)
    assert result.method == 'none'
    assert result.text == ''


# extract(): pdftotext / OCR fallback, subprocess mocked so no real tool is needed

def test_extract_pdf_uses_pdftotext_when_it_finds_a_text_layer(tmp_path, monkeypatch):
    path = tmp_path / 'doc.pdf'
    path.write_bytes(b'%PDF-1.4\n%%EOF\n')
    monkeypatch.setattr('shutil.which', lambda name: f'/usr/bin/{name}')

    def fake_run(cmd, **kwargs):
        assert cmd[0] == 'pdftotext'
        return subprocess.CompletedProcess(cmd, 0, stdout='A' * 250, stderr='')

    monkeypatch.setattr('subprocess.run', fake_run)
    result = extract(path)
    assert result.method == 'pdftotext'
    assert result.is_useful is True


def test_extract_pdf_falls_back_to_ocr_when_pdftotext_finds_nothing(tmp_path, monkeypatch):
    path = tmp_path / 'scan.pdf'
    path.write_bytes(b'%PDF-1.4\n%%EOF\n')
    monkeypatch.setattr('shutil.which', lambda name: f'/usr/bin/{name}')

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[0])
        if cmd[0] == 'pdftotext':
            return subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')
        if cmd[0] == 'pdftoppm':
            # No page files are produced, so the OCR loop below sees nothing
            # to do and the result is empty text with method 'none'.
            return subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')
        raise AssertionError(f'unexpected command: {cmd}')

    monkeypatch.setattr('subprocess.run', fake_run)
    result = extract(path)
    assert 'pdftotext' in calls
    assert 'pdftoppm' in calls
    assert result.method == 'none'


def test_extract_image_uses_tesseract(tmp_path, monkeypatch):
    path = tmp_path / 'scan.png'
    path.write_bytes(b'\x89PNG\r\n\x1a\n')
    monkeypatch.setattr('shutil.which', lambda name: f'/usr/bin/{name}')

    def fake_run(cmd, **kwargs):
        assert cmd[0] == 'tesseract'
        return subprocess.CompletedProcess(cmd, 0, stdout='Country: Germany', stderr='')

    monkeypatch.setattr('subprocess.run', fake_run)
    result = extract(path)
    assert result.method == 'tesseract'
    assert 'Germany' in result.text


def test_extract_returns_empty_when_tools_are_missing(tmp_path, monkeypatch):
    path = tmp_path / 'doc.pdf'
    path.write_bytes(b'%PDF-1.4\n%%EOF\n')
    monkeypatch.setattr('shutil.which', lambda name: None)
    result = extract(path)
    assert result.method == 'none'
    assert result.text == ''


# missing_tools()

def test_missing_tools_reports_absent_binaries(monkeypatch):
    present = {'pdftotext', 'tesseract'}
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/x' if name in present else None)
    assert missing_tools() == ['pdftoppm']


def test_missing_tools_empty_when_all_present(monkeypatch):
    monkeypatch.setattr('shutil.which', lambda name: '/usr/bin/x')
    assert missing_tools() == []


# match_vocab()

def test_match_vocab_finds_description_in_text():
    used = {'DE': 'Germany', 'ES': 'Spain'}
    assert match_vocab('Invoice issued in Germany, VAT included.', used) == 'DE'


def test_match_vocab_prefers_the_longer_more_specific_description():
    # "America" alone would also match "United States of America" style text;
    # the longer, more specific description must win.
    used = {'ORG1': 'America', 'ORG2': 'Bank of America'}
    assert match_vocab('Statement issued by Bank of America NA.', used) == 'ORG2'


def test_match_vocab_returns_empty_when_nothing_matches():
    used = {'DE': 'Germany', 'ES': 'Spain'}
    assert match_vocab('This document mentions no known country.', used) == ''


def test_match_vocab_handles_empty_input():
    assert match_vocab('', {'DE': 'Germany'}) == ''
    assert match_vocab('Germany', {}) == ''
    assert match_vocab('', {}) == ''
