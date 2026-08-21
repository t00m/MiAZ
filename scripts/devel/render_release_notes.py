#!/usr/bin/python3

"""Render the release notes into the three files that carry them.

The notes used to be written by hand in the AppStream metainfo, in
debian/changelog and in the spec %changelog. In practice that meant written in
none of them: sync_versions.sh writes "New release. See CHANGELOG.md for
details." as a placeholder, and 0.1.50 and 0.1.60 both shipped with it still
there, because nothing checked.

They now come from one file per release:

    releases/0.2.0.md

        # 0.2.0

        One line for a software centre to show.

        - a highlight
        - another highlight

Run it after sync_versions.sh, which creates the entry this fills:

    ./scripts/devel/sync_versions.sh
    ./scripts/devel/render_release_notes.py

Both are safe to run again: this replaces the notes for the current version
wherever it finds them, and leaves every older entry alone.
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
METAINFO = os.path.join(ROOT, 'data', 'io.github.t00m.MiAZ.metainfo.xml.in')
DEBIAN = os.path.join(ROOT, 'debian', 'changelog')
SPEC = os.path.join(ROOT, 'miaz.spec')
MESON = os.path.join(ROOT, 'meson.build')

# What sync_versions.sh writes when there is nothing to say yet.
PLACEHOLDER = re.compile(r'^(New release\.\s*)?See CHANGELOG\.md for details\.$')

# &, < and > in a highlight would make the metainfo invalid. They are rare in
# this text, so escaping is enough and there is no need for an XML writer that
# would reformat the whole file.
XML_ESCAPES = (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'))


def is_placeholder(line: str) -> bool:
    return bool(PLACEHOLDER.match(line.strip()))


def xml_escape(text: str) -> str:
    for raw, escaped in XML_ESCAPES:
        text = text.replace(raw, escaped)
    return text


def source_path(version: str) -> str:
    return os.path.join(ROOT, 'releases', f'{version}.md')


def read_version() -> str:
    """The release version from meson.build, build metadata stripped.

    meson.build owns the version, as it does for sync_versions.sh. '+build.N'
    is a build counter and has no place in a release history.
    """
    text = open(MESON, encoding='utf-8').read()
    found = re.search(r"version\s*:\s*'([^']+)'", text)
    if not found:
        raise LookupError('no version in meson.build')
    return found.group(1).split('+')[0]


def parse_source(text: str):
    """Return (version, summary, bullets) from a releases/<version>.md file."""
    heading = re.search(r'^#\s+(\S+)\s*$', text, re.MULTILINE)
    if not heading:
        raise ValueError("the file must start with '# <version>'")
    version = heading.group(1)

    body = text[heading.end():]
    bullets = [line[2:].strip() for line in body.splitlines()
               if line.startswith('- ') and line[2:].strip()]

    # The summary is the first paragraph, not the first line: a sentence long
    # enough to say anything gets wrapped in the file, and taking one line of
    # it truncates it mid-clause in every software centre that shows it.
    summary_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('- '):
            if summary_lines:
                break
            continue
        summary_lines.append(stripped)

    if not summary_lines:
        raise ValueError(f'{version}: no summary line, which is what a software '
                         f'centre shows first')
    if not bullets:
        raise ValueError(f'{version}: no "- " highlights, which would publish an '
                         f'empty list in three places')
    return version, ' '.join(summary_lines), bullets


def render_metainfo(text: str, version: str, summary: str, bullets) -> str:
    """Replace the <description> of this version's <release>, and only that one."""
    pattern = re.compile(
        r'(<release version="' + re.escape(version) + r'"[^>]*>\n)'
        r'(.*?)'
        r'(\n\s*</release>)', re.DOTALL)
    found = pattern.search(text)
    if not found:
        raise LookupError(f'no <release version="{version}"> in the metainfo; '
                          f'run sync_versions.sh first')
    indent = ' ' * 6
    lines = [f'{indent}<description>',
             f'{indent}  <p>{xml_escape(summary)}</p>',
             f'{indent}  <ul>']
    lines += [f'{indent}    <li>{xml_escape(bullet)}</li>' for bullet in bullets]
    lines += [f'{indent}  </ul>', f'{indent}</description>']
    return text[:found.start(2)] + '\n'.join(lines) + text[found.end(2):]


def render_debian(text: str, version: str, bullets) -> str:
    """Replace the '  * ' lines of this version's stanza, keeping the trailer."""
    pattern = re.compile(
        r'(^miaz \(' + re.escape(version) + r'-\d+\)[^\n]*\n\n)'
        r'((?:  \*[^\n]*\n)+)', re.MULTILINE)
    found = pattern.search(text)
    if not found:
        raise LookupError(f'no debian/changelog stanza for {version}; '
                          f'run sync_versions.sh first')
    body = ''.join(f'  * {bullet}\n' for bullet in bullets)
    return text[:found.start(2)] + body + text[found.end(2):]


def render_spec(text: str, version: str, bullets) -> str:
    """Replace the '- ' lines of this version's %changelog entry."""
    pattern = re.compile(
        r'(^\*[^\n]*-\s*' + re.escape(version) + r'-\d+\n)'
        r'((?:-[^\n]*\n)+)', re.MULTILINE)
    found = pattern.search(text)
    if not found:
        raise LookupError(f'no miaz.spec %changelog entry for {version}; '
                          f'run sync_versions.sh first')
    body = ''.join(f'- {bullet}\n' for bullet in bullets)
    return text[:found.start(2)] + body + text[found.end(2):]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--version', help='render this version instead of the '
                                          'one in meson.build')
    parser.add_argument('--check', action='store_true',
                        help='report what would change and exit 1 if anything '
                             'would, without writing')
    args = parser.parse_args(argv)

    version = args.version or read_version()
    path = source_path(version)
    if not os.path.exists(path):
        sys.stderr.write(
            f'no release notes for {version}.\n'
            f'Write {os.path.relpath(path, ROOT)} with a summary line and '
            f'"- " highlights, then run this again.\n')
        return 2

    declared, summary, bullets = parse_source(open(path, encoding='utf-8').read())
    if declared != version:
        sys.stderr.write(f'{os.path.relpath(path, ROOT)} says {declared}, '
                         f'meson.build says {version}\n')
        return 2

    work = (
        (METAINFO, lambda t: render_metainfo(t, version, summary, bullets)),
        (DEBIAN, lambda t: render_debian(t, version, bullets)),
        (SPEC, lambda t: render_spec(t, version, bullets)),
    )

    changed = []
    for target, render in work:
        before = open(target, encoding='utf-8').read()
        after = render(before)
        if before == after:
            continue
        changed.append(os.path.relpath(target, ROOT))
        if not args.check:
            open(target, 'w', encoding='utf-8').write(after)

    if args.check:
        for name in changed:
            print(f'would rewrite {name}')
        if changed:
            sys.stderr.write(f'{len(changed)} file(s) do not match '
                             f'{os.path.relpath(path, ROOT)}\n')
            return 1
        print(f'release notes for {version} are in place')
        return 0

    for name in changed:
        print(f'rewrote {name}')
    if not changed:
        print(f'release notes for {version} were already in place')
    return 0


if __name__ == '__main__':
    sys.exit(main())
