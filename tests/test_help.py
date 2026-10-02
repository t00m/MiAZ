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


def test_the_landing_page_prefers_the_local_copy(tmp_path):
    from MiAZ.backend.help import help_home_uri
    assert help_home_uri(None) == f'{HELP_SITE}index.html?theme=light'
    site = make_site(tmp_path)
    uri = help_home_uri(site, dark=True)
    assert uri.startswith('file://') and uri.endswith('/help/index.html?theme=dark')


def test_with_theme_swaps_only_the_theme_parameter():
    from MiAZ.backend.help import with_theme
    uri = f'{HELP_SITE}faq.html?theme=light#storage'
    assert with_theme(uri, True) == f'{HELP_SITE}faq.html?theme=dark#storage'
    assert with_theme(uri, False) == uri
    assert with_theme(f'{HELP_SITE}faq.html', True) == f'{HELP_SITE}faq.html'


# The help pages themselves. The help build catches all of this too, but it
# needs KB4IT installed and runs in its own workflow; these run with the unit
# suite, before anything is pushed.
SOURCE = os.path.join(REPO, 'help', 'source')
REQUIRED = ('DocType', 'Section', 'Order', 'Summary', 'Feature')
# Diataxis, as the apphelp theme spells it.
DOCTYPES = ('Tutorial', 'How-to guide', 'Reference', 'Explanation')
LAYOUTS = ('faq', 'tips', 'troubleshooting')


def help_pages():
    return sorted(name for name in os.listdir(SOURCE) if name.endswith('.md'))


def frontmatter(name):
    import yaml
    with open(os.path.join(SOURCE, name), encoding='utf-8') as fh:
        text = fh.read()
    assert text.startswith('---\n'), f'{name}: no frontmatter'
    block = text.split('---\n', 2)[1]
    return yaml.safe_load(block) or {}


def test_every_help_page_has_frontmatter_kb4it_can_read():
    problems = []
    for name in help_pages():
        try:
            meta = frontmatter(name)
        except Exception as error:
            problems.append(f'{name}: {error}')
            continue
        if name == 'index.md':
            continue
        if 'Kind' in meta:
            problems.append(f'{name}: Kind is replaced by DocType and Layout')
        if meta.get('DocType') and meta['DocType'] not in DOCTYPES:
            problems.append(f"{name}: DocType {meta['DocType']!r} is not one of {DOCTYPES}")
        if meta.get('Layout') and meta['Layout'] not in LAYOUTS:
            problems.append(f"{name}: Layout {meta['Layout']!r} is not one of {LAYOUTS}")
        for related in str(meta.get('Related') or '').split(','):
            if related.strip() and related.strip() not in help_pages():
                problems.append(f'{name}: Related names a missing page {related.strip()}')
        missing = [key for key in REQUIRED if not meta.get(key)]
        if missing:
            problems.append(f'{name}: missing {missing}')
        if len(str(meta.get('Summary', ''))) > 160:
            problems.append(f'{name}: Summary longer than 160 characters')
    assert problems == []


def test_the_shortcut_reference_lists_every_core_shortcut():
    """reference-shortcuts.md is written by hand from services/shortcuts.py."""
    path = os.path.join(REPO, 'MiAZ', 'frontend', 'desktop', 'services', 'shortcuts.py')
    with open(path, encoding='utf-8') as fh:
        source = fh.read()
    core = source[source.index('CORE = ('):source.index('\n)\n', source.index('CORE = ('))]
    labels = re.findall(r"\(SECTION_\w+, N_\('([^']+)'\)", core)
    assert labels, 'could not read the CORE table'
    with open(os.path.join(SOURCE, 'reference-shortcuts.md'), encoding='utf-8') as fh:
        page = fh.read()
    missing = [label for label in labels if f'| {label}' not in page]
    assert missing == [], f'shortcuts missing from the help: {missing}'


def test_plugin_help_links_name_ids_the_help_build_checks():
    plugins = os.path.join(REPO, 'data', 'resources', 'plugins')
    with open(os.path.join(REPO, 'help', 'config', 'contract.txt')) as fh:
        contract = {line.strip() for line in fh if line.strip() and not line.startswith('#')}
    missing = []
    for folder in sorted(os.listdir(plugins)):
        for name in os.listdir(os.path.join(plugins, folder)):
            if not name.endswith('.plugin'):
                continue
            with open(os.path.join(plugins, folder, name), encoding='utf-8') as fh:
                for line in fh:
                    match = re.match(r'Help=.*[?&]id=([a-z0-9._-]+)', line.strip())
                    if match and match.group(1) not in contract:
                        missing.append(f'{folder}: {match.group(1)}')
    assert missing == []
