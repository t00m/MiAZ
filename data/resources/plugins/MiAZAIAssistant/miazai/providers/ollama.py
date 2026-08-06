#!/usr/bin/python3

import json
import pathlib
from dataclasses import replace
from typing import Optional

from .base import Provider, MissingDependencyError
from miazai.suggestion import Suggestion
from miazai.usage import make_usage
from miazai.vocab import Vocabulary

_DEFAULT_MODEL = 'llama3.1:8b'
_DEFAULT_BASE_URL = 'http://localhost:11434'


class OllamaProvider(Provider):
    name = 'Ollama'
    requires_api_key = False
    supports_files = False
    supports_json_schema = False

    def suggest(self, *, text: Optional[str], file_path: Optional[pathlib.Path],
                vocab: Vocabulary, system_prompt: str, user_prompt: str,
                schema: dict) -> Suggestion:
        try:
            import ollama
        except ImportError:
            raise MissingDependencyError('ollama')

        model = self.config.get('model', _DEFAULT_MODEL)
        host = self.config.get('base_url', _DEFAULT_BASE_URL)

        if not text:
            raise RuntimeError(
                'Ollama does not support file upload. '
                'Install pdftotext or tesseract for local text extraction.')

        body = (system_prompt + '\n\n' + user_prompt + '\n\n' + text)
        resp = ollama.chat(
            model=model,
            host=host,
            messages=[{'role': 'user', 'content': body}],
            format='json',
        )
        if isinstance(resp, dict):
            raw_text = resp['message']['content']
            prompt_tokens = resp.get('prompt_eval_count')
            output_tokens = resp.get('eval_count')
        else:
            raw_text = resp.message.content
            prompt_tokens = getattr(resp, 'prompt_eval_count', None)
            output_tokens = getattr(resp, 'eval_count', None)
        usage = make_usage(prompt_tokens, output_tokens)
        try:
            d = json.loads(raw_text)
        except Exception:
            return Suggestion(usage=usage)
        return replace(_from_dict(d), usage=usage)

    def chat(self, *, messages, system_prompt,
             document_text: Optional[str] = None,
             file_path: Optional[str] = None) -> dict:
        try:
            import ollama
        except ImportError:
            raise MissingDependencyError('ollama')

        model = self.config.get('model', _DEFAULT_MODEL)
        host = self.config.get('base_url', _DEFAULT_BASE_URL)

        if not document_text:
            raise RuntimeError(
                'Ollama cannot read the document directly. Install pdftotext or '
                'tesseract for local text extraction, or pick a provider that '
                'supports file upload.')

        system_content = system_prompt + '\n\nDocument:\n\n' + document_text
        api = [{'role': 'system', 'content': system_content}]
        api += [{'role': m['role'], 'content': m['content']} for m in messages]

        resp = ollama.chat(model=model, host=host, messages=api)
        if isinstance(resp, dict):
            text = resp['message']['content']
            prompt_tokens = resp.get('prompt_eval_count')
            output_tokens = resp.get('eval_count')
        else:
            text = resp.message.content
            prompt_tokens = getattr(resp, 'prompt_eval_count', None)
            output_tokens = getattr(resp, 'eval_count', None)
        return {'text': text, 'usage': make_usage(prompt_tokens, output_tokens)}

    def healthcheck(self) -> tuple:
        try:
            import ollama as _ollama
            host = self.config.get('base_url', _DEFAULT_BASE_URL)
            _ollama.list(host=host)
            return True, ''
        except Exception as exc:
            return False, str(exc)


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
