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


def build_registry(plugin, log, secrets):
    registry = {}
    for pid, cls in PROVIDER_CLASSES.items():
        cfg = plugin.get_config_key(f'provider_{pid}') or {}
        account = f'{plugin.name}/{pid}'
        # Migrate a plaintext key into the secure store, then strip it from the
        # JSON config so it no longer lives on disk in clear text.
        plain = cfg.get('api_key')
        if plain and secrets.backend() is not None and secrets.store(account, plain):
            cfg = dict(cfg)
            cfg.pop('api_key', None)
            plugin.set_config_key(f'provider_{pid}', cfg)
            log.info(f"Migrated {account} API key to {secrets.backend()}")
        # Inject the key for this session from the secure store when present.
        key = secrets.lookup(account)
        if key:
            cfg = {**cfg, 'api_key': key}
        registry[pid] = cls(cfg, log)
    return registry


def active_provider(plugin, registry) -> Provider:
    pid = plugin.get_config_key('active_provider') or 'ollama'
    return registry.get(pid) or registry['ollama']
