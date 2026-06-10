#!/usr/bin/python3

"""
Tests for MiAZ.backend.util — runs without a display (GObject/Gio only, no GTK/Adw).

MockApp is intentionally minimal: MiAZUtil.__init__ only stores self.app, so any
object works.  None of the methods under test call self.app at all.
"""

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

import pytest
from MiAZ.backend.util import MiAZUtil


class MockApp:
    """Minimal stand-in for the real application object."""
    def get_config(self, name):
        return None


@pytest.fixture(scope='module')
def util():
    return MiAZUtil(MockApp())


# ---------------------------------------------------------------------------
# filename_is_normalized
# ---------------------------------------------------------------------------

def test_normalized_seven_fields(util):
    assert util.filename_is_normalized('20240315-ES-HOU-BANK-INV-concept-PERSON') is True


def test_normalized_simple_name_false(util):
    assert util.filename_is_normalized('simple_file') is False


def test_normalized_exactly_seven_parts(util):
    name = 'A-B-C-D-E-F-G'
    assert util.filename_is_normalized(name) is True


def test_normalized_six_parts_false(util):
    assert util.filename_is_normalized('A-B-C-D-E-F') is False


def test_normalized_eight_parts_false(util):
    # Eight dashes means 9 parts, not 7
    assert util.filename_is_normalized('A-B-C-D-E-F-G-H') is False


# ---------------------------------------------------------------------------
# get_fields
# ---------------------------------------------------------------------------

def test_get_fields_standard(util):
    fields = util.get_fields('20240315-ES-HOU-BANK-INV-concept-PERSON.pdf')
    assert isinstance(fields, list)
    assert len(fields) == 7
    assert fields[0] == '20240315'
    assert fields[1] == 'ES'
    assert fields[6] == 'PERSON'


def test_get_fields_no_extension(util):
    fields = util.get_fields('20240315-ES-HOU-BANK-INV-concept-PERSON')
    assert len(fields) == 7


def test_get_fields_excess_hyphens_merged(util):
    # concept field itself contains a hyphen: 8 dash-segments total
    # get_fields should merge the excess into the last field
    fields = util.get_fields('FAKE-XX-GRP-SND-PRP-con-cept-RCV.pdf')
    assert len(fields) == 7
    # The merged last field must contain the excess parts joined by '-'
    assert 'RCV' in fields[6]


def test_get_fields_basename_stripped(util):
    # Absolute path: only the basename should be parsed
    fields = util.get_fields('/some/path/to/FAKE-XX-GRP-SND-PRP-concept-RCV.pdf')
    assert len(fields) == 7
    assert fields[0] == 'FAKE'


# ---------------------------------------------------------------------------
# filename_details
# ---------------------------------------------------------------------------

def test_filename_details_extension_lowercased(util):
    name, ext = util.filename_details('/path/to/file.PDF')
    assert name == 'file'
    assert ext == 'pdf'


def test_filename_details_lowercase_passthrough(util):
    name, ext = util.filename_details('document.txt')
    assert ext == 'txt'


def test_filename_details_no_extension(util):
    name, ext = util.filename_details('nodotfile')
    assert name == 'nodotfile'
    assert ext == ''


def test_filename_details_multiple_dots(util):
    # rfind means only the last dot is the separator
    name, ext = util.filename_details('archive.tar.gz')
    assert ext == 'gz'
    assert name == 'archive.tar'


# ---------------------------------------------------------------------------
# valid_key
# ---------------------------------------------------------------------------

def test_valid_key_spaces_become_underscores(util):
    result = util.valid_key('hello world')
    assert ' ' not in result
    assert '_' in result


def test_valid_key_hyphens_become_underscores(util):
    result = util.valid_key('hello-world')
    assert result == 'hello_world'


def test_valid_key_special_chars_stripped(util):
    result = util.valid_key('hello@world!')
    assert '@' not in result
    assert '!' not in result


def test_valid_key_alphanumeric_unchanged(util):
    result = util.valid_key('FakeKey123')
    assert result == 'FakeKey123'


def test_valid_key_mixed(util):
    result = util.valid_key('  fake key - value! ')
    assert ' ' not in result
    assert '!' not in result


# ---------------------------------------------------------------------------
# filename_validate
#
# filename_validate is a STRUCTURAL check only: exactly 7 non-empty fields.
# Field-value validity (date format, country/group/sender/etc. enabled) is
# repo-relative and lives in the Workspace parser, not here.
# ---------------------------------------------------------------------------

def test_filename_validate_standard(util):
    assert util.filename_validate('20240315-ES-HOU-BANK-INV-concept-PERSON.pdf') is True

def test_filename_validate_non_iso_country(util):
    # Invented / non-ISO country codes are accepted: the country universe is
    # user-defined, not restricted to ISO-3166.
    assert util.filename_validate('20240315-MARS-HOU-BANK-INV-concept-PERSON.pdf') is True
    assert util.filename_validate('20240315-es-HOU-BANK-INV-concept-PERSON.pdf') is True

def test_filename_validate_non_yyyymmdd_date(util):
    # Dates that are not YYYYMMDD are accepted structurally; the Workspace
    # decides whether a date value is interpretable.
    assert util.filename_validate('2024Q1-ES-HOU-BANK-INV-concept-PERSON.pdf') is True

def test_filename_validate_wrong_field_count(util):
    assert util.filename_validate('20240315-ES-HOU-BANK-INV-concept.pdf') is False

def test_filename_validate_hyphen_in_tail_field(util):
    # Hyphens inside Concept/SentTo produce >7 parts; get_fields merges the
    # excess back into SentTo, so the name must still validate.
    assert util.filename_validate('20240315-ES-HOU-BANK-INV-Q1-report-PERSON.pdf') is True

def test_filename_validate_full_path(util):
    # A directory component with hyphens must not affect validation.
    assert util.filename_validate('/home/t00m/my-repo/20240315-ES-HOU-BANK-INV-concept-PERSON.pdf') is True

def test_filename_validate_empty_fields(util):
    assert util.filename_validate('20240315-ES-----.pdf') is False

def test_filename_normalize_already_normalized(util):
    fname = 'FAKE-XX-GRP-SND-PRP-concept-RCV.pdf'
    result = util.filename_normalize(fname)
    # Already normalized: name part should remain identical
    assert result == fname


def test_filename_normalize_unnormalized_puts_name_in_field5(util):
    result = util.filename_normalize('invoice.pdf')
    parts = result.split('.')[0].split('-')
    assert len(parts) == 7
    # Field at index 5 (Concept) should contain a sanitised version of 'invoice'
    assert 'invoice' in parts[5]


def test_filename_normalize_preserves_extension(util):
    result = util.filename_normalize('fakefile.docx')
    assert result.endswith('.docx')
