#!/usr/bin/env python3

from os import environ, path
from subprocess import call

prefix = environ.get('MESON_INSTALL_PREFIX', '/usr/local')
datadir = path.join(prefix, 'share')
destdir = environ.get('DESTDIR', '')

# Package managers set this so we don't need to run
if not destdir:
    print('Updating icon cache...')
    call(['gtk-update-icon-cache', '-qtf', path.join(datadir, 'icons', 'hicolor')])

    print('Updating desktop database...')
    call(['update-desktop-database', '-q', path.join(datadir, 'applications')])

    print('Compiling GSettings schemas...')
    call(['glib-compile-schemas', path.join(datadir, 'glib-2.0', 'schemas')])

    # meson already installs the launcher executable (install_mode rwxrwxr-x),
    # so this is a redundant safety net on a live install. Skip it during a
    # package build (DESTDIR set), where /usr/bin/miaz does not exist yet and the
    # chmod only prints a scary "cannot access" warning.
    print('Set the right permissions for MiAZ executable')
    call(['chmod', 'a+x', path.join(prefix, 'bin', 'miaz')])
