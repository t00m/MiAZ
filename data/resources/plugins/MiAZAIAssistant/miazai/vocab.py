
import json
import pathlib
from dataclasses import dataclass
from typing import Dict

_FIELD_CONFIG = {
    'country': {'used': 'countries',  'available': 'countries'},
    'group':   {'used': 'groups',     'available': 'groups'},
    'sentby':  {'used': 'senders',    'available': 'people'},
    'purpose': {'used': 'purposes',   'available': 'purposes'},
    'sentto':  {'used': 'recipients', 'available': 'people'},
    'concept': {'used': 'concepts',   'available': 'concepts'},
}


@dataclass(frozen=True)
class Vocabulary:
    used: Dict[str, Dict[str, str]]
    available: Dict[str, Dict[str, str]]


def load_vocabulary(conf_dir: pathlib.Path) -> Vocabulary:
    used, avail = {}, {}
    for field, stems in _FIELD_CONFIG.items():
        used[field] = _read(conf_dir / f"{stems['used']}-used.json")
        avail[field] = _read(conf_dir / f"{stems['available']}-available.json")
    return Vocabulary(used=used, available=avail)


def _read(path: pathlib.Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    try:
        return dict(json.loads(path.read_text()))
    except Exception:
        return {}
