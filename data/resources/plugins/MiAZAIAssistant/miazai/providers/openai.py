#!/usr/bin/python3

import json
import pathlib
from dataclasses import replace
from typing import Optional

from .base import Provider, MissingDependencyError
from miazai.suggestion import Suggestion
from miazai.usage import make_usage
from miazai.vocab import Vocabulary

_DEFAULT_MODEL = 'gpt-4o-mini'


class OpenAIProvider(Provider):
    name = 'OpenAI'
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
            from openai import OpenAI
        except ImportError:
            raise MissingDependencyError('openai')
        self._client = OpenAI(api_key=self.config.get('api_key', ''))

    def suggest(self, *, text: Optional[str], file_path: Optional[pathlib.Path],
                vocab: Vocabulary, system_prompt: str, user_prompt: str,
                schema: dict) -> Suggestion:
        self._ensure_client()
        model = self.config.get('model', _DEFAULT_MODEL)

        messages = [{'role': 'system', 'content': system_prompt}]

        if text:
            messages.append({'role': 'user', 'content': user_prompt + '\n\n' + text})
        elif file_path is not None:
            with open(file_path, 'rb') as fh:
                uploaded = self._client.files.create(file=fh, purpose='assistants')
            messages.append({
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': user_prompt},
                    {'type': 'file', 'file': {'file_id': uploaded.id}},
                ],
            })
        else:
            return Suggestion()

        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'propose_filename',
                    'schema': schema,
                    'strict': True,
                },
            },
        )
        usage = {}
        try:
            u = resp.usage
            usage = make_usage(u.prompt_tokens, u.completion_tokens, u.total_tokens)
        except Exception:
            pass
        raw_text = resp.choices[0].message.content or '{}'
        try:
            d = json.loads(raw_text)
        except Exception:
            return Suggestion(usage=usage)
        return replace(_from_dict(d), usage=usage)

    def chat(self, *, messages, system_prompt,
             document_text: Optional[str] = None,
             file_path: Optional[str] = None) -> dict:
        self._ensure_client()
        model = self.config.get('model', _DEFAULT_MODEL)

        api = [{'role': 'system', 'content': system_prompt}]
        if document_text:
            api.append({'role': 'user',
                        'content': 'Document to answer questions about:\n\n' + document_text})
            api.append({'role': 'assistant',
                        'content': 'Understood. Ask your questions about this document.'})
        elif file_path is not None:
            with open(file_path, 'rb') as fh:
                uploaded = self._client.files.create(file=fh, purpose='assistants')
            api.append({'role': 'user',
                        'content': [
                            {'type': 'text',
                             'text': 'This is the document to answer questions about.'},
                            {'type': 'file', 'file': {'file_id': uploaded.id}},
                        ]})
            api.append({'role': 'assistant',
                        'content': 'Understood. Ask your questions about this document.'})
        api += [{'role': m['role'], 'content': m['content']} for m in messages]

        resp = self._client.chat.completions.create(model=model, messages=api)
        usage = {}
        try:
            u = resp.usage
            usage = make_usage(u.prompt_tokens, u.completion_tokens, u.total_tokens)
        except Exception:
            pass
        text = resp.choices[0].message.content or ''
        return {'text': text, 'usage': usage}


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
