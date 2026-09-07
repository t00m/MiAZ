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

    def record(self, subject: str):
        """Record whatever changed as a new state, or None when nothing did.

        A state recorded while stepped back drops everything ahead of it. That
        is the text-editor rule: a change made after stepping back is a new
        branch of the user's work, and the states that were waiting to be
        stepped forward into are not offered again.
        """
        if not self.is_dirty():
            return None
        commit = self._commit(subject)
        state = self._read_state()
        states = state['states'][:state['index'] + 1] + [commit]
        self._write_state(states, len(states) - 1)
        return commit

    def can_undo(self) -> bool:
        return self._read_state()['index'] > 0

    def can_redo(self) -> bool:
        state = self._read_state()
        return state['index'] < len(state['states']) - 1

    def pending_undo(self):
        """(older, newer): the change a step back would take away, or None."""
        state = self._read_state()
        if state['index'] <= 0:
            return None
        return (state['states'][state['index'] - 1], state['states'][state['index']])

    def pending_redo(self):
        """(older, newer): the change a step forward would bring back, or None."""
        state = self._read_state()
        if state['index'] >= len(state['states']) - 1:
            return None
        return (state['states'][state['index']], state['states'][state['index'] + 1])

    def step_back(self, subject: str):
        state = self._read_state()
        if state['index'] <= 0:
            return None
        target = state['states'][state['index'] - 1]
        self._apply(target, subject)
        self._write_state(state['states'], state['index'] - 1)
        return target

    def step_forward(self, subject: str):
        state = self._read_state()
        if state['index'] >= len(state['states']) - 1:
            return None
        target = state['states'][state['index'] + 1]
        self._apply(target, subject)
        self._write_state(state['states'], state['index'] + 1)
        return target

    def _apply(self, target: str, subject: str):
        """Put the tree of `target` on disk, and record having done so.

        read-tree writes the index and the working tree in one go, adding,
        changing and deleting exactly what the difference asks for. It refuses
        rather than half-applying, so a failure here leaves the repository as
        it was.

        The result is committed rather than left in place: an uncommitted tree
        would be picked up by the next settle timer and recorded as though the
        user had made it.
        """
        self._run('read-tree', '--reset', '-u', target)
        self._keep_plugin_enabled()
        self._commit(subject, allow_empty=True)

    def _keep_plugin_enabled(self):
        """Put MiAZHistory back into plugins-used.json when a step removed it.

        The one key under .conf that a step does not restore verbatim. Without
        this, stepping back past the moment the plugin was enabled would
        switch off the plugin that holds the redo.
        """
        path = os.path.join(self.path, PLUGINS_USED)
        try:
            with open(path, encoding='utf-8') as used:
                plugins = json.load(used)
        except (OSError, ValueError):
            return
        if PLUGIN_NAME in plugins:
            return
        plugins[PLUGIN_NAME] = PLUGIN_DESCRIPTION
        with open(path, 'w', encoding='utf-8') as used:
            json.dump(plugins, used, indent=4, sort_keys=True)

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

    def changes(self, older: str, newer: str) -> list:
        """[(status, path, other)] between two states.

        Renames are detected rather than reported as a deletion and an
        addition: "renamed" is what the user did, and two halves would read as
        a document lost and another gained. The output is NUL separated
        because a filename may hold anything a filename may hold.
        """
        out = self._run('diff', '--name-status', '-M', '-z', older, newer)
        fields = [field for field in out.split('\0') if field]
        changes = []
        position = 0
        while position < len(fields):
            status = fields[position][0]
            if status in ('R', 'C'):
                changes.append((status, fields[position + 1], fields[position + 2]))
                position += 3
            else:
                changes.append((status, fields[position + 1], ''))
                position += 2
        return changes

    def timestamp(self, state: str) -> int:
        """When a state was made, in seconds since the epoch."""
        return int(self._run('show', '-s', '--format=%ct', state).strip())
