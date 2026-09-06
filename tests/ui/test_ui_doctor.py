#!/usr/bin/python3

"""UI: the Doctor report's Show button, through the real plugin.

The workspace side is covered in test_ui_widgets.py. This drives the plugin
itself: the report is built from the sandbox repository, the dialog is the one
the user sees, and the button is clicked rather than the method called. That is
where the bug was, so that is what is tested.
"""

import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Adw, Gtk

import pytest

from MiAZ.backend.doctor import Finding, PROBLEM, WARNING


def buttons(widget, found=None):
    """Every Gtk.Button under a widget, depth first."""
    found = [] if found is None else found
    child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
    while child is not None:
        if isinstance(child, Gtk.Button):
            found.append(child)
        buttons(child, found)
        child = child.get_next_sibling()
    return found


@pytest.fixture
def doctor(miaz):
    """The Doctor plugin, loaded for the test and left as it was found."""
    system = miaz.service('plugin-system')
    info = system.get_plugin_info('doctor')
    assert info is not None, 'the Doctor plugin is not in the index'
    was_loaded = system.is_plugin_loaded(info)
    if not was_loaded:
        assert system.load_plugin(info), 'the Doctor plugin did not load'
    miaz.pump(0.5)
    instance = system.get_extension('doctor')
    assert instance is not None, 'the Doctor plugin has no extension instance'
    yield instance
    if not was_loaded:
        system.unload_plugin(info)
        miaz.pump(0.3)


def test_every_show_button_puts_its_documents_on_screen(clean_view, doctor):
    """Show is the whole point of the report: a finding nobody can look at is
    half a finding. Every button is clicked, because they broke together.

    The filters are narrowed to something that excludes the findings first.
    With Review on and a search in the box, every Show showed an empty
    workspace: Review asks for pending documents while an explicit list lifts
    the pending check, and the two together match nothing.
    """
    workspace = clean_view.workspace
    review = clean_view.widget('workspace-togglebutton-pending-docs')
    search = clean_view.widget('searchentry')

    report = doctor.examine()
    findings = [finding for finding in report if finding.documents]
    assert findings, 'the sandbox repository is too healthy to test with'

    try:
        for index, finding in enumerate(findings):
            search.set_text('nothing matches this')
            review.set_active(True)
            clean_view.pump(0.5)

            doctor._on_examined(report)
            clean_view.pump(0.5)
            dialog = clean_view.widget('doctor-dialog')
            assert dialog is not None, 'the report dialog was not built'
            shows = [button for button in buttons(dialog)
                     if button.get_label() == 'Show']
            assert len(shows) == len(findings), 'one Show per finding with documents'

            shows[index].emit('clicked')
            clean_view.wait_until(
                lambda: sorted(clean_view.displayed()) == sorted(finding.documents),
                message=f'the documents {finding.check} named')
            assert workspace.get_shown_documents() == frozenset(finding.documents)
            workspace.clear_documents()
            clean_view.pump(0.5)
    finally:
        review.set_active(False)
        search.set_text('')
        workspace.clear_documents()
        clean_view.pump(0.5)


def rows(widget, found=None):
    """Every Adw preferences row under a widget, depth first."""
    found = [] if found is None else found
    child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
    while child is not None:
        if isinstance(child, (Adw.SwitchRow, Adw.ActionRow)):
            found.append(child)
        rows(child, found)
        child = child.get_next_sibling()
    return found


@pytest.fixture
def autorun_off(miaz, doctor):
    """The startup check off before and after, whatever the test does."""
    doctor.plugin.set_config_key('autorun', False)
    miaz.app.remove_widget('doctor-dialog')
    yield doctor
    doctor.plugin.set_config_key('autorun', False)
    dialog = miaz.widget('doctor-dialog')
    if dialog is not None:
        dialog.close()
    miaz.app.remove_widget('doctor-dialog')
    miaz.pump(0.3)


