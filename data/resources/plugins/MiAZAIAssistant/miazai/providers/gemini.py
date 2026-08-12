
import json
import pathlib
from dataclasses import replace
from typing import Optional

from .base import Provider, MissingDependencyError
from miazai.suggestion import Suggestion
from miazai.usage import make_usage
from miazai.vocab import Vocabulary

_DEFAULT_MODEL = 'gemini-2.0-flash'


class GeminiProvider(Provider):
    name = 'Gemini'
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
            from google import genai
        except ImportError:
            raise MissingDependencyError('google-genai')
        self._client = genai.Client(api_key=self.config.get('api_key', ''))

    def suggest(self, *, text: Optional[str], file_path: Optional[pathlib.Path],
                vocab: Vocabulary, system_prompt: str, user_prompt: str,
                schema: dict) -> Suggestion:
        self._ensure_client()
        from google import genai as _genai
        model = self.config.get('model', _DEFAULT_MODEL)

        contents = []
        if text:
            contents.append(system_prompt + '\n\n' + user_prompt + '\n\n' + text)
        elif file_path is not None:
            uploaded = self._client.files.upload(file=str(file_path))
            contents.append(system_prompt + '\n\n' + user_prompt)
            contents.append(uploaded)
        else:
            return Suggestion()

        resp = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=_genai.types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=schema,
            ),
        )
        usage = {}
        try:
            um = resp.usage_metadata
            usage = make_usage(um.prompt_token_count,
                               um.candidates_token_count,
                               um.total_token_count)
        except Exception:
            pass
        raw_text = resp.text or '{}'
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
