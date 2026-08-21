#!/usr/bin/python3

"""
The MiAZAIAssistant suggest path takes no widget.

It used to own an Adw.SplitButton and disabled it while the request ran. When
that button became an entry in the shared Suggest menu, the caller kept passing
None where the button had been, and the first click died on
`'NoneType' object has no attribute 'set_sensitive'`.

Nothing catches that statically: None has attributes until you ask for one. So
the contract is pinned here instead, cheaply, with no display and no provider.
"""

import importlib.util
import inspect
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, 'data', 'resources', 'plugins', 'MiAZAIAssistant',
                      'miazai', 'ui', 'dialog.py')


@pytest.fixture(scope='module')
def dialog_module():
    spec = importlib.util.spec_from_file_location('miazai_ui_dialog', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', ['_on_suggest', '_finish'])
def test_the_suggest_path_takes_no_widget(dialog_module, name):
    """A parameter named button is the shape of the bug: something to disable
    that no longer exists."""
    params = inspect.signature(getattr(dialog_module, name)).parameters
    assert 'button' not in params, (
        f'{name}{tuple(params)} still expects a widget. The entry is in the '
        f'shared Suggest menu now; disable its action, not a button.')


def test_the_caller_matches_the_callee(dialog_module):
    """_suggest_now is what the menu entry calls, and it has to hand
    _on_suggest exactly what _on_suggest asks for."""
    callee = inspect.signature(dialog_module._on_suggest).parameters
    source = inspect.getsource(dialog_module._suggest_now)
    call = source[source.index('_on_suggest('):]
    passed = call[len('_on_suggest('):call.index(')')].split(',')
    assert len([arg for arg in passed if arg.strip()]) == len(callee), (
        f'_suggest_now passes {len(passed)} arguments to _on_suggest, '
        f'which takes {len(callee)}: {tuple(callee)}')


def test_the_entry_is_re_enabled_through_the_actions_service(dialog_module):
    """Whatever happens, the entry has to come back, or it stays greyed out for
    the rest of the session. Both paths go through one helper."""
    calls = []

    class Actions:
        def set_suggest_item_enabled(self, name, enabled):
            calls.append((name, enabled))

    class App:
        def get_service(self, name):
            return Actions() if name == 'actions' else None

    dialog_module._set_entry_enabled(App(), False)
    dialog_module._set_entry_enabled(App(), True)
    assert calls == [('miazai-suggest', False), ('miazai-suggest', True)]


def test_a_missing_actions_service_is_survivable(dialog_module):
    """During teardown the service can be gone; re-enabling must not raise."""
    class App:
        def get_service(self, name):
            return None

    dialog_module._set_entry_enabled(App(), True)


class Config:
    """A stand-in for MiAZConfig holding a used and an available pool."""

    def __init__(self, used=None, available=None):
        self._used = used or {}
        self._available = available or {}

    def load_used(self):
        return self._used

    def load_available(self):
        return self._available


def test_a_suggestion_matches_an_existing_key_whatever_its_case(dialog_module):
    """The model is asked for an upper-case key, and the repository may hold
    the same company written differently. FVM had both 'ALLIANZ' and 'Allianz'
    as senders because a suggestion of ALLIANZ never matched the Allianz that
    was already there, and the second one was added alongside it.
    """
    cfg = Config(used={'Allianz': 'Allianz', 'DHL': 'DHL'})
    assert dialog_module._existing_key(cfg, 'ALLIANZ') == 'Allianz'
    assert dialog_module._existing_key(cfg, 'DHL') == 'DHL'


def test_a_genuinely_new_value_is_not_invented_out_of_an_old_one(dialog_module):
    """Only the same name in another case counts. A different value must come
    back as new, or the user is never offered the chance to add it."""
    cfg = Config(used={'Allianz': 'Allianz'})
    assert dialog_module._existing_key(cfg, 'ALLIANZDIRECT') is None
    assert dialog_module._existing_key(cfg, 'AXA') is None


def test_a_value_only_in_the_available_pool_is_found_too(dialog_module):
    """It is not enabled here yet, so the user is asked to enable it. Asking
    about 'Allianz' is right; asking about 'ALLIANZ' adds a duplicate."""
    cfg = Config(used={}, available={'Allianz': 'Allianz'})
    assert dialog_module._existing_key(cfg, 'ALLIANZ') == 'Allianz'


def test_a_used_value_wins_over_an_available_one(dialog_module):
    """When a repository somehow holds both spellings, the one already enabled
    here is the better answer."""
    cfg = Config(used={'Allianz': 'Allianz'}, available={'ALLIANZ': 'ALLIANZ'})
    assert dialog_module._existing_key(cfg, 'allianz') == 'Allianz'


def test_the_busy_indicator_is_cleared_however_the_request_ends(dialog_module):
    """A spinner left turning after a failure says the dialog is still working
    when it has given up. Both paths go through _finish."""
    calls = []

    class Dialog:
        def set_busy(self, message):
            calls.append(('set', message))

        def clear_busy(self):
            calls.append(('clear', None))

    class Actions:
        def set_suggest_item_enabled(self, name, enabled):
            pass

    class App:
        def get_widget(self, name):
            return Dialog() if name == 'dialog-rename' else None

        def get_service(self, name):
            return Actions() if name == 'actions' else None

    dialog_module._set_busy(App(), 'Guessing with AI (gpt-x)')
    assert calls == [('set', 'Guessing with AI (gpt-x)')]

    calls.clear()
    dialog_module._clear_busy(App())
    assert calls == [('clear', None)]


def test_a_dialog_without_a_busy_indicator_is_survivable(dialog_module):
    """The plugin must not assume the dialog it is used from has one."""
    class Plain:
        pass

    class App:
        def get_widget(self, name):
            return Plain()

        def get_service(self, name):
            return None

    dialog_module._set_busy(App(), 'anything')
    dialog_module._clear_busy(App())
