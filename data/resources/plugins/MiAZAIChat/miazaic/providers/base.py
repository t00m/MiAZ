#!/usr/bin/python3

import abc
from typing import Optional


class Provider(abc.ABC):
    name: str
    requires_api_key: bool
    supports_files: bool

    def __init__(self, config: dict, log):
        self.config = config
        self.log = log

    @abc.abstractmethod
    def chat(self, *, messages: list, system_prompt: str,
             document_text: Optional[str] = None,
             file_path: Optional[str] = None) -> dict:
        """Run one chat turn.

        'messages' is the running conversation, a list of
        {'role': 'user'|'assistant', 'content': str}. 'document_text' is the
        extracted document text when available; otherwise 'file_path' points at
        the document for providers that can read files. Returns
        {'text': <answer>, 'usage': {input_tokens, output_tokens, total_tokens}}.
        """

    def healthcheck(self) -> tuple:
        if not self.requires_api_key:
            return True, ''
        key = self.config.get('api_key', '')
        return bool(key), ('' if key else 'No API key configured')
