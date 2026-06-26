#!/usr/bin/python3

from dataclasses import dataclass, field


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


def make_usage(input_tokens=None, output_tokens=None, total_tokens=None):
    """Build a normalized token-usage dict from a provider response, skipping
    fields the provider did not report. Returns an empty dict when nothing is
    available."""
    usage = {}
    if input_tokens is not None:
        usage['input_tokens'] = int(input_tokens)
    if output_tokens is not None:
        usage['output_tokens'] = int(output_tokens)
    if total_tokens is not None:
        usage['total_tokens'] = int(total_tokens)
    elif input_tokens is not None and output_tokens is not None:
        usage['total_tokens'] = int(input_tokens) + int(output_tokens)
    return usage
