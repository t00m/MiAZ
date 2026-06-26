#!/usr/bin/python3

from typing import Optional

from .base import Provider
from miazaic.usage import make_usage

_DEFAULT_MODEL = 'gemini-2.0-flash'


class GeminiProvider(Provider):
    name = 'Gemini'
    requires_api_key = True
    supports_files = True

    def __init__(self, config: dict, log):
        super().__init__(config, log)
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from google import genai
        except ImportError:
            raise RuntimeError('google-genai package not installed; run: pip install google-genai')
        self._client = genai.Client(api_key=self.config.get('api_key', ''))

    def chat(self, *, messages, system_prompt,
             document_text: Optional[str] = None,
             file_path: Optional[str] = None) -> dict:
        self._ensure_client()
        model = self.config.get('model', _DEFAULT_MODEL)

        # Gemini generate_content is single-shot, so flatten the system prompt,
        # the document text and the running transcript into one prompt.
        parts = [system_prompt]
        if document_text:
            parts.append('Document:\n\n' + document_text)
        transcript = []
        for m in messages:
            who = 'User' if m['role'] == 'user' else 'Assistant'
            transcript.append(f"{who}: {m['content']}")
        parts.append('\n'.join(transcript))
        contents = ['\n\n'.join(parts)]

        if document_text is None and file_path is not None:
            uploaded = self._client.files.upload(file=str(file_path))
            contents.append(uploaded)

        resp = self._client.models.generate_content(model=model, contents=contents)
        usage = {}
        try:
            um = resp.usage_metadata
            usage = make_usage(um.prompt_token_count,
                               um.candidates_token_count,
                               um.total_token_count)
        except Exception:
            pass
        return {'text': resp.text or '', 'usage': usage}
