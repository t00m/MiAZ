#!/usr/bin/env python3
# Copyright 2019-2025 Tomás Vírseda
# SPDX-License-Identifier: GPL-3.0-or-later

"""Build the user help with KB4IT for meson.

Called by the 'help' custom_target in meson.build. The sources stay in the
source tree: KB4IT reads help/source/ and writes the site into the build
directory, never into help/. It needs a config whose paths point there, so a
copy of help/config/repo.json is written into a work directory with source,
target and contract made absolute. KB4IT keeps its cache in that work
directory too.

With --mode enabled a failed build fails meson. With --mode auto (the
default of the 'help' option) a failure is a warning: a KB4IT that predates
the apphelp DocType rules refuses these pages, and that should not stop
anyone installing MiAZ. The site built by hand in help/target is used
instead when there is one; otherwise nothing is installed and the help
window opens the published site.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


def warn(message):
    print(f'help: {message}', file=sys.stderr)


def write_config(help_dir, work_dir, output):
    with open(os.path.join(help_dir, 'config', 'repo.json'), encoding='utf-8') as fh:
        repo = json.load(fh)
    repo['source'] = os.path.join(help_dir, 'source')
    repo['target'] = output
    block = repo.setdefault('apphelp', {})
    block['contract'] = os.path.join(help_dir, block.get('contract', 'config/contract.txt'))
    config_dir = os.path.join(work_dir, 'config')
    os.makedirs(config_dir, exist_ok=True)
    path = os.path.join(config_dir, 'repo.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(repo, fh, indent=4, ensure_ascii=False)
    return path


def fall_back(help_dir, output, reason):
    """Install what was built by hand, or nothing."""
    prebuilt = os.path.join(help_dir, 'target')
    if os.path.isfile(os.path.join(prebuilt, 'go.html')):
        warn(f'{reason}; installing the copy already built in {prebuilt}')
        shutil.copytree(prebuilt, output)
    else:
        warn(f'{reason}; no help installed, the help window will open the published site')
        os.makedirs(output, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--kb4it', required=True, help='the kb4it executable')
    parser.add_argument('--help-dir', required=True, help='help/ in the source tree')
    parser.add_argument('--output', required=True, help='where the site goes')
    parser.add_argument('--work', required=True, help='scratch directory for KB4IT')
    parser.add_argument('--mode', choices=('auto', 'enabled'), default='auto')
    args = parser.parse_args()

    help_dir = os.path.abspath(args.help_dir)
    output = os.path.abspath(args.output)
    work_dir = os.path.abspath(args.work)
    # A clean target every time: KB4IT deploys incrementally, and a page
    # removed from help/source must not survive in the installed site.
    shutil.rmtree(output, ignore_errors=True)

    config = write_config(help_dir, work_dir, output)
    result = subprocess.run([args.kb4it, 'build', config, '--force'],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    built = result.returncode == 0 and os.path.isfile(os.path.join(output, 'go.html'))
    if built:
        print(f'help: built with KB4IT into {output}')
        return 0

    problems = [line.strip() for line in result.stdout.splitlines()
                if 'ERROR' in line or 'WARNING' in line]
    reason = f'KB4IT could not build the help (exit {result.returncode})'
    if args.mode == 'enabled':
        warn(reason)
        for line in problems[-20:] or result.stdout.splitlines()[-20:]:
            warn(line)
        return 1
    for line in problems[-5:]:
        warn(line)
    shutil.rmtree(output, ignore_errors=True)
    fall_back(help_dir, output, reason)
    return 0


if __name__ == '__main__':
    sys.exit(main())
