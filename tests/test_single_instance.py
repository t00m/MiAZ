#!/usr/bin/python3

"""
Tests for the single-instance lock, and for who it is supposed to stop.

MiAZ takes an exclusive lock on ~/.MiAZ/var/miaz.lock so a second window cannot
open on the same repository. It was taken in MiAZ.__init__, which runs for
every invocation, and run() only decides between the window and the command
line afterwards. So `miaz search` refused to run whenever the window was open,
which is exactly when somebody sitting at a terminal is most likely to try it.

The same ordering made a command line run empty ~/.MiAZ/var/tmp, where scans
waiting to be imported and exports being built are kept. The lock hid that: the
command exited before it got there. Fixing only the lock would have turned a
refusal into deleted files, so both are pinned here.
"""

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Removing all three is what a cron job or an SSH session without X forwarding
# looks like, which is where the command line matters most.
DISPLAY_VARS = ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR')

# What the lock holder is told to sleep for. Long enough that no test outruns
# it, short enough that a leaked process goes away on its own.
HOLD_SECONDS = 30


def miaz_env(home):
    env = {
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        'HOME': str(home),
        'PYTHONPATH': ROOT,
        'LC_ALL': 'C',
    }
    for name in DISPLAY_VARS:
        env.pop(name, None)
    return env


def run_miaz(args, home, timeout=120):
    return subprocess.run([sys.executable, '-m', 'MiAZ.miaz'] + args,
                          cwd=ROOT, env=miaz_env(home), capture_output=True,
                          text=True, timeout=timeout)


def hold_the_lock(home):
    """Take the lock the way a running MiAZ window holds it.

    Returns the process. The caller kills it. It prints once the lock is
    actually held, so a test never races the lock it depends on.
    """
    lock_dir = home / '.MiAZ' / 'var'
    lock_dir.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [sys.executable, '-c',
         'import fcntl, sys, time\n'
         f'fd = open({str(lock_dir / "miaz.lock")!r}, "w")\n'
         'fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
         'print("HELD", flush=True)\n'
         f'time.sleep({HOLD_SECONDS})\n'],
        stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == 'HELD', 'could not take the lock'
    return holder


def test_a_command_runs_while_the_window_holds_the_lock(tmp_path):
    """The bug. `miaz repos` opens no repository and writes nothing, and it
    refused to run because a window was open."""
    home = tmp_path / 'home'
    holder = hold_the_lock(home)
    try:
        result = run_miaz(['repos'], home)
    finally:
        holder.kill()
        holder.wait()

    assert 'already running' not in result.stderr, result.stderr[-2000:]
    # 1 is "no repositories configured", which is the right answer for a home
    # directory that has never opened one. 0 would mean it found some.
    assert result.returncode in (0, 1), (
        f'exit {result.returncode}: {result.stderr[-2000:]}')


def test_a_search_runs_while_the_window_holds_the_lock(tmp_path):
    """The command people actually type."""
    home = tmp_path / 'home'
    holder = hold_the_lock(home)
    try:
        result = run_miaz(['search', 'invoice'], home)
    finally:
        holder.kill()
        holder.wait()

    assert 'already running' not in result.stderr, result.stderr[-2000:]


def test_a_command_does_not_empty_the_temporary_directory(tmp_path):
    """var/tmp holds scans waiting to be imported and exports being built.

    Emptying it belongs to the window starting up, which owns those files. A
    command line run happening while the window works is not a fresh start.
    """
    home = tmp_path / 'home'
    # A first run builds the directory tree the way the application does.
    run_miaz(['repos'], home)
    scan = home / '.MiAZ' / 'var' / 'tmp' / 'scan-in-progress.pdf'
    scan.parent.mkdir(parents=True, exist_ok=True)
    scan.write_text('a page being scanned', encoding='utf-8')

    run_miaz(['repos'], home)

    assert scan.exists(), 'a command line run deleted a file the window owned'


def test_the_window_still_refuses_to_open_twice(tmp_path):
    """What the lock is for, unchanged.

    With no display the window path exits 2 saying so, and the lock refusal
    exits 1 before that, so the two outcomes cannot be confused.
    """
    home = tmp_path / 'home'
    holder = hold_the_lock(home)
    try:
        result = run_miaz([], home)
    finally:
        holder.kill()
        holder.wait()

    assert result.returncode == 1, (
        f'exit {result.returncode}, stderr: {result.stderr[-2000:]}')
    assert 'already running' in result.stderr.lower(), result.stderr[-2000:]


def test_the_window_opens_when_nothing_holds_the_lock(tmp_path):
    """The refusal has to be about the lock and not about every start.

    Without a display it gets as far as the display check and says so, which
    is proof it passed the lock.
    """
    home = tmp_path / 'home'

    result = run_miaz([], home)

    assert result.returncode == 2, result.stderr[-2000:]
    assert 'already running' not in result.stderr, result.stderr[-2000:]
    assert 'display' in result.stderr.lower(), result.stderr[-2000:]


def test_two_commands_can_run_at_the_same_time(tmp_path):
    """Reading a repository is not exclusive work. Two terminals, or a script
    and a terminal, have no reason to wait for each other."""
    home = tmp_path / 'home'
    run_miaz(['repos'], home)

    first = subprocess.Popen([sys.executable, '-m', 'MiAZ.miaz', 'repos'],
                             cwd=ROOT, env=miaz_env(home),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True)
    second = subprocess.Popen([sys.executable, '-m', 'MiAZ.miaz', 'repos'],
                              cwd=ROOT, env=miaz_env(home),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and None in (first.poll(), second.poll()):
        time.sleep(0.05)

    for process in (first, second):
        assert process.poll() is not None, 'a second command never finished'
        assert 'already running' not in process.stderr.read()
