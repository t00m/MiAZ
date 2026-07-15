#!/usr/bin/python3

"""
# File: secrets.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Secure storage for plugin secrets (API keys).

Secrets are stored through a cascade: libsecret (the Secret Service) first,
then the python 'keyring' library. The final plaintext fallback is not handled
here: it lives in the plugin's JSON config, so this class only answers whether a
secure backend accepted the secret. Backends are injectable so the store can be
tested without a real Secret Service.
"""

from MiAZ.backend.log import MiAZLog

APP_ID = 'io.github.t00m.MiAZ'
_LABEL = 'MiAZ secret'


class LibsecretBackend:
    """Secret Service backend using libsecret's simple password API."""
    name = 'libsecret'

    def __init__(self):
        import gi
        gi.require_version('Secret', '1')
        from gi.repository import Secret
        self._Secret = Secret
        self._schema = Secret.Schema.new(
            APP_ID + '.Secret', Secret.SchemaFlags.NONE,
            {
                'application': Secret.SchemaAttributeType.STRING,
                'account': Secret.SchemaAttributeType.STRING,
            })

    def _attrs(self, account):
        return {'application': APP_ID, 'account': account}

    def available(self):
        # A lookup round-trips to the Secret Service. If the service is missing
        # or unreachable it raises, so treat that as "backend unavailable".
        try:
            self._Secret.password_lookup_sync(self._schema, self._attrs('__probe__'), None)
            return True
        except Exception:
            return False

    def store(self, account, secret):
        return bool(self._Secret.password_store_sync(
            self._schema, self._attrs(account), self._Secret.COLLECTION_DEFAULT,
            f'{_LABEL} ({account})', secret, None))

    def lookup(self, account):
        return self._Secret.password_lookup_sync(self._schema, self._attrs(account), None)

    def clear(self, account):
        self._Secret.password_clear_sync(self._schema, self._attrs(account), None)


class KeyringBackend:
    """Fallback backend using the python 'keyring' library."""
    name = 'keyring'

    def __init__(self):
        import keyring
        self._keyring = keyring

    def available(self):
        try:
            backend = self._keyring.get_keyring()
            # keyring.backends.fail.Keyring is the null backend: it raises on
            # use, so a store/lookup would never persist anything.
            return backend is not None and 'fail' not in type(backend).__module__
        except Exception:
            return False

    def store(self, account, secret):
        self._keyring.set_password(APP_ID, account, secret)
        return True

    def lookup(self, account):
        return self._keyring.get_password(APP_ID, account)

    def clear(self, account):
        self._keyring.delete_password(APP_ID, account)


def _build_default_backends(log):
    backends = []
    for cls in (LibsecretBackend, KeyringBackend):
        try:
            backends.append(cls())
        except Exception as error:
            log.debug(f"Secret backend {cls.__name__} unavailable: {error}")
    return backends


class MiAZSecretStore:
    """Secure storage for plugin secrets, with a libsecret -> keyring cascade.

    The account identifier is built by the caller, e.g. 'MiAZAIChat/claude', so
    each plugin and provider gets its own entry.
    """

    def __init__(self, log=None, backends=None):
        self.log = log or MiAZLog('MiAZ.Secrets')
        if backends is None:
            self._backends = _build_default_backends(self.log)
        else:
            self._backends = list(backends)
        self._active = None
        self._resolved = False

    def _backend(self):
        if not self._resolved:
            for backend in self._backends:
                try:
                    if backend.available():
                        self._active = backend
                        break
                except Exception:
                    continue
            self._resolved = True
            if self._active is not None:
                self.log.debug(f"Secret store using backend: {self._active.name}")
        return self._active

    def backend(self):
        """Name of the active secure backend, or None if none is available."""
        active = self._backend()
        return active.name if active else None

    def store(self, account, secret):
        """Store secret. Return True if a secure backend accepted it."""
        active = self._backend()
        if active is None:
            return False
        try:
            return bool(active.store(account, secret))
        except Exception as error:
            self.log.error(f"Storing secret in {active.name} failed: {error}")
            return False

    def lookup(self, account):
        """Return the stored secret, or None."""
        active = self._backend()
        if active is None:
            return None
        try:
            return active.lookup(account)
        except Exception as error:
            self.log.error(f"Looking up secret in {active.name} failed: {error}")
            return None

    def clear(self, account):
        """Remove the stored secret, if any."""
        active = self._backend()
        if active is None:
            return
        try:
            active.clear(account)
        except Exception as error:
            self.log.error(f"Clearing secret in {active.name} failed: {error}")
