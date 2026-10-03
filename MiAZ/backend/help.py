# Copyright 2019-2025 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Where the user help is and how to address one of its topics.

The help is a static site built from help/ by KB4IT. Every topic the
application opens has a help id, and the site's go.html turns an id into the
right page and section, so the application never names a page:

    go.html?id=mass-rename  ->  howto-mass-rename.html

The copy installed with MiAZ is preferred: it works offline and documents the
version that is running. The published site is the fallback. No toolkit here;
the window that shows the result lives in widgets/helpwindow.py.
"""

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlsplit

HELP_SITE = 'https://t00m.github.io/MiAZ/'
DEFAULT_TOPIC = 'first-steps'
ENTRY_PAGE = 'go.html'

# The same rule KB4IT's apphelp theme applies to a HelpId, so an id that passes
# here is one the site can have.
HELP_ID_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')


def local_help_dir(help_dir: Optional[str]) -> Optional[str]:
    """The installed help directory, or None when there is no usable copy."""
    if help_dir and os.path.isfile(os.path.join(help_dir, ENTRY_PAGE)):
        return help_dir
    return None


def help_uri(help_id: Optional[str] = None,
             help_dir: Optional[str] = None,
             dark: bool = False) -> str:
    """The address that opens one help topic.

    An empty or malformed id opens the default topic rather than a page that
    says the topic does not exist: the caller is the application, and a typo
    in it is not something the user can do anything about.
    """
    if not help_id or not HELP_ID_RE.match(help_id):
        help_id = DEFAULT_TOPIC
    query = urlencode({'id': help_id, 'theme': 'dark' if dark else 'light'})
    local = local_help_dir(help_dir)
    if local is not None:
        base = Path(local, ENTRY_PAGE).resolve().as_uri()
    else:
        base = HELP_SITE + ENTRY_PAGE
    return f'{base}?{query}'


def is_help_uri(uri: str, help_dir: Optional[str] = None) -> bool:
    """Whether a navigation stays inside the help.

    Anything else (the GitHub repository from an "Edit this page" link, a
    vendor website named in a page) belongs in the user's web browser.
    """
    if not uri:
        return False
    if uri.startswith(HELP_SITE):
        return True
    local = local_help_dir(help_dir)
    if local is None:
        return False
    parts = urlsplit(uri)
    if parts.scheme != 'file':
        return False
    root = Path(local).resolve().as_uri().rstrip('/') + '/'
    return f'{parts.scheme}://{parts.netloc}{parts.path}'.startswith(root)


def help_home_uri(help_dir: Optional[str] = None, dark: bool = False) -> str:
    """The address of the help landing page, for browsing rather than a topic."""
    query = urlencode({'theme': 'dark' if dark else 'light'})
    local = local_help_dir(help_dir)
    if local is not None:
        base = Path(local, 'index.html').resolve().as_uri()
    else:
        base = HELP_SITE + 'index.html'
    return f'{base}?{query}'


def with_theme(uri: str, dark: bool) -> str:
    """The same help address in the other colour scheme.

    The site keeps the theme parameter on every link, so a page reached from
    one opened in light stays light. Swapping it is how a view follows the
    desktop when it switches. An address without the parameter is returned
    as it is.
    """
    old, new = ('theme=light', 'theme=dark') if dark else ('theme=dark', 'theme=light')
    return uri.replace(old, new) if old in uri else uri
