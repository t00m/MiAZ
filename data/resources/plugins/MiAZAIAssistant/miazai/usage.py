#!/usr/bin/python3


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
