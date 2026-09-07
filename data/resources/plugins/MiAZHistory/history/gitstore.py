"""The git repository behind MiAZHistory, and nothing else.

No gi import here on purpose: every rule about what a step is, and what
stepping back does, is testable without a display.

The timeline is not the commit chain. Applying a state is itself recorded, so
the chain interleaves what the user did with the undoing of it. The states the
user actually made are listed in .git/miaz-history.json, and `index` says which
one is on disk.
"""

import os
import json
import shutil
import subprocess

STATE_FILE = 'miaz-history.json'
STATE_VERSION = 1

# Repository local, so a user's own git identity is neither needed nor borrowed.
GIT_NAME = 'MiAZ'
GIT_EMAIL = 'miaz@localhost'

PLUGIN_NAME = 'MiAZHistory'
PLUGIN_DESCRIPTION = 'Undo and redo changes in this repository'
PLUGINS_USED = os.path.join('.conf', 'plugins-used.json')


class GitError(Exception):
    """A git command that did not return zero."""


def git_available() -> bool:
    """Whether git is installed and runs.

    A path hit is not enough: a broken symlink, or a binary the sandbox will
    not execute, answers `which` and then fails on use.
    """
    if shutil.which('git') is None:
        return False
    try:
        done = subprocess.run(['git', '--version'],
                              capture_output=True, text=True, check=False)
    except OSError:
        return False
    return done.returncode == 0


class GitStore:
    """One repository's history."""

    def __init__(self, path: str):
        self.path = path
        self.gitdir = os.path.join(path, '.git')
        self.statefile = os.path.join(self.gitdir, STATE_FILE)

    def _run(self, *args) -> str:
        done = subprocess.run(['git', '-C', self.path, *args],
                              capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise GitError(f"git {' '.join(args)}: {done.stderr.strip()}")
        return done.stdout

    def exists(self) -> bool:
        return os.path.isdir(self.gitdir)

    def is_ours(self) -> bool:
        return os.path.exists(self.statefile)

    def is_foreign(self) -> bool:
        """A git repository somebody else made. MiAZ leaves those alone."""
        return self.exists() and not self.is_ours()

    def init(self, subject: str) -> str:
        """Create the history and take the first snapshot.

        gpgsign is turned off here: a user who signs every commit globally
        would otherwise need a passphrase every time a document is filed.
        """
        self._run('-c', 'init.defaultBranch=main', 'init', '-q')
        self._run('config', 'user.name', GIT_NAME)
        self._run('config', 'user.email', GIT_EMAIL)
        self._run('config', 'commit.gpgsign', 'false')
        first = self._commit(subject, allow_empty=True)
        self._write_state([first], 0)
        return first

    def is_dirty(self) -> bool:
        return bool(self._run('status', '--porcelain').strip())

    def _commit(self, subject: str, allow_empty: bool = False) -> str:
        self._run('add', '-A')
        args = ['commit', '-q', '-m', subject]
        if allow_empty:
            args.append('--allow-empty')
        self._run(*args)
        return self._run('rev-parse', 'HEAD').strip()

    def _read_state(self) -> dict:
        try:
            with open(self.statefile, encoding='utf-8') as state:
                return json.load(state)
        except (OSError, ValueError):
            return {'version': STATE_VERSION, 'states': [], 'index': -1}

    def _write_state(self, states: list, index: int):
        payload = {'version': STATE_VERSION, 'states': states, 'index': index}
        with open(self.statefile, 'w', encoding='utf-8') as state:
            json.dump(payload, state, indent=2)

    def states(self) -> list:
        return self._read_state()['states']

    def index(self) -> int:
        return self._read_state()['index']

    def count(self) -> int:
        return len(self.states())

    def subject_of(self, revision: str) -> str:
        """The subject line of one state. Raises for a revision that is not one."""
        return self._run('show', '-s', '--format=%s', revision).strip()

    def size(self) -> int:
        """Bytes the history occupies on disk."""
        total = 0
        for root, _dirs, files in os.walk(self.gitdir):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    pass
        return total
