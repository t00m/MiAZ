#!/usr/bin/python3


def system_prompt(vocab) -> str:
    return (
        "You are a filing assistant for MiAZ. Documents are renamed "
        "to follow the strict 7-field convention:\n\n"
        "  {date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}\n\n"
        "Rules:\n"
        "  - date: YYYYMMDD\n"
        "  - country: ISO 3166-1 alpha-2 code (e.g. ES, DE, US)\n"
        "  - group: a coarse subject grouping (e.g. HEALTH, BANK, EDU)\n"
        "  - sentby: the document's issuer / sender\n"
        "  - purpose: a short purpose tag (e.g. INV for invoice, RPT for report)\n"
        "  - concept: a free-form descriptor of THIS specific document\n"
        "  - sentto: the recipient\n\n"
        "Prefer values from the repository's existing vocabulary "
        "(provided below) when they fit. Otherwise propose a NEW value "
        "and the user will be asked to confirm it.\n\n"
        f"Existing vocabulary (key → description):\n{_format_vocab(vocab)}\n\n"
        "Return your answer via the propose_filename tool."
    )


def user_prompt() -> str:
    return (
        "Please propose values for all seven fields based on the "
        "document content. Also return a per-field confidence "
        "between 0 and 1 in the 'confidence' object."
    )


def schema() -> dict:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['date', 'country', 'group', 'sentby',
                     'purpose', 'concept', 'sentto', 'confidence'],
        'properties': {
            'date':    {'type': 'string', 'pattern': r'^\d{8}$'},
            'country': {'type': 'string', 'maxLength': 16},
            'group':   {'type': 'string', 'maxLength': 32},
            'sentby':  {'type': 'string', 'maxLength': 32},
            'purpose': {'type': 'string', 'maxLength': 32},
            'concept': {'type': 'string', 'maxLength': 128},
            'sentto':  {'type': 'string', 'maxLength': 32},
            'confidence': {
                'type': 'object',
                'additionalProperties': {'type': 'number', 'minimum': 0, 'maximum': 1},
            },
        },
    }


def _format_vocab(vocab) -> str:
    out = []
    for field, entries in vocab.used.items():
        items = ', '.join(f"{k}={v}" for k, v in list(entries.items())[:50])
        out.append(f"  {field}: {items or '(empty)'}")
    return '\n'.join(out)
