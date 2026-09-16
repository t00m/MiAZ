#!/usr/bin/python3

"""
# File: fsprobe.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Count the filesystem work each MiAZ interaction costs

Local storage hides the cost of reading documents, so a repository on a remote
mount behaves nothing like the same repository on an SSD. What predicts remote
behaviour is the number of filesystem round trips and the number of bytes read,
and both can be counted on local storage without mounting anything.

This module patches the filesystem calls MiAZ uses, counts them per scenario,
and projects a time for a link of a given round trip time and bandwidth. The
projection is a model, not a measurement: see RemoteLink.

Run it against a repository:

    python3 scripts/devel/fsprobe.py --repo ~/Documents/testing/MiAZ/FVM

Never point it at the personal repository. Some scenarios write thumbnails.
"""

import argparse
import builtins
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# Import MiAZ from the checkout this script lives in, not from an installed copy.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class Counters:
    """What one scenario cost, in operations and bytes."""

    def __init__(self, name):
        self.name = name
        self.stat = 0
        self.scandir = 0
        self.dirents = 0
        self.listdir = 0
        self.opened = 0
        self.bytes_read = 0
        # Bytes a helper process read from the repository, charged at the full
        # size of every repository file it was handed.
        self.subprocess_bytes = 0
        self.wall = 0.0

    @property
    def metadata_ops(self):
        return self.stat + self.scandir + self.listdir

    @property
    def total_bytes(self):
        return self.bytes_read + self.subprocess_bytes


class _ReadCounter:
    """Wraps a file object and adds up what is actually read from it.

    Only the read methods are overridden. Everything else is delegated, so a
    caller cannot tell the difference. Counting at this level matters because
    some MiAZ readers take only the edges of a large file.
    """

    def __init__(self, handle, probe):
        self._handle = handle
        self._probe = probe

    def read(self, *args, **kwargs):
        data = self._handle.read(*args, **kwargs)
        self._probe.add_bytes(len(data))
        return data

    def readline(self, *args, **kwargs):
        data = self._handle.readline(*args, **kwargs)
        self._probe.add_bytes(len(data))
        return data

    def readlines(self, *args, **kwargs):
        lines = self._handle.readlines(*args, **kwargs)
        self._probe.add_bytes(sum(len(line) for line in lines))
        return lines

    def readinto(self, buffer):
        count = self._handle.readinto(buffer)
        self._probe.add_bytes(count or 0)
        return count

    def __iter__(self):
        for line in self._handle:
            self._probe.add_bytes(len(line))
            yield line

    def __enter__(self):
        self._handle.__enter__()
        return self

    def __exit__(self, *args):
        return self._handle.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self._handle, name)


class FSProbe:
    """Counts filesystem work under one directory tree.

    Patching os.stat is enough to catch os.path.exists, isfile, isdir and
    getsize as well: they all reach os.stat through genericpath. os.scandir is
    counted separately because its entries answer is_file() from the directory
    entry itself, which is the whole reason MiAZ uses it for listing.

    Calls touching paths outside `root` are ignored. The application also reads
    its own source, its configuration under HOME and the thumbnail cache, and
    none of those live on the remote mount.

    subprocess.run is patched too. A helper like pdftoppm reads its input
    outside Python, so nothing above would see it, and for thumbnails that is
    most of the traffic. Every argument that names a file inside the repository
    is charged at its full size when the process starts. That is an upper
    bound: pdftoppm rendering page one of a linearised PDF may read less.
    """

    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.current = None
        # One Counters per finished scenario, in the order they ran.
        self.results = []
        self._lock = threading.Lock()
        self._originals = {}

    def _in_scope(self, path):
        try:
            resolved = os.fspath(path)
        except TypeError:
            return False
        if not isinstance(resolved, (str, bytes)):
            return False
        if isinstance(resolved, bytes):
            resolved = resolved.decode('utf-8', 'replace')
        if not os.path.isabs(resolved):
            resolved = os.path.abspath(resolved)
        # The root itself counts, not only what is under it: listing the
        # repository directory is the most common operation there is.
        return resolved == self.root or resolved.startswith(self.root + os.sep)

    def add_bytes(self, count):
        with self._lock:
            if self.current is not None:
                self.current.bytes_read += count

    def _bump(self, field, amount=1):
        with self._lock:
            if self.current is not None:
                setattr(self.current, field, getattr(self.current, field) + amount)

    def start(self):
        self._originals = {
            'stat': os.stat,
            'lstat': os.lstat,
            'scandir': os.scandir,
            'listdir': os.listdir,
            'open': builtins.open,
            'run': subprocess.run,
        }
        probe = self

        def stat(path, *args, **kwargs):
            if probe._in_scope(path):
                probe._bump('stat')
            return probe._originals['stat'](path, *args, **kwargs)

        def lstat(path, *args, **kwargs):
            if probe._in_scope(path):
                probe._bump('stat')
            return probe._originals['lstat'](path, *args, **kwargs)

        def scandir(path='.'):
            entries = probe._originals['scandir'](path)
            if not probe._in_scope(path):
                return entries
            probe._bump('scandir')
            # Materialise so the entries can be counted, then hand back an
            # iterator that still works as a context manager.
            items = list(entries)
            probe._bump('dirents', len(items))
            return _ScandirResult(items, entries)

        def listdir(path='.'):
            names = probe._originals['listdir'](path)
            if probe._in_scope(path):
                probe._bump('listdir')
                probe._bump('dirents', len(names))
            return names

        def opener(file, mode='r', *args, **kwargs):
            handle = probe._originals['open'](file, mode, *args, **kwargs)
            if not probe._in_scope(file):
                return handle
            probe._bump('opened')
            if any(flag in mode for flag in ('w', 'a', 'x')) and '+' not in mode:
                return handle
            return _ReadCounter(handle, probe)

        def run(argv, *args, **kwargs):
            # The helper reads its input itself, so charge every repository
            # file it was handed. Sizes come from the unpatched stat so the
            # accounting does not count itself as a metadata operation.
            if isinstance(argv, (list, tuple)):
                for item in argv:
                    if isinstance(item, str) and probe._in_scope(item):
                        try:
                            size = probe._originals['stat'](item).st_size
                        except OSError:
                            continue
                        probe._bump('subprocess_bytes', size)
            return probe._originals['run'](argv, *args, **kwargs)

        os.stat = stat
        os.lstat = lstat
        os.scandir = scandir
        os.listdir = listdir
        builtins.open = opener
        subprocess.run = run

    def stop(self):
        for name, original in self._originals.items():
            if name == 'open':
                builtins.open = original
            elif name == 'run':
                subprocess.run = original
            else:
                setattr(os, name, original)
        self._originals = {}

    def measure(self, name):
        """Context manager collecting one scenario into its own Counters."""
        return _Scenario(self, name)


