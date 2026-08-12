
from .base import Provider, MissingDependencyError as MissingDependencyError
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


def effective_active_pid(plugin, registry) -> str:
    """Provider id that should be used for a request.

    An explicit choice in the 'Active provider' selector always wins. When none
    is set yet, use the first provider whose API key is already configured, so
    configuring a provider (for example Claude) is enough to use it without also
    changing the selector. Fall back to a keyless provider (ollama) when nothing
    is configured.
    """
    pid = plugin.get_config_key('active_provider')
    if pid and pid in registry:
        return pid
    for candidate, provider in registry.items():
        if provider.requires_api_key and provider.healthcheck()[0]:
            return candidate
    return 'ollama' if 'ollama' in registry else next(iter(registry))


def active_provider(plugin, registry) -> Provider:
    return registry[effective_active_pid(plugin, registry)]
