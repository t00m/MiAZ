#!/usr/bin/python3

"""Write each plugin's .plugin file from the plugin_info in its module.

A plugin declares itself twice: in plugin_info, which the running plugin reads,
and in the .plugin file, which libpeas and the command line read before any
module is imported. This generates the second from the first, so the two
cannot drift.

Usage:

    PYTHONPATH=. python scripts/devel/create_plugin_definitions.py data/resources/plugins
    PYTHONPATH=. python scripts/devel/create_plugin_definitions.py --check data/resources/plugins

--check writes nothing and exits 1 when a file on disk differs from what would
be written. tests/test_plugin_definitions.py makes the same comparison, so the
check is there for a pre-commit hook or a quick look by hand.
"""

import argparse
import ast
import glob
import os
import sys

import gi
gi.require_version('Peas', '2')

from MiAZ.backend.plugins import plugin_definition_text
from MiAZ.backend.util import SafeDictExtractor


def read_plugin_info(module_path):
    """The plugin_info dict of one module, or None when it has none."""
    with open(module_path, encoding='utf-8') as handler:
        tree = ast.parse(handler.read(), filename=module_path)
    extractor = SafeDictExtractor('plugin_info')
    extractor.visit(tree)
    return extractor.result


def definition_path(module_path):
    """The .plugin file that belongs beside this module."""
    return module_path[:-len('.py')] + '.plugin'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plugins_dir',
                        help='the directory holding one directory per plugin')
    parser.add_argument('--check', action='store_true',
                        help='compare instead of writing, exit 1 on any difference')
    args = parser.parse_args()

    root = os.path.abspath(args.plugins_dir)
    if not os.path.isdir(root):
        parser.error(f"'{args.plugins_dir}' is not a directory")

    stale = 0
    for module_path in sorted(glob.glob(os.path.join(root, '*', '*.py'))):
        plugin_info = read_plugin_info(module_path)
        if plugin_info is None:
            continue
        text = plugin_definition_text(plugin_info)
        target = definition_path(module_path)
        current = None
        if os.path.exists(target):
            with open(target, encoding='utf-8') as handler:
                current = handler.read()
        if current == text:
            continue
        stale += 1
        if args.check:
            print(f'stale: {target}')
            continue
        with open(target, 'w', encoding='utf-8') as handler:
            handler.write(text)
        print(f'written: {target}')

    if args.check and stale:
        print(f'{stale} definition(s) do not match their module')
        return 1
    if not args.check:
        print(f'{stale} definition(s) updated')
    return 0


if __name__ == '__main__':
    sys.exit(main())
