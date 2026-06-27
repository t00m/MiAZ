#!/usr/bin/python3

from typing import Optional

from .base import Provider
from miazaic.usage import make_usage

_DEFAULT_MODEL = 'gpt-4o-mini'


class OpenAIProvider(Provider):
    name = 'OpenAI'
    requires_api_key = True
    supports_files = True

    def __init__(self, config: dict, log):
        super().__init__(config, log)
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError('openai package not installed; run: pip install openai')
        self._client = OpenAI(api_key=self.config.get('api_key', ''))

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