class _ScandirResult:
    """Keeps os.scandir usable as both an iterator and a context manager."""

    def __init__(self, items, original):
        self._items = items
        self._original = original

    def __iter__(self):
        return iter(self._items)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        close = getattr(self._original, 'close', None)
        if close is not None:
            close()
        return False


class _Scenario:
    def __init__(self, probe, name):
        self.probe = probe
        self.counters = Counters(name)

    def __enter__(self):
        self.probe.current = self.counters
        self.counters.wall = time.perf_counter()
        return self.counters

    def __exit__(self, *args):
        self.counters.wall = time.perf_counter() - self.counters.wall
        self.probe.current = None
        self.probe.results.append(self.counters)
        return False


class RemoteLink:
    """Projects a wall time for a link from the counted operations.

    The model is deliberately simple and stated rather than hidden:

    - one metadata operation costs one round trip
    - one open costs one round trip
    - a directory listing costs one extra round trip per 100 entries, which is
      the batch size the watcher asks GIO for
    - bytes cost time at the given bandwidth

    It ignores read-ahead, server side caching and parallelism, so it is a
    floor for latency bound work rather than a prediction. Its value is
    comparing two scenarios on the same assumptions.
    """

    def __init__(self, rtt_ms, mbps):
        self.rtt = rtt_ms / 1000.0
        self.bytes_per_second = mbps * 1_000_000 / 8

    def project(self, counters):
        trips = counters.metadata_ops + counters.opened
        trips += counters.dirents // 100
        transfer = counters.total_bytes / self.bytes_per_second
        return trips * self.rtt + transfer


def build_app(home):
    """A headless MiAZ with its configuration under home, no repository yet.

    MiAZ.env resolves LPATH from the expanded home directory, so HOME has to be
    set before it is imported. Nothing here touches the real ~/.MiAZ.
    """
    os.environ['HOME'] = home
    os.makedirs(home, exist_ok=True)

    from MiAZ.env import ENV
    from MiAZ.frontend.console.app import MiAZConsoleApp

    for key in ('ETC', 'VAR', 'CACHE', 'TMP', 'LOG', 'DB', 'REPOS'):
        path = ENV['LPATH'].get(key)
        if path:
            os.makedirs(path, exist_ok=True)

    return MiAZConsoleApp(ENV), ENV


def scenario_open(app, probe, repo_path):
    """Opening a repository: read its .conf, list it, build the index.

    This is the cold path, the one a repository switch pays. Every
    configuration file lives in .conf inside the repository, so on a remote
    mount they are remote reads.
    """
    with probe.measure('repository open (cold)'):
        code, message = app.open_repository(repo_path)
    if code != 0:
        raise SystemExit(f"cannot open repository: {message}")


def scenario_index(app, probe):
    """A re-scan, which is what the watcher triggers on any change.

    The configuration is cached by now, so this is the listing plus the index
    rebuild and nothing else.
    """
    index = app.get_service('index')
    with probe.measure('index rebuild (watcher)'):
        index.reload()


def scenario_listing(app, probe):
    """The bare directory listing the index is built from."""
    util = app.get_service('util')
    repo = app.get_service('repo')
    with probe.measure('directory listing'):
        util.get_files(repo.docs)


