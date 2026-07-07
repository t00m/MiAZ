#!/usr/bin/python3

"""
Tests for MiAZ.backend.secrets.MiAZSecretStore: the libsecret -> keyring cascade
and its failure handling. Real secret backends are not present in CI, so the
store is exercised with injected fake backends.
"""

from MiAZ.backend.secrets import MiAZSecretStore


class FakeBackend:
    """In-memory secret backend for tests."""

    def __init__(self, name, available=True, raise_on=None):
        self.name = name
        self._available = available
        self._store = {}
        self._raise_on = raise_on or set()

    def available(self):
        if 'available' in self._raise_on:
            raise RuntimeError('probe failed')
        return self._available

    def store(self, account, secret):
        if 'store' in self._raise_on:
            raise RuntimeError('store failed')
        self._store[account] = secret
        return True

    def lookup(self, account):
        if 'lookup' in self._raise_on:
            raise RuntimeError('lookup failed')
        return self._store.get(account)

    def clear(self, account):
        if 'clear' in self._raise_on:
            raise RuntimeError('clear failed')
        self._store.pop(account, None)


def _store(*backends):
    return MiAZSecretStore(backends=backends)


def test_first_available_backend_wins():
    primary = FakeBackend('libsecret')
    secondary = FakeBackend('keyring')
    store = _store(primary, secondary)

    assert store.backend() == 'libsecret'
    assert store.store('MiAZAIChat/claude', 'sk-123') is True
    assert store.lookup('MiAZAIChat/claude') == 'sk-123'
    # The secret went into the primary, not the secondary.
    assert secondary.lookup('MiAZAIChat/claude') is None


def test_cascade_falls_through_to_second():
    primary = FakeBackend('libsecret', available=False)
    secondary = FakeBackend('keyring')
    store = _store(primary, secondary)

    assert store.backend() == 'keyring'
    assert store.store('acct', 'sec') is True
    assert store.lookup('acct') == 'sec'


def test_probe_error_is_treated_as_unavailable():
    primary = FakeBackend('libsecret', raise_on={'available'})
    secondary = FakeBackend('keyring')
    store = _store(primary, secondary)

    assert store.backend() == 'keyring'


def test_no_backend_available():
    store = _store(FakeBackend('libsecret', available=False),
                   FakeBackend('keyring', available=False))

    assert store.backend() is None
    assert store.store('acct', 'sec') is False
    assert store.lookup('acct') is None
    # clear is a no-op, must not raise
    store.clear('acct')


def test_empty_backend_list():
    store = _store()
    assert store.backend() is None
    assert store.store('a', 'b') is False


def test_store_failure_returns_false():
    backend = FakeBackend('libsecret', raise_on={'store'})
    store = _store(backend)
    assert store.store('acct', 'sec') is False


def test_lookup_failure_returns_none():
    backend = FakeBackend('libsecret', raise_on={'lookup'})
    store = _store(backend)
    assert store.lookup('acct') is None


def test_clear_removes_secret():
    backend = FakeBackend('libsecret')
    store = _store(backend)
    store.store('acct', 'sec')
    store.clear('acct')
    assert store.lookup('acct') is None


def test_backend_resolved_once():
    # available() must not be re-probed on every call.
    calls = {'n': 0}
    backend = FakeBackend('libsecret')
    orig = backend.available

    def counting():
        calls['n'] += 1
        return orig()

    backend.available = counting
    store = _store(backend)
    store.backend()
    store.store('a', 'b')
    store.lookup('a')
    assert calls['n'] == 1
