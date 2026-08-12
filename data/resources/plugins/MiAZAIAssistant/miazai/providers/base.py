
import abc
import pathlib
from typing import Optional

from miazai.suggestion import Suggestion
from miazai.vocab import Vocabulary


class MissingDependencyError(Exception):
    """A provider's Python library is not installed in the venv.

    Carries the pip package name so the UI can offer to install it.
    """
    def __init__(self, package: str):
        self.package = package
        super().__init__(f'The Python library "{package}" is not installed.')


class Provider(abc.ABC):
    name: str
    requires_api_key: bool
    supports_files: bool
    supports_json_schema: bool

    def __init__(self, config: dict, log):
        self.config = config
        self.log = log

    @abc.abstractmethod
    def suggest(self, *, text: Optional[str],
                file_path: Optional[pathlib.Path],
                vocab: Vocabulary,
                system_prompt: str,
                user_prompt: str,
                schema: dict) -> Suggestion:
        """Run a single suggestion request."""

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
