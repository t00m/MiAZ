#!/usr/bin/python3

"""
Tests for MiAZ.backend.util — runs without a display (GObject/Gio only, no GTK/Adw).

MockApp is intentionally minimal: MiAZUtil.__init__ only stores self.app, so any
object works.  None of the methods under test call self.app at all.
"""

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')

from datetime import date

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


# ---------------------------------------------------------------------------
# since_date_last_n_months: first day of the month N calendar months back.
# A fixed 30-day delta used to drift at month boundaries, which hid documents
# from the previous month in the "Since past month" date filter.
# ---------------------------------------------------------------------------

def _ymd(dt):
    return dt.strftime('%Y%m%d')


def test_since_date_last_n_months_past_month_from_month_end(util):
    # The reported bug: on Jul 31, "past month" (n=1) must be Jun 1, not Jul 1.
    assert _ymd(util.since_date_last_n_months(date(2026, 7, 31), 1)) == '20260601'


def test_since_date_last_n_months_three_from_month_end(util):
    assert _ymd(util.since_date_last_n_months(date(2026, 7, 31), 3)) == '20260401'


def test_since_date_last_n_months_six_from_month_end(util):
    assert _ymd(util.since_date_last_n_months(date(2026, 7, 31), 6)) == '20260101'


def test_since_date_last_n_months_crosses_year_boundary(util):
    assert _ymd(util.since_date_last_n_months(date(2026, 1, 15), 1)) == '20251201'
    assert _ymd(util.since_date_last_n_months(date(2026, 3, 31), 6)) == '20250901'


def test_since_date_last_n_months_mid_month(util):
    # Day of adate is irrelevant; the result is always the first of the month.
    assert _ymd(util.since_date_last_n_months(date(2026, 6, 10), 1)) == '20260501'


def test_since_date_last_six_months_delegates(util):
    assert _ymd(util.since_date_last_six_months(date(2026, 7, 31))) == '20260101'


# ---------------------------------------------------------------------------
# filename_rename_needed
# ---------------------------------------------------------------------------

DOC = '20240115-ES-HOU-BANK-INV-RENT-JOHN.pdf'


def test_rename_not_needed_when_the_name_is_unchanged(util):
    # The rename dialog leans on this: a document can be opened only to edit
    # what a plugin tab holds, leaving every filename field alone.
    assert util.filename_rename_needed(DOC, DOC) is False


def test_rename_not_needed_when_only_the_casing_differs(util):
    # filename_rename uppercases the target, so a lowercase target that
    # uppercases back to the source is not a rename either.
    assert util.filename_rename_needed(DOC, DOC.lower()) is False
    assert util.filename_rename_needed(DOC, '20240115-es-hou-bank-inv-rent-john.PDF') is False


def test_rename_needed_when_a_field_changes(util):
    target = '20240115-ES-HOU-BANK-INV-Q1INVOICE-JOHN.pdf'
    assert util.filename_rename_needed(DOC, target) is True


def test_rename_needed_compares_full_paths(util):
    assert util.filename_rename_needed(f'/docs/{DOC}', f'/docs/{DOC}') is False
    assert util.filename_rename_needed(f'/docs/{DOC}', f'/other/{DOC}') is True


def test_rename_needed_without_uppercasing(util):
    # upper=False (zip exports and other non-document files): the target is
    # compared as given.
    assert util.filename_rename_needed(DOC, DOC.lower(), upper=False) is True
    assert util.filename_rename_needed(DOC, DOC, upper=False) is False


# "Since last year" means the last twelve months, not since January 1st.
# It used to resolve through since_date_this_year, so on 7 August it covered
# seven months, and on 2 January it covered two days.

def test_since_date_last_n_months_twelve_is_one_year_back(util):
    assert _ymd(util.since_date_last_n_months(date(2026, 8, 7), 12)) == '20250801'


def test_since_date_last_n_months_twelve_from_january(util):
    """The case the old range got most wrong: on 2 January it covered two days."""
    assert _ymd(util.since_date_last_n_months(date(2026, 1, 2), 12)) == '20250101'


def test_since_date_last_n_months_twelve_from_december(util):
    assert _ymd(util.since_date_last_n_months(date(2026, 12, 31), 12)) == '20251201'


def test_since_date_this_year_still_means_january_first(util):
    """Kept for anything that genuinely wants the calendar year to date."""
    assert _ymd(util.since_date_this_year(date(2026, 8, 7))) == '20260101'
