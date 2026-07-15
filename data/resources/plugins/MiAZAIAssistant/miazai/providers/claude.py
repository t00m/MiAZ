#!/usr/bin/python3

import pathlib
from dataclasses import replace
from typing import Optional

from .base import Provider, MissingDependencyError
from miazai.suggestion import Suggestion, make_usage
from miazai.vocab import Vocabulary

_DEFAULT_MODEL = 'claude-haiku-4-5-20251001'

# Friendly names map to current model IDs so the Model field can hold
# 'Sonnet'/'Opus'/'Haiku' instead of the full API id. A full id is passed
# through unchanged.
_MODEL_ALIASES = {
    'opus': 'claude-opus-4-8',
    'sonnet': 'claude-sonnet-4-6',
    'haiku': 'claude-haiku-4-5',
}


def _resolve_model(value: str) -> str:
    value = (value or '').strip()
    if not value:
        return _DEFAULT_MODEL
    return _MODEL_ALIASES.get(value.lower(), value)


class ClaudeProvider(Provider):
    name = 'Claude'
    requires_api_key = True
    supports_files = True
    supports_json_schema = True

    def __init__(self, config: dict, log):
        super().__init__(config, log)
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from anthropic import Anthropic
        except ImportError:
            raise MissingDependencyError('anthropic')
        self._client = Anthropic(api_key=self.config.get('api_key', ''))

    def suggest(self, *, text: Optional[str], file_path: Optional[pathlib.Path],
                vocab: Vocabulary, system_prompt: str, user_prompt: str,
                schema: dict) -> Suggestion:
        self._ensure_client()
        model = _resolve_model(self.config.get('model', ''))

        tool = {
            'name': 'propose_filename',
            'description': 'Return the proposed 7 filename fields.',
            'input_schema': schema,
        }

        content = []
        if text:
            content.append({'type': 'text', 'text': user_prompt + '\n\n' + text})
        elif file_path is not None:
            with open(file_path, 'rb') as fh:
                uploaded = self._client.beta.files.upload(file=fh)
            content.append({'type': 'document',
                            'source': {'type': 'file', 'file_id': uploaded.id}})
            content.append({'type': 'text', 'text': user_prompt})
        else:
            return Suggestion()

        resp = self._client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            tools=[tool],
            tool_choice={'type': 'tool', 'name': 'propose_filename'},
            messages=[{'role': 'user', 'content': content}],
        )
        usage = {}
        try:
            u = resp.usage
            usage = make_usage(u.input_tokens, u.output_tokens)
        except Exception:
            pass
        for block in resp.content:
            if block.type == 'tool_use' and block.name == 'propose_filename':
                return replace(_from_dict(block.input), usage=usage)
        return Suggestion(usage=usage)


def _from_dict(d: dict) -> Suggestion:
    return Suggestion(
        date=str(d.get('date', '')),
        country=str(d.get('country', '')),
        group=str(d.get('group', '')),
        sentby=str(d.get('sentby', '')),
        purpose=str(d.get('purpose', '')),
        concept=str(d.get('concept', '')),
        sentto=str(d.get('sentto', '')),
        confidence=dict(d.get('confidence', {})),
        raw=d,
    )
