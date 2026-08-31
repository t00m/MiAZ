#!/usr/bin/python3

"""
Tests for scripts/devel/render_release_notes.py.

The release notes lived in three files and were written by hand in each, which
in practice meant not written at all: 0.1.50 and 0.1.60 both shipped with
"New release. See CHANGELOG.md for details." in debian/changelog and in the
spec %changelog, because sync_versions.sh writes that placeholder and nothing
ever checked whether it had been replaced.

They now come from one file per release, releases/<version>.md, and the three
are rendered from it.
"""

import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'scripts', 'devel', 'render_release_notes.py')


def load():
    """Import the script by path: scripts/devel is not a package, and it has
    no business becoming one for the sake of a test."""
    spec = importlib.util.spec_from_file_location('render_release_notes', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def render():
    return load()


SOURCE = """# 0.2.0

Shortcuts on older libadwaita, dates checked when you leave the field.

- The keyboard shortcuts window works on libadwaita 1.7
- The date is checked when you leave the field, not on every keystroke
- German and French catalogues removed
"""

BULLETS = [
    'The keyboard shortcuts window works on libadwaita 1.7',
    'The date is checked when you leave the field, not on every keystroke',
    'German and French catalogues removed',
]

METAINFO = """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <releases>
    <release version="0.2.0" date="2026-08-21" urgency="medium">
      <description>
        <p>See CHANGELOG.md for details.</p>
      </description>
    </release>
    <release version="0.1.60" date="2026-08-19" urgency="medium">
      <description>
        <p>Something real that must not be touched.</p>
      </description>
    </release>
  </releases>
</component>
"""

DEBIAN = """miaz (0.2.0-1) unstable; urgency=medium

  * New release. See CHANGELOG.md for details.

 -- Tomas Virseda <t@example.com>  Thu, 21 Aug 2026 00:00:00 +0200

miaz (0.1.60-1) unstable; urgency=medium

  * An older entry that must not be touched.

 -- Tomas Virseda <t@example.com>  Wed, 19 Aug 2026 00:00:00 +0200
"""

SPEC = """%changelog
* Thu Aug 21 2026 Tomas Virseda <t@example.com> - 0.2.0-1
- New release. See CHANGELOG.md for details.

* Wed Aug 19 2026 Tomas Virseda <t@example.com> - 0.1.60-1
- An older entry that must not be touched.
"""


def test_the_source_is_read_as_a_summary_and_its_bullets(render):
    version, summary, bullets = render.parse_source(SOURCE)
    assert version == '0.2.0'
    assert summary == 'Shortcuts on older libadwaita, dates checked when you leave the field.'
    assert bullets == BULLETS


def test_a_wrapped_summary_is_read_as_one_sentence(render):
    """A summary is a sentence, and a sentence long enough to say anything gets
    wrapped in the file. Reading only the first line truncates it mid-clause,
    which is what a software centre would then display."""
    _version, summary, _bullets = render.parse_source(
        "# 0.2.0\n\nRuns on Debian 13, a rename date that waits,\n"
        "and a complete Spanish translation.\n\n- a highlight\n")
    assert summary == ('Runs on Debian 13, a rename date that waits, '
                       'and a complete Spanish translation.')


def test_only_the_first_paragraph_is_the_summary(render):
    """Anything after the blank line is prose for a human reading the file."""
    _version, summary, _bullets = render.parse_source(
        "# 0.2.0\n\nThe summary.\n\nA note to self, not for release.\n\n- a highlight\n")
    assert summary == 'The summary.'


def test_a_source_without_bullets_is_refused(render):
    """An empty highlight list renders three empty entries and looks deliberate.
    Better to stop than to publish nothing in three places."""
    with pytest.raises(ValueError):
        render.parse_source('# 0.2.0\n\nJust a summary.\n')


def test_a_source_without_a_summary_is_refused(render):
    with pytest.raises(ValueError):
        render.parse_source('# 0.2.0\n\n- only a bullet\n')


def test_the_metainfo_entry_is_filled(render):
    out = render.render_metainfo(METAINFO, '0.2.0', 'A summary.', BULLETS)
    assert '<p>A summary.</p>' in out
    for bullet in BULLETS:
        assert f'<li>{bullet}</li>' in out
    assert 'See CHANGELOG.md for details' not in out


def test_the_metainfo_leaves_older_releases_alone(render):
    out = render.render_metainfo(METAINFO, '0.2.0', 'A summary.', BULLETS)
    assert '<p>Something real that must not be touched.</p>' in out
    assert out.count('<release ') == 2


def test_the_debian_stanza_is_filled(render):
    out = render.render_debian(DEBIAN, '0.2.0', BULLETS)
    for bullet in BULLETS:
        assert f'  * {bullet}' in out
    assert 'New release. See CHANGELOG.md' not in out
    assert '  * An older entry that must not be touched.' in out
    # The trailer that dpkg needs has to survive.
    assert ' -- Tomas Virseda <t@example.com>  Thu, 21 Aug 2026' in out


def test_the_spec_entry_is_filled(render):
    out = render.render_spec(SPEC, '0.2.0', BULLETS)
    for bullet in BULLETS:
        assert f'- {bullet}' in out
    assert 'New release. See CHANGELOG.md' not in out
    assert '- An older entry that must not be touched.' in out


@pytest.mark.parametrize('name, text, args', [
    ('render_metainfo', METAINFO, ('0.2.0', 'A summary.', BULLETS)),
    ('render_debian', DEBIAN, ('0.2.0', BULLETS)),
    ('render_spec', SPEC, ('0.2.0', BULLETS)),
])
def test_rendering_twice_changes_nothing_the_second_time(render, name, text, args):
    """It runs on every release and after every edit of the source, so it has
    to be safe to run again."""
    once = getattr(render, name)(text, *args)
    twice = getattr(render, name)(once, *args)
    assert once == twice


@pytest.mark.parametrize('name, text, args', [
    ('render_metainfo', METAINFO, ('9.9.9', 'A summary.', BULLETS)),
    ('render_debian', DEBIAN, ('9.9.9', BULLETS)),
    ('render_spec', SPEC, ('9.9.9', BULLETS)),
])
def test_a_missing_entry_is_an_error_not_a_silent_pass(render, name, text, args):
    """sync_versions.sh creates the stanza; this fills it. If the stanza is not
    there, the version was never synced and rendering nothing would hide it."""
    with pytest.raises(LookupError):
        getattr(render, name)(text, *args)


def test_the_placeholder_is_recognised(render):
    assert render.is_placeholder('New release. See CHANGELOG.md for details.')
    assert render.is_placeholder('See CHANGELOG.md for details.')
    assert not render.is_placeholder('The date is checked when you leave the field')
