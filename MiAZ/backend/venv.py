#!/usr/bin/python3
"""
# File: venv.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Optional per-user virtualenv for plugin Python dependencies.

Some plugins need third-party Python libraries (for example the AI provider
SDKs). Installing them into the system Python is blocked on modern distros
(PEP 668) and would pollute the OS, so MiAZ keeps them in a virtualenv it owns
at ~/.MiAZ/opt/venv. The venv is only a package store: the app keeps running
under the system Python and just adds the venv's site-packages to sys.path so
plugins can import the libraries. Nothing is installed unless the user enables
the feature.
"""

import os
import re
import sys
import glob
import shutil
import subprocess

from gi.repository import GLib, GObject

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.tasks import run_in_background

MARKER = 'miaz-python'


def requirement_name(requirement):
    """Distribution name from a line like 'anthropic>=0.40' -> 'anthropic'."""
    match = re.match(r'^[A-Za-z0-9._-]+', requirement.strip())
    return match.group(0) if match else ''


class MiAZVenv(GObject.GObject):
    """Manage the optional external-libraries virtualenv."""
    __gtype_name__ = 'MiAZVenv'
    __gsignals__ = {
        'install-started': (GObject.SignalFlags.RUN_LAST, None, ()),
        'install-progress': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        # Fraction of the whole install completed, 0.0 to 1.0, emitted at each
        # package boundary so the UI can drive a determinate progress bar.
        'install-fraction': (GObject.SignalFlags.RUN_LAST, None, (float,)),
        'install-finished': (GObject.SignalFlags.RUN_LAST, None, (bool, str)),
    }

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZ.Venv')
        self._path = None
        self._busy = False

    # Paths and state

    def path(self):
        # Resolved lazily: get_env() is not ready while the app is still
        # constructing its services in __init__.
        if self._path is None:
            self._path = self.app.get_env()['LPATH']['VENV']
        return self._path

    def python_bin(self):
        return os.path.join(self.path(), 'bin', 'python')

    def exists(self):
        return os.path.isfile(self.python_bin())

    def is_busy(self):
        return self._busy

    def site_packages(self):
        hits = glob.glob(os.path.join(self.path(), 'lib', 'python*', 'site-packages'))
        return hits[0] if hits else None

    def _pyver(self):
        return f'{sys.version_info.major}.{sys.version_info.minor}'

    def _marker_file(self):
        return os.path.join(self.path(), MARKER)

    def stale(self):
        """True when the venv was built with a different Python minor version.

        Compiled wheels (for example pydantic-core) do not import across Python
        minor versions, so a stale venv must be rebuilt.
        """
        if not self.exists():
            return False
        try:
            with open(self._marker_file(), encoding='utf-8') as fh:
                built = fh.read().strip()
        except OSError:
            return False
        return built != self._pyver()

    # sys.path integration

    def ensure_on_syspath(self):
        """Add the venv site-packages to sys.path when the venv is present.

        Idempotent and safe to call once at startup before plugins load. Nothing
        happens when the feature was never enabled.
        """
        if not self.exists():
            return
        site = self.site_packages()
        if site and site not in sys.path:
            sys.path.insert(0, site)
            self.log.debug(f'Added venv site-packages to sys.path: {site}')

    # Requirements

    def requirements_for(self, plugin_dirs):
        """Read and dedupe requirements.txt from the given plugin directories."""
        reqs = []
        for pdir in plugin_dirs:
            path = os.path.join(pdir, 'requirements.txt')
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding='utf-8') as fh:
                    for raw in fh:
                        line = raw.strip()
                        if line and not line.startswith('#') and line not in reqs:
                            reqs.append(line)
            except OSError as error:
                self.log.warning(f'Cannot read {path}: {error}')
        return reqs

    def installed_details(self):
        """Distributions in the venv as a name -> version mapping."""
        site = self.site_packages()
        if not site:
            return {}
        details = {}
        for dist in glob.glob(os.path.join(site, '*.dist-info')):
            base = os.path.basename(dist)[:-len('.dist-info')]
            name, _sep, version = base.partition('-')
            details[name.lower().replace('_', '-')] = version
        return details

    def installed(self):
        """Top-level distribution names present in the venv site-packages."""
        return set(self.installed_details())

    def distribution_url(self, name):
        """Best project URL for an installed distribution.

        Reads Home-page and Project-URL from the package METADATA, preferring a
        homepage, source or repository link. Falls back to the PyPI project page
        when the metadata carries no usable URL.
        """
        target = name.lower().replace('_', '-')
        site = self.site_packages()
        if site:
            for dist in glob.glob(os.path.join(site, '*.dist-info')):
                base = os.path.basename(dist)[:-len('.dist-info')]
                if base.partition('-')[0].lower().replace('_', '-') == target:
                    url = self._metadata_url(os.path.join(dist, 'METADATA'))
                    if url:
                        return url
                    break
        return f'https://pypi.org/project/{target}/'

    def _metadata_url(self, path):
        home = None
        projects = {}
        try:
            with open(path, encoding='utf-8') as fh:
                for line in fh:
                    if not line.strip():
                        break  # headers end at the first blank line
                    if line.startswith('Home-page:'):
                        home = line.split(':', 1)[1].strip()
                    elif line.startswith('Project-URL:'):
                        label, _sep, url = line.split(':', 1)[1].partition(',')
                        if url.strip():
                            projects[label.strip().lower()] = url.strip()
        except OSError:
            return None
        for key in ('homepage', 'home', 'source', 'source code', 'repository',
                    'github'):
            if key in projects:
                return projects[key]
        return home or next(iter(projects.values()), None)

    def missing(self, requirements):
        have = self.installed()
        result = []
        for req in requirements:
            name = requirement_name(req).lower().replace('_', '-')
            if name and name not in have:
                result.append(req)
        return result

    # Build and install

    def _venv_python(self):
        # Build the venv with a real Python of the running version so wheels
        # match. sys.executable may be the app launcher in a packaged build, so
        # prefer an explicit pythonX.Y, then python3, then sys.executable.
        for cand in (f'python{self._pyver()}', 'python3'):
            found = shutil.which(cand)
            if found:
                return found
        return sys.executable

    def create(self):
        os.makedirs(os.path.dirname(self.path()), exist_ok=True)
        try:
            subprocess.run([self._venv_python(), '-m', 'venv', self.path()],
                           check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or str(error)).strip()
            raise RuntimeError(
                detail + '\nOn Debian/Ubuntu install the python3-venv package.') from error
        with open(self._marker_file(), 'w', encoding='utf-8') as fh:
            fh.write(self._pyver())

    def install_async(self, requirements):
        """Create the venv if needed and pip-install requirements in a thread.

        Emits install-started, then install-progress(line) per output line, then
        install-finished(ok, message). Signals are marshalled to the main loop.
        """
        if self._busy:
            return
        self._busy = True
        self.emit('install-started')
        run_in_background(
            lambda: self._install_worker(list(requirements)),
            on_error=lambda error: self._finish(False, str(error)),
            name='venv-install')

    def _emit_idle(self, name, *args):
        GLib.idle_add(self.emit, name, *args)

    def _install_worker(self, requirements):
        """Runs off the main loop. A failure here reaches the on_error passed to
        run_in_background, which reports it through install-finished."""
        if self.stale():
            self._emit_idle('install-progress', 'Rebuilding virtualenv…')
            shutil.rmtree(self.path(), ignore_errors=True)
        if not self.exists():
            self._emit_idle('install-progress', 'Creating virtualenv…')
            self.create()
        self.ensure_on_syspath()
        if not requirements:
            self._finish(True, 'No libraries required.')
            return
        # Install one requirement per pip call. pip prints no percentages
        # through a pipe (its progress bars need a TTY), so the package
        # boundary is the honest unit of progress for a determinate bar.
        total = len(requirements)
        for done, req in enumerate(requirements):
            self._emit_idle('install-progress',
                            f'Installing {req} ({done + 1}/{total})…')
            proc = subprocess.Popen(
                [self.python_bin(), '-m', 'pip', 'install', '--upgrade', req],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for raw in proc.stdout:
                line = raw.rstrip()
                if line:
                    self._emit_idle('install-progress', line)
            proc.wait()
            if proc.returncode != 0:
                self._finish(False, f'pip failed installing "{req}" '
                                    f'(exit code {proc.returncode}).')
                return
            self._emit_idle('install-fraction', (done + 1) / total)
        self._finish(True, 'Libraries installed.')

    def _finish(self, ok, message):
        self._busy = False
        self._emit_idle('install-finished', ok, message)

    def remove(self):
        if os.path.isdir(self.path()):
            shutil.rmtree(self.path(), ignore_errors=True)
            self.log.info('Removed external libraries virtualenv')
