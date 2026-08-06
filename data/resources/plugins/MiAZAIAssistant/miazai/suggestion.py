#!/usr/bin/python3

from dataclasses import dataclass, field

from miazai.usage import make_usage  # re-export: single definition lives in usage.py


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

