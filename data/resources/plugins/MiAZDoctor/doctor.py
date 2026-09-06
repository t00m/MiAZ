# pylint: disable=E1101

"""
# File: doctor.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Run every repository health check in one pass and repair the vocabulary
"""

import os
from gettext import gettext as _
from gettext import ngettext

from gi.repository import Adw
from gi.repository import Gtk

from MiAZ.backend.doctor import NOTE, PROBLEM, WARNING, build_report, summarise
from MiAZ.backend.duplicates import find_duplicates
from MiAZ.backend.tasks import run_in_background
from MiAZ.backend.vocabhealth import FIELD_POSITION, is_unnamed
from MiAZ.frontend.desktop.services.pluginsystem import MiAZExtension, MiAZPlugin

plugin_info = {
    'Module':        'doctor',
    'Name':          'MiAZDoctor',
    'Loader':        'Python3',
    'Description':   _('Run every repository health check in one pass and repair the vocabulary'),
    'Authors':       'Tomás Vírseda <tomasvirseda@gmail.com>',
    'Copyright':     'Copyright © 2026 Tomás Vírseda',
    'Website':       'http://github.com/t00m/MiAZ',
    'Help':          'https://github.com/t00m/MiAZ/blob/main/README.md',
    'Version':       '0.3.0',
    'Category':      'Repository',
    'Subcategory':   'Health',
    'MenuEntries':   [
        ('run', _('Run repository health check')),
    ]
}

# How each severity is shown, and what it means.
SEVERITY = {
    PROBLEM: (_('Problems'), 'error',
              _('These stop documents being filed or found.')),
    WARNING: (_('Worth cleaning'), 'warning',
              _('Nothing is broken, but the repository is drifting.')),
    NOTE: (_('Notes'), 'dim-label',
           _('Tidying, whenever it suits.')),
}

# How many offenders to list under a finding before saying "and N more".
# Vocabulary findings are not capped: each value listed can be fixed in place.
SHOWN = 12

# The checks whose items are vocabulary values, and so can be repaired here.
VOCABULARY_CHECKS = ('unknown-codes', 'undescribed-codes', 'unused-codes')


