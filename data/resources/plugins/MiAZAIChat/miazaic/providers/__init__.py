#!/usr/bin/python3

from .base import Provider
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider

PROVIDER_CLASSES = {
    'claude': ClaudeProvider,
    'openai': OpenAIProvider,
    'gemini': GeminiProvider,
    'ollama': OllamaProvider,
}

PROVIDER_IDS = list(PROVIDER_CLASSES.keys())


def build_registry(plugin, log):
    registry = {}
    for pid, cls in PROVIDER_CLASSES.items():
        cfg = plugin.get_config_key(f'provider_{pid}') or {}
        registry[pid] = cls(cfg, log)
    return registry


def active_provider(plugin, registry) -> Provider:
    pid = plugin.get_config_key('active_provider') or 'ollama'
    return registry.get(pid) or registry['ollama']
