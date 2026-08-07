#!/usr/bin/python3

"""
Manual check: set_query() writes the query back into the sidebar.

set_query() applies a DocumentQuery built elsewhere: a plugin, or a saved
search. It used to set the filter only in memory, leaving the sidebar showing
something else, and the next time any filter control changed the query was
rebuilt from those controls and the applied filter silently vanished.

This drives it in the running app and checks both halves:

  1. after set_query(), the sidebar controls show what the query asked for
  2. after changing one unrelated control, the rest of the query survives

Usage:

    PYTHONPATH=. python scripts/devel/check_set_query.py [--watch SECONDS]

Watch the sidebar while it runs. With --watch it pauses between steps so the
controls can be seen moving; the default is 3 seconds per step. The window
opens, the checks run, and it quits by itself.
"""

import sys
from datetime import datetime

from MiAZ.backend.query import DATE_PRESET_LAST_12_MONTHS, DocumentQuery

WATCH_DEFAULT = 3


def dropdown_state(app):
    """What each sidebar control currently shows."""
    dropdowns = app.get_widget('ws-dropdowns') or {}
    state = {}
    for name, dropdown in dropdowns.items():
        selected = dropdown.get_selected_item()
        state[name] = selected.id if selected is not None else None
    entry = app.get_widget('searchentry')
    state['search'] = entry.get_text() if entry is not None else None
    return state


def date_title(app):
    """The visible label of the selected date entry."""
    dropdowns = app.get_widget('ws-dropdowns') or {}
    dropdown = dropdowns.get('Date')
    if dropdown is None:
        return None
    selected = dropdown.get_selected_item()
    return selected.title if selected is not None else None


def pick_a_sender(app):
    """A sender with a document inside the window this check applies.

    Any sender will not do. Filtering to one with nothing in the last twelve
    months leaves the view empty, and an empty view has no values to offer, so
    the sidebar dropdowns collapse to "Any" by design. That says nothing about
    whether set_query wrote them.
    """
    from MiAZ.backend.query import parse_date

    util = app.get_service('util')
    index = app.get_service('index')
    since = util.since_date_last_n_months(datetime.now(), 12).date()
    for doc in index.documents():
        if not doc.sentby_id:
            continue
        when = parse_date(doc.date)
        if when is not None and when >= since:
            return doc.sentby_id
    return None


def run_checks(app, watch):
    from gi.repository import GLib

    workspace = app.get_widget('workspace')
    sender = pick_a_sender(app)
    if sender is None:
        print('RESULT fatal: no document with a sender to filter on')
        app.quit()
        return False

    steps = []

    def step_apply():
        print(f'RESULT baseline   {dropdown_state(app)}')
        query = DocumentQuery(sentby=sender, date_preset=DATE_PRESET_LAST_12_MONTHS)
        missing = workspace.set_query(query)
        print(f'RESULT applied    sentby={sender} date_preset=last-12-months')
        print(f'RESULT unrepresented {missing}')
        # The dropdowns are narrowed back to the visible values on idle, so
        # check the settled state rather than the instant after the call.
        GLib.timeout_add(500, step_verify, missing)
        return False

    def step_verify(missing):
        visible = workspace.view.filter_model.get_n_items()
        print(f'RESULT visible    {visible} document(s) match the applied query')
        state = dropdown_state(app)
        applied = workspace.get_query()
        print(f'RESULT sidebar    {state}')
        print(f'RESULT date-label {date_title(app)}')
        print(f'RESULT query-back sentby={applied.sentby} '
              f'preset={applied.date_preset} '
              f'since={applied.date_since} until={applied.date_until}')

        ok = (state.get('SentBy') == sender
              and applied.sentby == sender
              and applied.date_preset == DATE_PRESET_LAST_12_MONTHS
              and applied.date_since is not None)
        print(f'RESULT step1-writes-back {"PASS" if ok else "FAIL"}')
        steps.append(ok)
        return False

    def step_survive():
        # Change one unrelated control the way a user would. The query is
        # rebuilt from the sidebar; the sender must still be in it.
        dropdowns = app.get_widget('ws-dropdowns') or {}
        group = dropdowns.get('Group')
        if group is not None and group.get_model().get_n_items() > 1:
            group.set_selected(1)
        applied = workspace.get_query()
        print(f'RESULT after-touching-group sentby={applied.sentby} '
              f'group={applied.group} preset={applied.date_preset}')
        ok = applied.sentby == sender and applied.date_preset == DATE_PRESET_LAST_12_MONTHS
        print(f'RESULT step2-survives-a-widget-change {"PASS" if ok else "FAIL"}')
        steps.append(ok)
        return False

    def finish():
        print(f'RESULT overall {"PASS" if steps and all(steps) else "FAIL"}')
        app.quit()
        return False

    GLib.timeout_add_seconds(0, step_apply)
    GLib.timeout_add_seconds(watch, step_survive)
    GLib.timeout_add_seconds(watch * 2, finish)
    return False


def main():
    watch = WATCH_DEFAULT
    if '--watch' in sys.argv:
        watch = int(sys.argv[sys.argv.index('--watch') + 1])
    # The app parses its own arguments.
    sys.argv = ['miaz']

    from MiAZ.env import ENV
    from MiAZ.miaz import MiAZ
    MiAZ(ENV)

    from gi.repository import GLib
    from MiAZ.frontend.desktop.app import MiAZApp

    app = MiAZApp(application_id=ENV['APP']['ID'])
    app.set_env(ENV)
    # Wait for the first scan to finish before touching the filters.
    app.connect('application-started',
                lambda *_a: GLib.timeout_add_seconds(3, run_checks, app, watch))
    app.run()


if __name__ == '__main__':
    main()