def test_the_settings_group_offers_the_startup_check(autorun_off):
    """The switch is how a repository asks to be checked when it opens."""
    group = autorun_off.build_settings()
    assert isinstance(group, Adw.PreferencesGroup)
    switches = [row for row in rows(group) if isinstance(row, Adw.SwitchRow)]
    assert len(switches) == 1, 'one switch, for the startup check'
    assert not switches[0].get_active(), 'off until it is asked for'


def test_switching_it_on_is_remembered_by_the_repository(autorun_off):
    """The answer belongs to the repository, not to the installation: one
    repository being cleaned up wants the check, an archive does not.
    """
    switch = [row for row in rows(autorun_off.build_settings())
              if isinstance(row, Adw.SwitchRow)][0]
    switch.set_active(True)
    assert autorun_off.plugin.get_config_key('autorun') is True
    switch.set_active(False)
    assert autorun_off.plugin.get_config_key('autorun') is False


def test_the_check_runs_when_the_repository_opens(miaz, autorun_off):
    """Switched on, opening the repository is enough to get the report.

    The sandbox repository holds a document whose sender the configuration
    does not know, which is a problem, so the report opens as a dialog.
    """
    autorun_off.plugin.set_config_key('autorun', True)
    miaz.workspace.emit('workspace-loaded')
    miaz.wait_until(lambda: miaz.widget('doctor-dialog') is not None,
                    message='the report the startup check found')


def test_nothing_runs_while_the_setting_is_off(miaz, autorun_off):
    """Off is off: no report, no toast, no repository read."""
    miaz.workspace.emit('workspace-loaded')
    miaz.pump(2.0)
    assert miaz.widget('doctor-dialog') is None


def test_a_report_without_problems_is_a_toast(miaz, autorun_off):
    """Nothing broken means nothing interrupts: the verdict goes to a toast
    with a button, and the workspace is left alone.
    """
    toasts = []
    original = autorun_off.srvdlg.show_toast
    autorun_off.srvdlg.show_toast = lambda *args, **kwargs: toasts.append(
        (args, kwargs)) or original(*args, **kwargs)
    try:
        report = [Finding('duplicates', WARNING, 'Groups of documents',
                          [['a.pdf', 'b.pdf']], 'Keep one of each group.',
                          documents=['a.pdf', 'b.pdf'])]
        autorun_off._on_autorun_examined(report)
        miaz.pump(0.5)
    finally:
        autorun_off.srvdlg.show_toast = original

    assert miaz.widget('doctor-dialog') is None, 'a warning does not interrupt'
    assert len(toasts) == 1, 'the verdict is said once'
    args, kwargs = toasts[0]
    assert '1 thing worth cleaning' in args[0]
    assert kwargs.get('button_label'), 'the toast opens the report'


def test_a_healthy_repository_says_so(miaz, autorun_off):
    """A check that finds nothing has to say it ran."""
    toasts = []
    original = autorun_off.srvdlg.show_toast
    autorun_off.srvdlg.show_toast = lambda *args, **kwargs: toasts.append(
        (args, kwargs)) or original(*args, **kwargs)
    try:
        autorun_off._on_autorun_examined([])
        miaz.pump(0.5)
    finally:
        autorun_off.srvdlg.show_toast = original

    assert miaz.widget('doctor-dialog') is None
    assert len(toasts) == 1
    assert 'good order' in toasts[0][0][0]


def test_a_problem_opens_the_report(miaz, autorun_off):
    """A problem stops documents being filed or found, so it is shown."""
    report = [Finding('names', PROBLEM, 'Documents not named in seven fields',
                      ['a.pdf'], 'Rename them.', documents=['a.pdf'])]
    autorun_off._on_autorun_examined(report)
    miaz.wait_until(lambda: miaz.widget('doctor-dialog') is not None,
                    message='the report a problem opens')


