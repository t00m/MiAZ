"""What a step is called, and how it is written out for the user.

The vocabulary is fixed: undo, redo, change, history. A word from git does not
belong in front of somebody filing an invoice.
"""

import os
import datetime
from gettext import gettext as _
from gettext import ngettext

# How many lines a section shows before it says how many are left.
SHOWN = 12

# A configuration file, and what it is called in the interface.
CONFIG_LABELS = {
    'countries': _('Countries'),
    'groups': _('Groups'),
    'purposes': _('Purposes'),
    'concepts': _('Concepts'),
    'people': _('People'),
    'senders': _('Senders'),
    'recipients': _('Recipients'),
    'projects': _('Projects'),
    'plugins': _('Plugins'),
    'repo': _('Repository settings'),
}


def subject(counts: dict) -> str:
    """The name a step is recorded under.

    `counts` is what the signals said happened: how many documents were added,
    renamed or deleted, and whether the configuration changed. An empty one
    means only the file monitor spoke, so the change came from somewhere else.
    """
    parts = []
    if counts.get('added'):
        parts.append(ngettext('Added %d document', 'Added %d documents', counts['added']) % counts['added'])
    if counts.get('renamed'):
        parts.append(ngettext('Renamed %d document', 'Renamed %d documents', counts['renamed']) % counts['renamed'])
    if counts.get('deleted'):
        parts.append(ngettext('Deleted %d document', 'Deleted %d documents', counts['deleted']) % counts['deleted'])
    if counts.get('config'):
        parts.append(_('Changed settings'))
    if not parts:
        return _('Changed outside MiAZ')
    # The first part keeps its capital and the rest join it in lower case, so
    # a step that did two things reads as one sentence.
    return ', '.join([parts[0]] + [part[0].lower() + part[1:] for part in parts[1:]])


def when(timestamp: int, now=None) -> str:
    """A moment, written the way a person would say it."""
    now = datetime.datetime.now() if now is None else now
    moment = datetime.datetime.fromtimestamp(timestamp)
    clock = moment.strftime('%H:%M')
    days = (now.date() - moment.date()).days
    if days == 0:
        return _('Today at %s') % clock
    if days == 1:
        return _('Yesterday at %s') % clock
    return _('%(date)s at %(time)s') % {
        'date': moment.strftime('%-d %B'), 'time': clock}


def config_label(path: str):
    """What a configuration file is called, or None when it is not one."""
    if not path.startswith('.conf/'):
        return None
    parts = path.split('/')
    if len(parts) > 2 and parts[1] == 'plugins':
        return _('%s settings') % parts[2]
    name = os.path.splitext(parts[-1])[0]
    for key, label in CONFIG_LABELS.items():
        if name.startswith(key):
            return label
    return _('Settings')


# The status git reports, the heading it is listed under, and the order the
# headings appear in.
STATUS_TITLES = (
    ('A', _('Added')),
    ('R', _('Renamed')),
    ('M', _('Changed')),
    ('D', _('Deleted')),
)


def sections(changes: list, cap: int = SHOWN) -> list:
    """[(title, [line])] for a dialog: filenames only, never file content."""
    grouped = {status: [] for status, _title in STATUS_TITLES}
    configuration = []
    for status, path, other in changes:
        label = config_label(path)
        if label is not None:
            if label not in configuration:
                configuration.append(label)
            continue
        if status == 'R':
            grouped['R'].append(_('%(old)s -> %(new)s') % {'old': path, 'new': other})
        else:
            grouped.setdefault(status, []).append(path)

    listed = []
    for status, title in STATUS_TITLES:
        lines = grouped.get(status, [])
        if lines:
            listed.append((title, _cap(lines, cap)))
    if configuration:
        listed.append((_('Configuration'), _cap(configuration, cap)))
    return listed


def _cap(lines: list, cap: int) -> list:
    if len(lines) <= cap + 1:
        return lines
    left = len(lines) - cap
    return lines[:cap] + [_('and %d more') % left]


def body(changes: list, timestamp: int, now=None) -> str:
    """The dialog body: when the change was made, and what it touched."""
    lines = [when(timestamp, now), '']
    for title, entries in sections(changes):
        lines.append(title)
        lines.extend(f'  {entry}' for entry in entries)
        lines.append('')
    return '\n'.join(lines).strip()


def headline(changes: list) -> str:
    """One line for a button tooltip."""
    counts = {}
    for status, path, _other in changes:
        if config_label(path) is not None:
            counts['config'] = 1
            continue
        counts_key = {'A': 'added', 'R': 'renamed', 'D': 'deleted'}.get(status)
        if counts_key is None:
            continue
        counts[counts_key] = counts.get(counts_key, 0) + 1
    return subject(counts)
