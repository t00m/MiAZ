#!/usr/bin/python3

"""
Harness for the UI tests: the real application, driven in process.

These tests need a display and a repository, which is why they are not in the
main suite. They start the actual MiAZApp, let it build its window, and then
read and poke the real widgets. No synthetic mouse events and no screenshots:
what they assert is state, which is the part of the manual checklist that a
machine can judge better than a person.

They never touch your own configuration. scripts/checks/run_ui_tests.sh points
HOME at a throwaway directory and sets MIAZ_UI_SANDBOX; without that variable
every test here is skipped, so a plain `pytest` run stays green and fast.
"""

import json
import os
import time

import pytest

if not os.environ.get('MIAZ_UI_SANDBOX'):
    pytest.skip('UI tests need scripts/checks/run_ui_tests.sh',
                allow_module_level=True)

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import GLib

# Two repositories, so switching between them is observable. Alpha's documents
# use values the default configuration knows, except for the people, which no
# fresh repository has: that is what the Review path is for.
ALPHA_DOCS = [
    '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
    '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf',
    '20240101-DE-ADM-CITY-NTF-permit-JOHNDOE.pdf',
]
BETA_DOCS = ['20250301-PT-EDU-SCHOOL-RPT-report-JOHNDOE.pdf']

# A document whose sender the configuration does not know, which is what the
# workspace hides and the Review button counts. Seeded into Alpha, and left out
# of the vocabulary on purpose.
UNKNOWN_DOC = '20260401-ES-FIN-STRANGER-INV-unknown-JOHNDOE.pdf'

# Values are described, not repeated: a description equal to its code would
# make "the view shows labels, not codes" untestable.
DESCRIPTIONS = {
    'ES': 'Spain', 'DE': 'Germany', 'PT': 'Portugal',
    'FIN': 'Finance', 'HOU': 'Housing', 'ADM': 'Public Administration',
    'EDU': 'Education',
    'INV': 'Invoice', 'NTF': 'Notification', 'RPT': 'Report',
    'BANKX': 'Bank X', 'ACME': 'ACME S.A.', 'CITY': 'City Council',
    'SCHOOL': 'The School', 'JOHNDOE': 'John Doe',
}

# What repository.init() writes into a fresh repository.
DEFAULT_PLUGINS = {
    'MiAZProjectMgt': 'Project management',
    'MiAZNotes': 'Notes',
    'MiAZPeriodicity': 'Periodicity',
    'MiAZFullscreen': 'Fullscreen',
}


# Beta enables a different set on purpose: the plugins are per repository, so
# switching has to unload what Alpha had and load what Beta asks for. With the
# same list in both, a switch that ignored the list entirely would still pass.
BETA_PLUGINS = {
    'MiAZColumnVisibility': 'Column visibility',
    'MiAZFullscreen': 'Fullscreen',
}


def describe(code):
    return DESCRIPTIONS.get(code, code.title())


def _write(path, payload):
    with open(path, 'w', encoding='utf-8') as handler:
        json.dump(payload, handler)


def _make_repository(root, documents, plugins=None):
    """A repository whose configuration knows the values its documents use.

    Without this the workspace hides everything, exactly as it does for a real
    document whose sender is not in the configuration, and every assertion
    about what is displayed would be checking an empty view.
    """
    conf = os.path.join(root, '.conf')
    os.makedirs(conf, exist_ok=True)
    _write(os.path.join(conf, 'repo.json'), {'FORMAT': 1})

    countries, groups, purposes, senders, recipients = {}, {}, {}, {}, {}
    for name in documents:
        fields = name.rsplit('.', 1)[0].split('-')
        countries[fields[1]] = describe(fields[1])
        groups[fields[2]] = describe(fields[2])
        senders[fields[3]] = describe(fields[3])
        purposes[fields[4]] = describe(fields[4])
        recipients[fields[6]] = describe(fields[6])

    _write(os.path.join(conf, 'countries-used.json'), countries)
    _write(os.path.join(conf, 'groups-used.json'), groups)
    _write(os.path.join(conf, 'purposes-used.json'), purposes)
    _write(os.path.join(conf, 'senders-used.json'), senders)
    _write(os.path.join(conf, 'recipients-used.json'), recipients)
    people = dict(senders)
    people.update(recipients)
    _write(os.path.join(conf, 'people-available.json'), people)
    _write(os.path.join(conf, 'people-used.json'), people)
    _write(os.path.join(conf, 'plugins-used.json'),
           DEFAULT_PLUGINS if plugins is None else plugins)

    for name in documents:
        with open(os.path.join(root, name), 'w', encoding='utf-8') as handler:
            handler.write('document')
    return root


