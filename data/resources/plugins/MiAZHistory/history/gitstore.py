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
import tempfile
import threading
import subprocess

STATE_FILE = 'miaz-history.json'
STATE_VERSION = 1

# A git command that answers a question: status, diff, rev-parse, show. Long
# enough for a large repository, short enough that one on a network share that
# stopped answering gives up instead of leaving the plugin waiting for ever.
GIT_TIMEOUT = 120

# A git command that writes the whole tree. The first snapshot of a repository
# of several gigabytes is minutes of work, so this one is generous.
GIT_LONG_TIMEOUT = 3600

# What work that was never recorded is called when a step rescues it. The
# plugin passes the translated wording; this is the fallback for a caller that
# does not, such as a test.
RESCUE_SUBJECT = 'Changed outside MiAZ'

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
                              capture_output=True, text=True, check=False,
                              timeout=GIT_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def _write_json(path: str, payload, indent: int = 2, sort_keys: bool = False):
    """Write JSON so that a crash never leaves half a file behind.

    Opening a file for writing truncates it, so a write that dies partway
    through, on a full disk or a power loss, leaves something that will not
    parse. Write to a temporary file beside the target, flush it to the disk,
    then rename it over the target: os.replace is atomic within one
    filesystem, so a reader sees either the old file or the new one.

    This repeats MiAZ's own atomic_json_save rather than importing it.
    MiAZ.backend.util pulls in gi, and everything in this module is meant to
    be testable without a display.
    """
    dirpath = os.path.dirname(path) or '.'
    handle, tmppath = tempfile.mkstemp(dir=dirpath, prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as out:
            json.dump(payload, out, indent=indent, sort_keys=sort_keys)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmppath, path)
    except BaseException:
        # Never leave the temporary file behind, whatever went wrong.
        try:
            os.unlink(tmppath)
        except OSError:
            pass
        raise


