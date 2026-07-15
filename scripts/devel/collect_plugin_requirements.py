#!/usr/bin/env python3
"""Collect plugin requirements into a single manifest.

Scans data/resources/plugins/<Plugin>/ for a requirements.txt and the plugin
module name (the Module= key in its .plugin file) and writes
data/resources/plugins-requirements.json mapping module name to its list of
requirements. Run at build time. The app also reads each requirements.txt
directly, so this manifest is an aggregate index for validation and offline use.
"""

import json
import os
import sys


def module_name(plugin_dir):
    for name in os.listdir(plugin_dir):
        if name.endswith('.plugin'):
            with open(os.path.join(plugin_dir, name), encoding='utf-8') as fh:
                for line in fh:
                    if line.strip().startswith('Module='):
                        return line.split('=', 1)[1].strip()
    return os.path.basename(plugin_dir)


def read_requirements(path):
    reqs = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith('#'):
                reqs.append(line)
    return reqs


def main():
    here = os.path.abspath(__file__)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    plugins_dir = os.path.join(repo_root, 'data', 'resources', 'plugins')
    out_path = os.path.join(repo_root, 'data', 'resources', 'plugins-requirements.json')

    manifest = {}
    for entry in sorted(os.listdir(plugins_dir)):
        pdir = os.path.join(plugins_dir, entry)
        req = os.path.join(pdir, 'requirements.txt')
        if os.path.isdir(pdir) and os.path.isfile(req):
            manifest[module_name(pdir)] = read_requirements(req)

    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write('\n')

    total = sum(len(v) for v in manifest.values())
    print(f'Wrote {out_path}: {total} requirements across {len(manifest)} plugins')
    return 0


if __name__ == '__main__':
    sys.exit(main())
