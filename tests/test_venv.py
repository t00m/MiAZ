#!/usr/bin/python3

"""
Tests for MiAZ.backend.venv.MiAZVenv. The network-heavy parts (venv creation and
pip) are not exercised here; these cover the pure logic: requirements parsing,
installed/missing detection against a fake site-packages tree, the stale marker,
and requirement_name.
"""

import os

from MiAZ.backend.venv import MiAZVenv, requirement_name


class StubApp:
    def __init__(self, venv_path):
        self._env = {'LPATH': {'VENV': venv_path}}

    def get_env(self):
        return self._env


def _make_venv(tmp_path, python='3.12', dists=()):
    """Create a fake venv tree (no real interpreter, no pip)."""
    venv = tmp_path / 'opt' / 'venv'
    (venv / 'bin').mkdir(parents=True)
    (venv / 'bin' / 'python').write_text('')
    site = venv / 'lib' / f'python{python}' / 'site-packages'
    site.mkdir(parents=True)
    for dist in dists:
        (site / f'{dist}.dist-info').mkdir()
    (venv / 'miaz-python').write_text(python)
    return str(venv)


def test_requirement_name():
    assert requirement_name('anthropic>=0.40') == 'anthropic'
    assert requirement_name('google-genai==1.2') == 'google-genai'
    assert requirement_name('  ollama  ') == 'ollama'
    assert requirement_name('') == ''


def test_absent_venv(tmp_path):
    venv = MiAZVenv(StubApp(str(tmp_path / 'opt' / 'venv')))
    assert not venv.exists()
    assert venv.site_packages() is None
    assert venv.installed() == set()
    assert venv.stale() is False


def test_installed_and_missing(tmp_path):
    _make_venv(tmp_path, dists=['anthropic-0.40.0', 'google_genai-1.2.0'])
    venv = MiAZVenv(StubApp(str(tmp_path / 'opt' / 'venv')))
    assert venv.exists()
    assert venv.installed() == {'anthropic', 'google-genai'}
    # Name -> version mapping, with names normalised like requirements.
    assert venv.installed_details() == {'anthropic': '0.40.0',
                                        'google-genai': '1.2.0'}
    # google_genai on disk normalises to the google-genai requirement name.
    assert venv.missing(['anthropic', 'google-genai', 'openai']) == ['openai']


def test_distribution_url(tmp_path):
    venv_path = _make_venv(tmp_path, dists=['anthropic-0.40.0', 'openai-1.0.0'])
    site = os.path.join(venv_path, 'lib', 'python3.12', 'site-packages')
    # anthropic: a Project-URL Homepage wins over anything else.
    with open(os.path.join(site, 'anthropic-0.40.0.dist-info', 'METADATA'),
              'w', encoding='utf-8') as fh:
        fh.write('Metadata-Version: 2.1\nName: anthropic\nVersion: 0.40.0\n'
                 'Project-URL: Repository, https://github.com/anthropics/x\n'
                 'Project-URL: Homepage, https://www.anthropic.com\n'
                 '\nLong description here.\n')
    # openai: only a legacy Home-page header.
    with open(os.path.join(site, 'openai-1.0.0.dist-info', 'METADATA'),
              'w', encoding='utf-8') as fh:
        fh.write('Name: openai\nHome-page: https://github.com/openai/openai-python\n\n')

    venv = MiAZVenv(StubApp(str(tmp_path / 'opt' / 'venv')))
    assert venv.distribution_url('anthropic') == 'https://www.anthropic.com'
    assert venv.distribution_url('openai') == 'https://github.com/openai/openai-python'
    # Unknown or metadata-less package falls back to the PyPI project page.
    assert venv.distribution_url('google-genai') == \
        'https://pypi.org/project/google-genai/'


def test_requirements_for(tmp_path):
    pdir = tmp_path / 'PluginX'
    pdir.mkdir()
    (pdir / 'requirements.txt').write_text('# a comment\nanthropic>=0.40\nopenai\n\nopenai\n')
    venv = MiAZVenv(StubApp(str(tmp_path / 'opt' / 'venv')))
    # Comments and blanks dropped, duplicates deduped, order preserved.
    assert venv.requirements_for([str(pdir), str(tmp_path / 'missing')]) == \
        ['anthropic>=0.40', 'openai']


def test_stale_marker(tmp_path):
    _make_venv(tmp_path, python='3.12')
    venv = MiAZVenv(StubApp(str(tmp_path / 'opt' / 'venv')))
    marker = os.path.join(venv.path(), 'miaz-python')
    # Same version as the running interpreter would not be stale; force a
    # different one to prove the check.
    with open(marker, 'w', encoding='utf-8') as fh:
        fh.write('2.7')
    assert venv.stale() is True