def test_the_group_reaches_the_repository_settings_dialog(miaz, doctor):
    """Building the group is not enough: it has to be offered to the dialog,
    under the heading the plugin's own Category names."""
    registry = miaz.service('plugin-system').settings
    offered = [(category, owner) for category, owner, _b in registry.builders()]
    assert ('Repository', 'MiAZDoctor') in offered, offered


def test_the_inline_form_describes_a_value_that_already_has_a_row(miaz, doctor):
    """The whole point of the vocabulary rows: a value described by nothing
    but itself gets a name here.

    The save went through config.add_used, which adds a key and does nothing
    at all when the key is already there. Every value the check reports as
    undescribed is already there, so the form never changed anything.
    """
    config = miaz.app.get_config('SentBy')
    people = miaz.app.get_config('Person')
    key = 'ACME'
    original = config.load_used()[key]
    entry = Gtk.Entry()
    entry.set_text('ACME Corporation')
    row = Adw.ActionRow()
    button = Gtk.Button()
    try:
        doctor._on_save(button, 'SentBy', key, entry, row)
        miaz.pump(0.3)
        assert config.load_used()[key] == 'ACME Corporation'
        assert people.load_available()[key] == 'ACME Corporation'
        assert people.load_used()[key] == 'ACME Corporation'
    finally:
        config.set_description(key, original)
        miaz.pump(0.3)


def test_the_inline_form_still_adds_a_value_the_vocabulary_lacks(miaz, doctor):
    """The other half of that row: a value used by documents and unknown to
    the repository has to be added, not only described."""
    config = miaz.app.get_config('SentBy')
    key = 'STRANGER'
    assert not config.exists_used(key), 'the sandbox keeps this one unknown'
    entry = Gtk.Entry()
    entry.set_text('A Stranger')
    row = Adw.ActionRow()
    try:
        doctor._on_save(Gtk.Button(), 'SentBy', key, entry, row)
        miaz.pump(0.3)
        assert config.load_used()[key] == 'A Stranger'
        assert config.load_available()[key] == 'A Stranger'
    finally:
        config.remove_used(key)
        config.remove_available(key)
        miaz.pump(0.3)


def test_showing_the_duplicates_finding_tells_the_copies_apart(clean_view, doctor):
    """177 documents in date order do not say which is a copy of which.

    The copy column answers that, and it stays hidden until something has been
    scanned. Showing a group of copies is exactly the moment to ask.
    """
    index = clean_view.service('index')
    view = clean_view.widget('workspace-view')
    index._invalidate_duplicates()
    view.column_duplicate.set_visible(False)

    report = doctor.examine()
    finding = next((f for f in report if f.check == 'duplicates'), None)
    assert finding is not None, 'the sandbox documents share their content'

    doctor._on_show(Gtk.Button(), finding)
    clean_view.wait_until(lambda: not index.duplicates_stale(),
                          message='the duplicate scan')
    clean_view.pump(0.5)
    assert view.column_duplicate.get_visible() is True
    assert sorted(clean_view.displayed()) == sorted(finding.documents)
    clean_view.workspace.clear_documents()
    clean_view.pump(0.3)


def test_showing_another_finding_leaves_the_copy_column_alone(clean_view, doctor):
    """Only the finding about copies asks for the scan; the rest are not
    about content and should not pay 0.9 seconds of reading for it.
    """
    index = clean_view.service('index')
    view = clean_view.widget('workspace-view')
    index._invalidate_duplicates()
    view.column_duplicate.set_visible(False)

    report = doctor.examine()
    finding = next((f for f in report
                    if f.documents and f.check != 'duplicates'), None)
    assert finding is not None, 'the sandbox has a finding of another kind'

    doctor._on_show(Gtk.Button(), finding)
    clean_view.pump(2.0)
    assert index.duplicates_stale() is True
    assert view.column_duplicate.get_visible() is False
    clean_view.workspace.clear_documents()
    clean_view.pump(0.3)
