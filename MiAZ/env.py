# Copyright 2019-2025 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MiAZ environment module.

Two run modes are supported from a single file:

- Installed: Meson generates ``MiAZ/_buildconfig.py`` with the build-time
  paths (prefix, version, profile). It is imported and used as-is.
- Source checkout: ``_buildconfig`` is absent, so paths self-locate relative
  to this file (resources are read from the repo's ``data/`` directory).
"""

import os
import re
import sys


def _build_env(app_id, version, pkgdatadir, localedir, profile):
    """Build the ENV dictionary from the resolved build-time values."""
    ENV = {}

    # SYS Env
    ENV['SYS'] = {}
    ENV['SYS']['PYTHON'] = sys.version

    # App
    ENV['APP'] = {}
    ENV['APP']['ID'] = app_id
    ENV['APP']['VERSION'] = version
    ENV['APP']['PGKDATADIR'] = pkgdatadir
    ENV['APP']['LOCALEDIR'] = localedir
    ENV['APP']['PROFILE'] = profile
    ENV['APP']['name'] = "AZ Organizer"
    ENV['APP']['shortname'] = "MiAZ"
    ENV['APP']['description'] = 'Personal Document Organizer'
    ENV['APP']['license'] = 'GPL v3'
    ENV['APP']['copyright'] = "Copyright \xa9 2019 Tomás Vírseda"
    ENV['APP']['author'] = 'Tomás Vírseda'
    ENV['APP']['author_email'] = 'tomasvirseda@gmail.com'
    ENV['APP']['author_website'] = 'https://github.com/t00m'
    ENV['APP']['contributors'] = []
    ENV['APP']['website'] = 'https://github.com/t00m/MiAZ'

    # Configuration
    ENV['CONF'] = {}
    ENV['CONF']['ROOT'] = ENV['APP']['PGKDATADIR']
    ENV['CONF']['USER_DIR'] = os.path.expanduser('~')

    # Local paths
    ENV['LPATH'] = {}
    ENV['LPATH']['ROOT'] = os.path.join(ENV['CONF']['USER_DIR'], f".{ENV['APP']['shortname']}")
    ENV['LPATH']['ETC'] = os.path.join(ENV['LPATH']['ROOT'], 'etc')
    ENV['LPATH']['REPOS'] = os.path.join(ENV['LPATH']['ETC'], 'repos')
    ENV['LPATH']['VAR'] = os.path.join(ENV['LPATH']['ROOT'], 'var')
    ENV['LPATH']['DB'] = os.path.join(ENV['LPATH']['VAR'], 'db')
    ENV['LPATH']['CACHE'] = os.path.join(ENV['LPATH']['VAR'], 'cache')
    ENV['LPATH']['LOG'] = os.path.join(ENV['LPATH']['VAR'], 'log')
    ENV['LPATH']['TMP'] = os.path.join(ENV['LPATH']['VAR'], 'tmp')
    ENV['LPATH']['REPO'] = os.path.join(ENV['LPATH']['TMP'], 'repo')
    ENV['LPATH']['OPT'] = os.path.join(ENV['LPATH']['ROOT'], 'opt')
    ENV['LPATH']['PLUGINS'] = os.path.join(ENV['LPATH']['OPT'], 'plugins')

    # Global paths
    ENV['GPATH'] = {}
    ENV['GPATH']['ROOT'] = ENV['CONF']['ROOT']
    ENV['GPATH']['DATA'] = os.path.join(ENV['GPATH']['ROOT'], 'resources')
    ENV['GPATH']['DOCS'] = os.path.join(ENV['GPATH']['DATA'], 'docs')
    ENV['GPATH']['ICONS'] = os.path.join(ENV['GPATH']['DATA'], 'icons', 'hicolor', 'scalable')
    ENV['GPATH']['FLAGS'] = os.path.join(ENV['GPATH']['ICONS'], 'flags')
    ENV['GPATH']['LOCALE'] = os.path.join(ENV['GPATH']['DATA'], 'po')
    ENV['GPATH']['PLUGINS'] = os.path.join(ENV['GPATH']['DATA'], 'plugins')
    ENV['GPATH']['CONF'] = os.path.join(ENV['GPATH']['DATA'], 'conf')

    # Common file paths
    ENV['FILE'] = {}
    ENV['FILE']['CONF'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-application.json')
    ENV['FILE']['VERSION'] = os.path.join(ENV['GPATH']['DOCS'], 'VERSION')
    ENV['FILE']['README'] = os.path.join(ENV['GPATH']['DOCS'], 'README')
    ENV['FILE']['APPICON'] = os.path.join(ENV['GPATH']['ICONS'], 'MiAZ.svg')
    ENV['FILE']['LOG'] = os.path.join(ENV['LPATH']['LOG'], 'MiAZ.log')
    ENV['FILE']['GROUPS'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-groups.json')
    ENV['FILE']['PURPOSES'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-purposes.json')
    ENV['FILE']['CONCEPTS'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-concepts.json')
    ENV['FILE']['PEOPLE'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-people.json')
    ENV['FILE']['EXTENSIONS'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-extensions.json')
    ENV['FILE']['COUNTRIES'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-countries.json')
    ENV['FILE']['WHO'] = os.path.join(ENV['LPATH']['ETC'], 'MiAZ-who.json')
    ENV['FILE']['PLUGINS'] = os.path.join(ENV['LPATH']['CACHE'], "index-plugins.json")

    # Caches
    ENV['CACHE'] = {}
    ENV['CACHE']['CONCEPTS'] = {}
    ENV['CACHE']['CONCEPTS']['ACTIVE'] = []
    ENV['CACHE']['CONCEPTS']['INACTIVE'] = []

    # Plugins
    ENV['APP']['PLUGINS'] = {}
    ENV['APP']['PLUGINS']['INDEX'] = os.path.join(ENV['LPATH']['CACHE'], "index-plugins.json")

    # App status
    ENV['APP']['STATUS'] = {}
    ENV['APP']['STATUS']['RESTART_NEEDED'] = False

    # App executable
    ENV['APP']['RUNTIME'] = {}

    return ENV


def _read_dev_version(repo_root):
    """Read the project version from meson.build for source-checkout runs."""
    meson_build = os.path.join(repo_root, 'meson.build')
    try:
        with open(meson_build, encoding='utf-8') as handle:
            for line in handle:
                match = re.search(r"(?<![_\w])version\s*:\s*'([^']+)'", line)
                if match:
                    return match.group(1)
    except OSError:
        pass
    return '0.0.0-dev'


try:
    from MiAZ import _buildconfig as _bc
    ENV = _build_env(
        app_id=_bc.APP_ID,
        version=_bc.VERSION,
        pkgdatadir=_bc.PKGDATADIR,
        localedir=_bc.LOCALEDIR,
        profile=_bc.PROFILE,
    )
except ImportError:
    # Source checkout: resolve paths relative to the repository.
    _repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ENV = _build_env(
        app_id='io.github.t00m.MiAZ',
        version=_read_dev_version(_repo_root),
        pkgdatadir=os.path.join(_repo_root, 'data'),
        localedir=os.path.join(_repo_root, 'po'),
        profile='development',
    )
