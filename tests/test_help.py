#!/usr/bin/python3

"""The help address: installed copy first, published site second."""

import os
import re

from MiAZ.backend.help import (DEFAULT_TOPIC, HELP_SITE, help_uri,
                               is_help_uri, local_help_dir)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_site(tmp_path):
    site = tmp_path / 'help'
    site.mkdir()
    (site / 'go.html').write_text('<html></html>')
    return str(site)


def test_without_a_local_copy_the_published_site_is_used(tmp_path):
    uri = help_uri('mass-rename', str(tmp_path / 'missing'))
    assert uri == f'{HELP_SITE}go.html?id=mass-rename&theme=light'


def test_a_folder_without_go_html_is_not_a_local_copy(tmp_path):
    assert local_help_dir(str(tmp_path)) is None
    assert help_uri('faq', str(tmp_path)).startswith(HELP_SITE)


def test_the_local_copy_wins_when_it_exists(tmp_path):
    site = make_site(tmp_path)
    uri = help_uri('review', site, dark=True)
    assert uri.startswith('file://')
    assert uri.endswith('/help/go.html?id=review&theme=dark')


def test_a_missing_or_malformed_id_opens_the_first_steps(tmp_path):
    for bad in (None, '', 'Mass Rename', '../etc', 'a&b=c'):
        assert f'id={DEFAULT_TOPIC}&' in help_uri(bad, None), bad


def test_navigation_inside_the_help_stays_in_the_window(tmp_path):
    site = make_site(tmp_path)
    page = help_uri('faq', site).replace('go.html', 'faq.html')
    assert is_help_uri(page, site)
    assert is_help_uri(HELP_SITE + 'tips.html#remote', site)


def test_everything_else_goes_to_the_web_browser(tmp_path):
    site = make_site(tmp_path)
    assert not is_help_uri('https://github.com/t00m/MiAZ/edit/main/help/source/faq.md', site)
    assert not is_help_uri('file:///etc/passwd', site)
    # A sibling whose name starts like the help folder is not inside it.
    sibling = tmp_path / 'help-other'
    sibling.mkdir()
    assert not is_help_uri(sibling.as_uri() + '/x.html', site)
    assert not is_help_uri('', site)


def test_every_contract_id_is_a_valid_help_id():
    """The ids the application opens are the ones the help build checks."""
    with open(os.path.join(REPO, 'help', 'config', 'contract.txt')) as fh:
        ids = [line.strip() for line in fh
               if line.strip() and not line.startswith('#')]
    assert ids
    for help_id in ids:
        if '.html' in help_id:
            continue
        assert re.match(r'^[a-z0-9][a-z0-9._-]*$', help_id), help_id
        assert f'id={help_id}&' in help_uri(help_id, None)