class GitStore:
    """One repository's history."""

    def __init__(self, path: str):
        self.path = path
        self.gitdir = os.path.join(path, '.git')
        self.statefile = os.path.join(self.gitdir, STATE_FILE)
        # git writes the index and the working tree, and two commands doing
        # that at once against one repository fight over .git/index.lock. The
        # loser raises, and the pair can leave the state file describing a tree
        # that is not the one on disk. Every method that writes takes this
        # first. Reentrant, because those methods call each other.
        self._lock = threading.RLock()

    def _run(self, *args, timeout: int = GIT_TIMEOUT) -> str:
        try:
            done = subprocess.run(['git', '-C', self.path, *args],
                                  capture_output=True, text=True, check=False,
                                  timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise GitError(
                f"git {' '.join(args)}: gave up after {timeout}s") from error
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
        with self._lock:
            self._run('-c', 'init.defaultBranch=main', 'init', '-q')
            self._run('config', 'user.name', GIT_NAME)
            self._run('config', 'user.email', GIT_EMAIL)
            self._run('config', 'commit.gpgsign', 'false')
            # Claim the repository before the first commit, which is minutes of
            # work on a large one. Quitting or crashing in between would
            # otherwise leave a .git with no state file, which is_foreign()
            # reads as somebody else's repository: the plugin would then refuse
            # this repository on every launch from now on, and the only way out
            # is deleting a directory it may not name. An empty timeline is
            # picked up by the next catch_up() instead.
            self._write_state([], -1)
            first = self._commit(subject, allow_empty=True)
            self._write_state([first], 0)
            return first

    def is_dirty(self) -> bool:
        return bool(self._run('status', '--porcelain').strip())

    def _commit(self, subject: str, allow_empty: bool = False) -> str:
        self._run('add', '-A', timeout=GIT_LONG_TIMEOUT)
        args = ['commit', '-q', '-m', subject]
        if allow_empty:
            args.append('--allow-empty')
        self._run(*args, timeout=GIT_LONG_TIMEOUT)
        return self._run('rev-parse', 'HEAD').strip()

    def record(self, subject: str):
        """Record whatever changed as a new state, or None when nothing did.

        A state recorded while stepped back drops everything ahead of it. That
        is the text-editor rule: a change made after stepping back is a new
        branch of the user's work, and the states that were waiting to be
        stepped forward into are not offered again.
        """
        with self._lock:
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

    def step_back(self, subject: str, rescue_subject: str = RESCUE_SUBJECT):
        with self._lock:
            state = self._read_state()
            if state['index'] <= 0:
                return None
            target = state['states'][state['index'] - 1]
            states = self._rescue_pending(state, rescue_subject)
            self._apply(target, subject)
            self._write_state(states, state['index'] - 1)
            return target

    def step_forward(self, subject: str, rescue_subject: str = RESCUE_SUBJECT):
        with self._lock:
            state = self._read_state()
            if state['index'] >= len(state['states']) - 1:
                return None
            target = state['states'][state['index'] + 1]
            states = self._rescue_pending(state, rescue_subject)
            self._apply(target, subject)
            self._write_state(states, state['index'] + 1)
            return target

    def _rescue_pending(self, state: dict, subject: str) -> list:
        """Commit work that never reached a state, before a step overwrites it.

        _apply writes the whole working tree, so anything uncommitted is gone
        with nothing to go back to. A dirty tree at this point is not a rare
        accident: a recording that failed leaves one and does not re-arm, and
        the configuration files a plugin writes reach disk with no signal for
        the settle timer to hear.

        The rescued work is appended as the newest state, and what was ahead is
        kept. record() drops what is ahead because a change made after stepping
        back is the user starting a new branch of their work. This is not that.
        It is work that was already there and was only never written down, so
        every state stays reachable and the promise that no change is lost
        holds. Returns the states list the caller should write.
        """
        if not self.is_dirty():
            return state['states']
        return state['states'] + [self._commit(subject)]

    def _apply(self, target: str, subject: str):
        """Put the tree of `target` on disk, and record having done so.

        read-tree writes the index and the working tree in one go, adding,
        changing and deleting exactly what the difference asks for. It refuses
        rather than half-applying, so a failure here leaves the repository as
        it was.

        The result is committed rather than left in place: an uncommitted tree
        would be picked up by the next settle timer and recorded as though the
        user had made it.

        Callers rescue anything uncommitted first, because --reset -u
        overwrites a tracked file that was modified and never recorded. See
        _rescue_pending.
        """
        self._run('read-tree', '--reset', '-u', target,
                  timeout=GIT_LONG_TIMEOUT)
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
        # Atomic, and for a sharper reason than the state file: this one is
        # written from a worker thread while the main thread may be reading it,
        # and MiAZConfig.load swallows a parse error and returns {}, which
        # opens the repository with every plugin apparently switched off.
        # sort_keys and indent match what MiAZ itself writes, so a rescued file
        # is byte for byte what the application would have produced.
        _write_json(path, plugins, indent=4, sort_keys=True)

    def _read_state(self) -> dict:
        """The timeline as it is on disk.

        A missing file means there is no history yet, which is the ordinary
        answer for a repository nobody has tracked. A file that will not parse
        is a different thing and must not be read as the same one: the next
        record() would write states[:0] + [commit] over it, and every state the
        user still had would be orphaned with nothing pointing at it and no
        word said. So it raises, and the plugin reports a change it could not
        record instead of quietly dropping the history.
        """
        if not os.path.exists(self.statefile):
            return {'version': STATE_VERSION, 'states': [], 'index': -1}
        try:
            with open(self.statefile, encoding='utf-8') as state:
                return json.load(state)
        except ValueError as error:
            raise GitError(f"The history index is unreadable: {error}") from error
        except OSError as error:
            raise GitError(f"The history index cannot be read: {error}") from error

    def _write_state(self, states: list, index: int):
        payload = {'version': STATE_VERSION, 'states': states, 'index': index}
        _write_json(self.statefile, payload, indent=2)

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
