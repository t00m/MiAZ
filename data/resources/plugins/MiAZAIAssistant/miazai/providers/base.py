#!/usr/bin/python3

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

    def healthcheck(self) -> tuple:
        if not self.requires_api_key:
            return True, ''
        key = self.config.get('api_key', '')
        return bool(key), ('' if key else 'No API key configured')
