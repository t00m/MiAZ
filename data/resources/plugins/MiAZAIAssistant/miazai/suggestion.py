#!/usr/bin/python3

from dataclasses import dataclass, field

from miazai.usage import make_usage

# make_usage is re-exported here, not defined here: the single definition lives
# in usage.py. Naming it in __all__ says the re-export is deliberate, so a
# linter does not read it as a stray import and offer to delete it.
# tests/test_ai_plugin.py asserts both names resolve to the same object.
__all__ = ['Suggestion', 'make_usage']


@dataclass(frozen=True)
class Suggestion:
    date: str = ''
    country: str = ''
    group: str = ''
    sentby: str = ''
    purpose: str = ''
    concept: str = ''
    sentto: str = ''
    confidence: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'date': self.date,
            'country': self.country,
            'group': self.group,
            'sentby': self.sentby,
            'purpose': self.purpose,
            'concept': self.concept,
            'sentto': self.sentto,
            'confidence': self.confidence,
        }