def scenario_watcher_poll(app, probe):
    """One remote watcher poll, which happens every 2 seconds.

    files_with_timestamp_async asks GIO for standard::name, standard::type and
    time::modified in one enumeration, so the modification times arrive with
    the batch rather than costing a stat each. Plain scandir is the closest
    countable equivalent: one listing, and the projection charges a round trip
    per batch of entries.
    """
    repo = app.get_service('repo')
    with probe.measure('watcher poll (one tick)'):
        with os.scandir(repo.docs) as entries:
            list(entries)


def scenario_thumbnails(app, probe, cache_dir, count, scale, label):
    """What a screen of thumbnail cells costs.

    The grid binds one cell per visible document and each cell calls
    request_thumbnail, which calls thumbnail_for. Calling thumbnail_for
    directly is the same filesystem work without needing a display.
    """
    from MiAZ.backend.thumbnails import thumbnail_for

    util = app.get_service('util')
    repo = app.get_service('repo')
    docs = util.get_files(repo.docs)[:count]
    with probe.measure(label):
        for path in docs:
            thumbnail_for(path, cache_dir, scale=scale)


def scenario_duplicates(app, probe):
    """The duplicate scan review mode starts on its own."""
    from MiAZ.backend.duplicates import find_duplicates

    util = app.get_service('util')
    repo = app.get_service('repo')
    docs = util.get_files(repo.docs)
    with probe.measure('duplicate scan (review mode)'):
        find_duplicates(docs)


def human_bytes(count):
    if count < 1024:
        return f"{count} B"
    for unit in ('KB', 'MB', 'GB'):
        count /= 1024.0
        if count < 1024:
            return f"{count:.1f} {unit}"
    return f"{count:.1f} TB"


def print_table(rows, link):
    headers = ('scenario', 'meta ops', 'opens', 'read', 'helper read', 'local',
               f'@{link.rtt*1000:.0f}ms')
    widths = [len(h) for h in headers]
    body = []
    for counters in rows:
        cells = (
            counters.name,
            f"{counters.metadata_ops:,}",
            f"{counters.opened:,}",
            human_bytes(counters.bytes_read),
            human_bytes(counters.subprocess_bytes),
            f"{counters.wall:.2f}s",
            f"{link.project(counters):.1f}s",
        )
        body.append(cells)
        widths = [max(w, len(c)) for w, c in zip(widths, cells)]

    line = '  '.join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print('  '.join('-' * w for w in widths))
    for cells in body:
        print('  '.join(c.ljust(w) for c, w in zip(cells, widths)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[4])
    parser.add_argument('--repo', required=True,
                        help='repository to measure, never the personal one')
    parser.add_argument('--cells', type=int, default=24,
                        help='documents on one grid screen (default 24)')
    parser.add_argument('--walk', type=int, default=10,
                        help='documents visited in the preview walk (default 10)')
    parser.add_argument('--grid-scale', type=int, default=256,
                        help='thumbnail width a grid cell asks for')
    parser.add_argument('--preview-scale', type=int, default=640,
                        help='thumbnail width the preview sheet asks for')
    parser.add_argument('--rtt-ms', type=float, default=40.0,
                        help='round trip time to project for (default 40)')
    parser.add_argument('--mbps', type=float, default=100.0,
                        help='link bandwidth to project for (default 100)')
    parser.add_argument('--keep-cache', action='store_true',
                        help='keep the thumbnail cache directory afterwards')
    args = parser.parse_args()

    repo_path = os.path.realpath(os.path.expanduser(args.repo))
    if not os.path.isdir(repo_path):
        raise SystemExit(f"not a directory: {repo_path}")

    workdir = tempfile.mkdtemp(prefix='miaz-fsprobe-')
    home = os.path.join(workdir, 'home')
    cache_dir = os.path.join(workdir, 'thumbnails')
    os.makedirs(cache_dir, exist_ok=True)

    app, _env = build_app(home)
    probe = FSProbe(repo_path)
    link = RemoteLink(args.rtt_ms, args.mbps)

    probe.start()
    try:
        scenario_open(app, probe, repo_path)
        scenario_index(app, probe)
        scenario_listing(app, probe)
        scenario_watcher_poll(app, probe)
        scenario_thumbnails(app, probe, cache_dir, args.cells,
                            args.grid_scale, 'grid screen, cold cache')
        scenario_thumbnails(app, probe, cache_dir, args.cells,
                            args.grid_scale, 'grid screen, warm cache')
        scenario_thumbnails(app, probe, cache_dir, args.walk,
                            args.preview_scale, 'preview walk, cold cache')
        scenario_thumbnails(app, probe, cache_dir, args.walk,
                            args.preview_scale, 'preview walk, warm cache')
        scenario_duplicates(app, probe)
    finally:
        probe.stop()

    print(f"repository: {repo_path}")
    print(f"projection: {args.rtt_ms:.0f} ms round trip, {args.mbps:.0f} Mbit/s\n")
    print_table(probe.results, link)
    print("\nThe projection is a model, not a measurement. See RemoteLink.")

    if args.keep_cache:
        print(f"\nthumbnail cache kept at {cache_dir}")
    else:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    main()