@pytest.fixture(scope='session')
def sandbox():
    """The throwaway HOME, with two repositories registered in it."""
    home = os.environ['HOME']
    alpha = _make_repository(os.path.join(home, 'Alpha'), ALPHA_DOCS)
    with open(os.path.join(alpha, UNKNOWN_DOC), 'w', encoding='utf-8') as handler:
        handler.write('document')
    beta = _make_repository(os.path.join(home, 'Beta'), BETA_DOCS,
                            plugins=BETA_PLUGINS)

    etc = os.path.join(home, '.MiAZ', 'etc')
    os.makedirs(etc, exist_ok=True)
    repos = {'Alpha': {'description': 'Alpha', 'path': alpha},
             'Beta': {'description': 'Beta', 'path': beta}}
    _write(os.path.join(etc, 'repos-used.json'), repos)
    _write(os.path.join(etc, 'repos-available.json'), repos)
    _write(os.path.join(etc, 'MiAZ-application.json'),
           {'current': 'Alpha', 'source': alpha})
    return {'home': home, 'Alpha': alpha, 'Beta': beta}


class Driver:
    """What a test uses to talk to the running application."""

    def __init__(self, app):
        self.app = app

    def pump(self, seconds=0.2):
        """Let the main loop work for a while.

        The application is not run with app.run(): that would block the test.
        Its main context is iterated by hand instead, which is what makes the
        whole thing drivable.
        """
        context = GLib.MainContext.default()
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            while context.pending():
                context.iteration(False)
            time.sleep(0.005)

    def wait_until(self, predicate, timeout=15, message='condition'):
        """Pump until `predicate` is true. Most work here is asynchronous."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump(0.05)
            if predicate():
                return True
        raise AssertionError(f'timed out waiting for {message}')

    def widget(self, name):
        return self.app.get_widget(name)

    def service(self, name):
        return self.app.get_service(name)

    @property
    def workspace(self):
        return self.app.get_widget('workspace')

    def displayed(self):
        """The document ids the workspace is showing, after filtering."""
        view = self.app.get_widget('workspace-view')
        model = view.get_model_filter()
        return [model.get_item(position).id for position in range(len(model))]

    def dropdown(self, gtype_name):
        """A sidebar filter dropdown, by its model type name."""
        return self.app.get_widget('ws-dropdowns')[gtype_name]

    def select_dropdown_value(self, gtype_name, value_id):
        """Pick an entry in a sidebar dropdown.

        Field dropdowns are keyed by item id. The Date one is keyed by preset
        token: its ids hold the range resolved for today, so they change daily.
        """
        dropdown = self.dropdown(gtype_name)
        model = dropdown.get_model()
        attribute = 'preset' if gtype_name == 'Date' else 'id'
        for position in range(len(model)):
            if getattr(model.get_item(position), attribute, None) == value_id:
                dropdown.set_selected(position)
                self.pump(0.4)
                return True
        raise AssertionError(f'{gtype_name} has no entry {value_id!r}')

    def select_documents(self, *ids):
        """Select rows in the workspace by document id."""
        view = self.app.get_widget('workspace-view')
        model = view.get_model_filter()
        selection = view.get_selection()
        selection.unselect_all()
        for position in range(len(model)):
            if model.get_item(position).id in ids:
                selection.select_item(position, False)
        self.pump(0.2)


@pytest.fixture(scope='session')
def miaz(sandbox):
    """The running application, built once for the whole session."""
    import sys
    sys.argv = ['miaz']

    from MiAZ.env import ENV
    from MiAZ.miaz import MiAZ
    MiAZ(ENV)

    from MiAZ.frontend.desktop.app import MiAZApp

    app = MiAZApp(application_id='io.github.t00m.MiAZ.UITest')
    app.set_env(ENV)

    started = []
    app.connect('application-started', lambda *args: started.append(True))
    app.register(None)
    app.activate()

    driver = Driver(app)
    driver.wait_until(lambda: bool(started), message='application-started')
    driver.wait_until(lambda: app.get_widget('workspace') is not None,
                      message='the workspace')
    driver.wait_until(lambda: app.get_widget('workspace').is_loaded(),
                      message='the workspace to finish loading')
    yield driver

    app.quit()
    driver.pump(0.3)


@pytest.fixture
def clean_view(miaz):
    """Reset the filters, so one test cannot leave another one blind."""
    def reset():
        for gtype_name in ('Country', 'Group', 'SentBy', 'Purpose', 'SentTo'):
            try:
                miaz.select_dropdown_value(gtype_name, 'Any')
            except AssertionError:
                pass
        try:
            miaz.select_dropdown_value('Date', 'all-documents')
        except AssertionError:
            pass
        searchbar = miaz.widget('searchentry')
        if searchbar is not None:
            searchbar.set_text('')
        miaz.pump(0.4)
    reset()
    yield miaz
    reset()
