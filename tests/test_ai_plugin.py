#!/usr/bin/python3

"""
Regression guard for the merged MiAZAIAssistant plugin.

The plugin package `miazai` lives under the plugin directory, which is not on
the default path, so the test inserts it the same way the plugin does at
runtime. The provider modules and prompt/usage/suggestion helpers are pure
Python (SDKs are imported lazily inside methods), so importing and instantiating
them needs no GTK and no provider SDK installed.
"""

import os
import sys

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'resources', 'plugins', 'MiAZAIAssistant')


@pytest.fixture(autouse=True)
def _plugin_path():
    if PLUGIN_DIR not in sys.path:
        sys.path.insert(0, PLUGIN_DIR)


def test_make_usage_single_source():
    from miazai.usage import make_usage
    from miazai.suggestion import make_usage as re_exported
    assert make_usage is re_exported
    assert make_usage(3, 5) == {
        'input_tokens': 3, 'output_tokens': 5, 'total_tokens': 8}


def test_prompt_has_suggest_and_chat_builders():
    import miazai.prompt as P
    assert callable(P.suggest_system_prompt)
    assert callable(P.suggest_user_prompt)
    assert P.chat_system_prompt('doc.pdf').strip() != ''
    assert isinstance(P.schema(), dict)


def test_providers_expose_suggest_and_chat():
    from miazai.providers import PROVIDER_CLASSES, PROVIDER_IDS
    assert set(PROVIDER_IDS) == {'claude', 'openai', 'gemini', 'ollama'}
    for pid, cls in PROVIDER_CLASSES.items():
        # Instantiation succeeds only when both abstract methods are implemented.
        inst = cls({}, None)
        assert callable(getattr(inst, 'suggest')), pid
        assert callable(getattr(inst, 'chat')), pid