class Doctor(MiAZExtension):
    """Every repository health check in one pass, and the means to fix what
    can be fixed in place.

    The checks exist separately: duplicates in the review column, names in
    whether a document reaches the view at all. Running them one at a time
    answers "is this value described"; running them together answers "is
    this repository in good order", which is the question actually worth
    asking. The vocabulary is the part that can be repaired without leaving
    the report: a value nobody described gets a name here, a value nothing
    uses is removed here.
    """
    __gtype_name__ = 'MiAZDoctorPlugin'
    plugin = None

    def do_activate(self):
        self.app = self.object.app
        self.plugin = MiAZPlugin(self.app)
        self.plugin.register(self, plugin_info)
        self.log = self.plugin.get_logger()
        self.util = self.app.get_service('util')
        self.srvdlg = self.app.get_service('dialogs')
        self.repository = self.app.get_service('repo')
        self._autorun_in_flight = False

        self.plugin.install_settings_group(self.build_settings)

        # Connected either way, and not only when the workspace is still
        # loading: the signal fires again on every repository switch, which is
        # what lets each repository be checked with its own setting.
        self.workspace = self.app.get_widget('workspace')
        self._startup_handler = self.workspace.connect('workspace-loaded',
                                                       self.startup)
        if self.workspace.is_loaded():
            self.startup()

    def do_deactivate(self):
        if hasattr(self, '_startup_handler'):
            self.workspace.disconnect(self._startup_handler)
        self.plugin.set_started(False)

    def startup(self, *args):
        if not self.plugin.started():
            self.plugin.install_menu_entries({'run': self.run})
            self.plugin.set_started(started=True)
        self.autorun()

    def build_settings(self):
        """The one thing there is to configure: check on opening, or not."""
        group = Adw.PreferencesGroup(
            title=_('Repository health'),
            description=_('What happens when this repository is opened'))
        row = Adw.SwitchRow(
            title=_('Check the repository when it opens'),
            subtitle=_('The check runs in the background. The report opens by '
                       'itself only when something is wrong.'))
        row.set_active(bool(self.plugin.get_config_key('autorun')))
        row.connect('notify::active', self._on_autorun_setting)
        group.add(row)
        return group

    def _on_autorun_setting(self, row, gparam):
        self.plugin.set_config_key('autorun', row.get_active())

    def autorun(self, *args):
        """Run the check the repository asked for when it was opened.

        The setting lives with the repository, so a switch reads the answer of
        the repository being opened rather than the one being left.
        """
        if not self.plugin.get_config_key('autorun'):
            return
        if self._autorun_in_flight:
            # A switch while the previous repository was still being examined.
            # That answer is about to be discarded, so this one waits for it.
            return
        self._autorun_in_flight = True
        run_in_background(self.examine,
                          on_done=self._on_autorun_examined,
                          on_error=self._on_autorun_failed,
                          name='doctor-autorun')

    def _on_autorun_failed(self, error):
        self._autorun_in_flight = False
        # Nobody asked for this one, so it does not get to raise a dialog.
        self.log.error(f"Startup health check failed: {error}")

    def _on_autorun_examined(self, report):
        """Show what the startup check found, as loudly as it deserves.

        A problem stops documents being filed or found, so the report opens.
        Anything else is drift worth cleaning whenever it suits, which is a
        toast and a button rather than a window in the way of the workspace.
        """
        self._autorun_in_flight = False
        if not report:
            self.srvdlg.show_toast(_('The repository is in good order'))
            return
        if summarise(report)[PROBLEM]:
            self._show_report(report)
            return
        self.srvdlg.show_toast(
            self._verdict(report), timeout=6, button_label=_('Open'),
            on_button=lambda: self._show_report(report))

    def examine(self):
        """Read the repository and answer every check. Safe off the main loop.

        Hashing a thousand documents takes seconds, so nothing here touches a
        widget: the caller shows what comes back.
        """
        paths = self.util.get_files(self.repository.docs)
        filenames = [os.path.basename(path) for path in paths]

        empty, unreadable = [], []
        for path in paths:
            try:
                if os.path.getsize(path) == 0:
                    empty.append(os.path.basename(path))
            except OSError:
                unreadable.append(os.path.basename(path))

        vocabularies = {}
        for field in FIELD_POSITION:
            config = self.app.get_config(field)
            if config is not None:
                vocabularies[field] = config.load_used()

        # find_duplicates answers per path, listing that path's twins. One
        # group of three would otherwise be reported three times, so the paths
        # are folded back into groups by their membership.
        twins = find_duplicates(paths)
        groups, seen = [], set()
        for path in sorted(twins):
            if path in seen:
                continue
            group = sorted([path] + twins[path])
            seen.update(group)
            groups.append([os.path.basename(member) for member in group])
        duplicates = groups
        return build_report(filenames, vocabularies, duplicates=duplicates,
                            unreadable=unreadable, empty=empty)

    def run(self, *args):
        self.srvdlg.show_toast(_('Examining the repository...'))
        run_in_background(self.examine,
                          on_done=self._on_examined,
                          on_error=self._on_failed,
                          name='doctor')

    def _on_failed(self, error):
        self.log.error(f"Health check failed: {error}")
        self.srvdlg.show_error(title=_('Health check failed'), body=str(error))

    def _on_examined(self, report):
        if not report:
            self.srvdlg.show_toast(_('The repository is in good order'))
            return
        self._show_report(report)

    def _show_report(self, report):
        """Put the report on screen. Asked for from the menu, or offered by
        the startup check when it found something worth stopping for."""
        window = self.app.get_widget('window')
        # A report of problems is not good news, so it does not get the dialog
        # that congratulates the user. Warning while anything needs doing.
        counted = summarise(report)
        needs_doing = counted[PROBLEM] or counted[WARNING]
        dialog = self.srvdlg.create(
            dtype='warning' if needs_doing else 'info',
            title=_('Repository health'),
            body=self._verdict(report),
            widget=self._build_page(report),
            width=800, height=640)
        self.app.add_widget('doctor-dialog', dialog)
        dialog.present(window)

    @staticmethod
    def _verdict(report):
        """One line saying what was found, counting the things, not the checks.

        Saying "1 problem" when the one problem is 31 badly named documents
        reads as though there were one document to fix.
        """
        counted = {PROBLEM: 0, WARNING: 0, NOTE: 0}
        for finding in report:
            counted[finding.severity] += finding.count
        parts = []
        if counted[PROBLEM]:
            parts.append(ngettext('{count} problem', '{count} problems',
                                  counted[PROBLEM]).format(count=counted[PROBLEM]))
        if counted[WARNING]:
            parts.append(ngettext('{count} thing worth cleaning',
                                  '{count} things worth cleaning',
                                  counted[WARNING]).format(count=counted[WARNING]))
        if counted[NOTE]:
            parts.append(ngettext('{count} note', '{count} notes',
                                  counted[NOTE]).format(count=counted[NOTE]))
        return ', '.join(parts)

    def _build_page(self, report):
        page = Adw.PreferencesPage()
        page.set_hexpand(True)
        page.set_vexpand(True)
        for severity in (PROBLEM, WARNING, NOTE):
            findings = [finding for finding in report if finding.severity == severity]
            if not findings:
                continue
            title, css, explanation = SEVERITY[severity]
            group = Adw.PreferencesGroup()
            group.set_title(title)
            group.set_description(explanation)
            for finding in findings:
                group.add(self._build_row(finding, css))
            page.add(group)
        return page

    def _build_row(self, finding, css):
        row = Adw.ExpanderRow()
        row.set_title(_(finding.summary))
        row.set_subtitle(finding.hint)
        count = Gtk.Label(label=str(finding.count))
        count.add_css_class(css)
        count.add_css_class('title-4')
        count.set_valign(Gtk.Align.CENTER)
        row.add_suffix(count)
        # A report nobody can act on is only half of one. Narrowing the view to
        # what a finding names is what turns it into work that can be done.
        if finding.documents:
            show = Gtk.Button(label=_('Show'))
            show.set_valign(Gtk.Align.CENTER)
            show.set_tooltip_text(
                ngettext('Show this document in the workspace',
                         'Show these {count} documents in the workspace',
                         len(finding.documents)).format(
                             count=len(finding.documents)))
            show.connect('clicked', self._on_show, finding)
            row.add_suffix(show)
        if finding.check in VOCABULARY_CHECKS:
            for field, code, count in finding.items:
                row.add_row(self._build_repair_row(finding.check, field, code, count))
        else:
            for text in self._describe(finding):
                line = Adw.ActionRow()
                line.set_title(text)
                line.set_title_lines(1)
                row.add_row(line)
        return row

    def _build_repair_row(self, check, field, code, count):
        """One vocabulary value with what can be done about it: a name for
        a value that has none, removal for a value nothing uses."""
        row = Adw.ActionRow()
        row.set_title(code)
        row.set_subtitle(_('{field}, used by {count} documents').format(
            field=field, count=count) if count else _('{field}, used by none').format(field=field))
        if check == 'unused-codes':
            button = Gtk.Button(label=_('Remove'))
            button.add_css_class('destructive-action')
            button.set_valign(Gtk.Align.CENTER)
            button.connect('clicked', self._on_remove, field, code, row)
            row.add_suffix(button)
            return row
        entry = Gtk.Entry()
        entry.set_placeholder_text(_('Describe this value'))
        entry.set_valign(Gtk.Align.CENTER)
        entry.set_width_chars(28)
        description = self._description_of(field, code)
        if not is_unnamed(code, description):
            entry.set_text(description)
        button = Gtk.Button(label=_('Save'))
        button.set_valign(Gtk.Align.CENTER)
        button.connect('clicked', self._on_save, field, code, entry, row)
        entry.connect('activate', lambda *_: button.emit('clicked'))
        row.add_suffix(entry)
        row.add_suffix(button)
        return row

    def _description_of(self, field, code):
        config = self.app.get_config(field)
        if config is None:
            return ''
        return config.load_used().get(code, '') or ''

    def _on_save(self, button, field, code, entry, row):
        """Name a value, adding it to the vocabulary when it was not there."""
        description = entry.get_text().strip()
        if not description:
            return
        config = self.app.get_config(field)
        if config is None:
            return
        if not config.exists_available(code):
            config.add_available(code, description)
        if not config.exists_used(code):
            config.add_used(code, description)
        # add_used only adds: it leaves a key that is already there alone, and
        # every value this form is offered for is already there, described by
        # nothing but itself. set_description is the one that writes over it,
        # in every file of the repository that holds the key.
        config.set_description(code, description)
        row.set_subtitle(_('Saved as "{description}"').format(description=description))
        button.set_sensitive(False)
        entry.set_sensitive(False)

    def _on_remove(self, button, field, code, row):
        config = self.app.get_config(field)
        if config is None:
            return
        config.remove_used(code)
        row.set_subtitle(_('Removed from the vocabulary'))
        button.set_sensitive(False)

    def _on_show(self, button, finding):
        """Put the documents a finding named in front of the user."""
        workspace = self.app.get_widget('workspace')
        if workspace is None:
            return
        workspace.show_documents(finding.documents, label=_(finding.summary))
        if finding.check == 'duplicates':
            # A list of copies is not usable until the copies are told apart.
            # The workspace has the column that says which document matches
            # which; only this finding is about content, so only this one asks
            # for the scan behind it.
            workspace.show_duplicates()
        dialog = self.app.get_widget('doctor-dialog')
        if dialog is not None:
            dialog.close()

    @staticmethod
    def _describe(finding):
        """The offenders, as lines of text, capped so a row stays readable."""
        lines = []
        for item in finding.items[:SHOWN]:
            if isinstance(item, tuple) and len(item) == 3:
                field, code, count = item
                lines.append(_('{code} ({field}), {count} documents').format(
                    code=code, field=field, count=count) if count else
                    _('{code} ({field})').format(code=code, field=field))
            elif isinstance(item, (list, tuple)):
                lines.append(', '.join(str(part) for part in item))
            else:
                lines.append(str(item))
        remaining = finding.count - len(lines)
        if remaining > 0:
            lines.append(_('and {count} more').format(count=remaining))
        return lines
