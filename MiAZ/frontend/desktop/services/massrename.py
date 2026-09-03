# File: massrename.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Core mass-rename service. Sets a filename field across the
#              selected documents, with a live preview.

import os
from datetime import datetime
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import File, Group, Country, Purpose, SentBy, SentTo, Date, Concept
from MiAZ.backend.util import date_is_valid, UNKNOWN_DATE
from MiAZ.frontend.desktop.widgets.configview import MiAZCountries
from MiAZ.frontend.desktop.widgets.configview import MiAZGroups
from MiAZ.frontend.desktop.widgets.configview import MiAZPurposes
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentBy
from MiAZ.frontend.desktop.widgets.configview import MiAZPeopleSentTo
from MiAZ.frontend.desktop.widgets.dateentry import MiAZDateEntry
from MiAZ.frontend.desktop.widgets.views import MiAZColumnViewMassRename

# Field index in the 7-field filename convention
# {date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
Field = {
    Date: 0,
    Country: 1,
    Group: 2,
    SentBy: 3,
    Purpose: 4,
    Concept: 5,
    SentTo: 6,
}

Configview = {
    'Country': MiAZCountries,
    'Group': MiAZGroups,
    'Purpose': MiAZPurposes,
    'SentBy': MiAZPeopleSentBy,
    'SentTo': MiAZPeopleSentTo,
}


# concept-field transformations

def parse_positions(spec, count):
    """Parse concept fields"""
    indices = set()
    for part in (spec or '').split(','):
        part = part.strip()
        if not part:
            continue
        try:
            if '-' in part:
                lo, _, hi = part.partition('-')
                start = int(lo) if lo.strip() else 1
                end = int(hi) if hi.strip() else count
            else:
                start = end = int(part)
        except ValueError:
            continue
        for pos in range(start, end + 1):
            if 1 <= pos <= count:
                indices.add(pos - 1)
    return sorted(indices)


def keep_tokens(concept, spec, sep='_'):
    tokens = concept.split(sep)
    keep = parse_positions(spec, len(tokens))
    return sep.join(tokens[i] for i in keep)


def remove_tokens(concept, spec, sep='_'):
    tokens = concept.split(sep)
    drop = set(parse_positions(spec, len(tokens)))
    return sep.join(t for i, t in enumerate(tokens) if i not in drop)


def add_prefix(concept, text, sep='_'):
    if not text:
        return concept
    if not concept:
        return text
    return f"{text}{sep}{concept}"


def add_suffix(concept, text, sep='_'):
    if not text:
        return concept
    if not concept:
        return text
    return f"{concept}{sep}{text}"


def find_replace(concept, find, replace):
    if not find:
        return concept
    return concept.replace(find, replace)


def change_case(concept, mode):
    if mode == 'upper':
        return concept.upper()
    if mode == 'lower':
        return concept.lower()
    if mode == 'title':
        return concept.title()
    return concept


def set_value(concept, value):
    return value


def apply_concept_op(op, concept, params):
    sep = params.get('sep') or '_'
    if op == 'keep':
        return keep_tokens(concept, params.get('positions', ''), sep)
    if op == 'remove':
        return remove_tokens(concept, params.get('positions', ''), sep)
    if op == 'prefix':
        return add_prefix(concept, params.get('text', ''), sep)
    if op == 'suffix':
        return add_suffix(concept, params.get('text', ''), sep)
    if op == 'replace':
        return find_replace(concept, params.get('find', ''), params.get('replace', ''))
    if op == 'case':
        return change_case(concept, params.get('mode', ''))
    if op == 'set':
        return set_value(concept, params.get('value', ''))
    return concept


class MiAZMassRename(GObject.GObject):
    """Mass-rename the selected documents by setting one filename field.
    """
    __gtype_name__ = 'MiAZMassRename'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZMassRename')
        self.util = app.get_service('util')
        self.factory = app.get_service('factory')
        self.srvdlg = app.get_service('dialogs')
        self.actions = app.get_service('actions')
        self.repository = app.get_service('repo')
        self.config = app.get_config_dict()
        self.build_menu()

    def build_menu(self):
        """Build (once) the Gio.Menu of the seven mass-rename functions and
        register their app actions. Stored as widget 'massrename-menu' and
        reused by every consumer."""
        menu = self.app.get_widget('massrename-menu')
        if menu is not None:
            return menu
        menu = Gio.Menu.new()
        entries = [
            ('massrename-date', Date, self.rename_date),
            ('massrename-country', Country, self.rename_field),
            ('massrename-group', Group, self.rename_field),
            ('massrename-purpose', Purpose, self.rename_field),
            ('massrename-concept', Concept, self.rename_concept),
            ('massrename-sentby', SentBy, self.rename_field),
            ('massrename-sentto', SentTo, self.rename_field),
        ]
        for name, item_type, callback in entries:
            label = _(item_type.__title__)
            menuitem = self.factory.create_menuitem(
                name=name, label=label, callback=callback,
                data=item_type, shortcuts=None)
            menu.append_item(menuitem)
        self.app.add_widget('massrename-menu', menu)
        return menu

    def _selection(self):
        workspace = self.app.get_widget('workspace')
        items = workspace.get_selected_items() if workspace is not None else []
        if self.actions.stop_if_no_items():
            self.log.debug("No items selected")
            return None
        return items

    def rename_field(self, action, data, item_type):
        """Set a controlled field (country/group/purpose/sentby/sentto) to a
        value picked from that field's vocabulary, across the selection."""
        items = self._selection()
        if items is None:
            return

        def update_columnview(dropdown, gparamobj, columnview, item_type, items):
            citems = []
            for item in items:
                selected = dropdown.get_selected_item()
                if selected is None:
                    continue
                source = item.id
                name, ext = self.util.filename_details(source)
                n = Field[item_type]
                tmpfile = name.split('-')
                tmpfile[n] = selected.id
                filename = f"{'-'.join(tmpfile)}.{ext}"
                target = os.path.join(os.path.dirname(source), filename)
                citems.append(File(id=os.path.basename(source),
                                   title=self.util.filename_upper(os.path.basename(target))))
            columnview.update(citems)

        def dialog_response(dialog, response, dropdown, item_type, items, cfg_handler_id):
            try:
                self.config[item_type.__gtype_name__].disconnect(cfg_handler_id)
            except Exception:
                pass
            if response != 'apply':
                return
            selected = dropdown.get_selected_item()
            if selected is None:
                return
            # No BUSY toggling: the workspace skips updates while BUSY, and a
            # mid-loop error would strand it there. Each filename_rename emits
            # the debounced 'filename-renamed'. Skip bad files, do not abort.
            n = Field[item_type]
            for item in items:
                bsource = item.id
                name, ext = self.util.filename_details(bsource)
                tmpfile = name.split('-')
                if n >= len(tmpfile):
                    self.log.warning(f"Skipping '{bsource}': not enough fields")
                    continue
                tmpfile[n] = selected.id
                btarget = f"{'-'.join(tmpfile)}.{ext}"
                source = os.path.join(self.repository.docs, bsource)
                target = os.path.join(self.repository.docs, btarget)
                self.util.filename_rename(source, target)

        i_type = item_type.__gtype_name__
        i_title = item_type.__title__
        i_title_plural = item_type.__title_plural__
        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label(
            _('Rename {count} files by setting the field <b>{field}</b> to:\n')
            .format(count=len(items), field=i_title))
        dropdown = self.factory.create_dropdown_generic(item_type)
        icon_name = f'io.github.t00m.MiAZ-res-{i_title_plural.lower()}'
        btnManage = self.factory.create_button(icon_name=icon_name, title='')
        btnManage.connect('clicked', self.actions.manage_resource,
                          Configview[i_type])
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        dropdown.connect("notify::selected-item", update_columnview, cv, item_type, items)
        cfg_handler_id = self.config[i_type].connect('used-updated', self.actions.dropdown_repopulate, dropdown, item_type, False)
        self.actions.dropdown_populate(self.config[i_type], dropdown, item_type, any_value=False)
        frame.set_child(cv)
        box.append(label)
        hbox = self.factory.create_box_horizontal()
        hbox.append(dropdown)
        hbox.append(btnManage)
        box.append(hbox)
        box.append(frame)
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_action(title=_('Mass renaming'), widget=box, width=1024, height=600)
        dialog.connect('response', dialog_response, dropdown, item_type, items, cfg_handler_id)
        dialog.present(window)

    def rename_date(self, action, data, item_type):
        """Set the date field (field 0) across the selection via a calendar."""
        items = self._selection()
        if items is None:
            return

        # Per-file detected dates, cached so the preview does not re-read files.
        detected = {}

        def detected_for(item):
            if item.id in detected:
                return detected[item.id]
            bsource = os.path.basename(item.id)
            name, _ext = self.util.filename_details(bsource)
            fields = name.split('-')
            concept_hint = fields[5] if len(fields) == 7 else ''
            abspath = os.path.join(self.repository.docs, bsource)
            guess = self.util.filename_guess_date(abspath, concept_hint=concept_hint)
            detected[item.id] = guess
            return guess

        def current_sdate():
            # Falls back to today while the user is halfway through typing.
            sdate = date_widget.get_text()
            return sdate if date_is_valid(sdate) else datetime.now().strftime('%Y%m%d')

        def date_for(item, sdate):
            # Per-file detection (like single rename) when the box is checked;
            # otherwise the single calendar date for every file.
            return detected_for(item) if chk_detect.get_active() else sdate

        def refresh_preview(*_a):
            sdate = current_sdate()
            citems = []
            read = 0
            for item in items:
                source = os.path.basename(item.id)
                name, ext = self.util.filename_details(source)
                lname = name.split('-')
                lname[0] = date_for(item, sdate)
                if lname[0] != UNKNOWN_DATE:
                    read += 1
                target = f"{'-'.join(lname)}.{ext}"
                citems.append(File(id=source, title=self.util.filename_upper(target)))
            if chk_detect.get_active():
                # Say how many dates were really read. The count is what tells a
                # working detection from one that found nothing and wrote the
                # unknown date everywhere.
                label.set_text(
                    _('Date read from {read} of {total} files, the rest set to {unknown}')
                    .format(read=read, total=len(items), unknown=UNKNOWN_DATE))
            else:
                label.set_text(datetime.strptime(sdate, '%Y%m%d').strftime('%A, %B %d %Y'))
            cv.update(citems)

        def dialog_response_date(dialog, response):
            if response != 'apply':
                return
            sdate = current_sdate()
            for item in items:
                bsource = os.path.basename(item.id)
                name, ext = self.util.filename_details(bsource)
                lname = name.split('-')
                if not lname:
                    continue
                lname[0] = date_for(item, sdate)
                btarget = f"{'-'.join(lname)}.{ext}"
                source = os.path.join(self.repository.docs, bsource)
                target = os.path.join(self.repository.docs, btarget)
                self.util.filename_rename(source, target)

        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        chk_detect = Gtk.CheckButton(label=_('Detect date from each file'))
        chk_detect.set_active(True)
        hbox = self.factory.create_box_horizontal()
        label = Gtk.Label()
        date_widget = MiAZDateEntry(self.app, show_label=False)
        date_widget.set_text(datetime.now().strftime('%Y%m%d'), validate=True)
        date_widget.set_sensitive(False)
        hbox.append(date_widget)
        hbox.append(label)
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        frame.set_child(cv)
        box.append(chk_detect)
        box.append(hbox)
        box.append(frame)
        date_widget.connect('date-changed', refresh_preview)

        def on_toggle(*_a):
            date_widget.set_sensitive(not chk_detect.get_active())
            refresh_preview()

        chk_detect.connect('toggled', on_toggle)
        refresh_preview()
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_action(title=_('Mass renaming'), widget=box, width=640, height=480)
        dialog.connect('response', dialog_response_date)
        dialog.present(window)

    def rename_concept(self, action, data, item_type):
        """Transform the free-form concept field of the selected documents."""
        items = self._selection()
        if items is None:
            return

        n = Field[Concept]
        op_keys = ['keep', 'remove', 'prefix', 'suffix', 'replace', 'case', 'set']
        op_labels = [_('Keep token(s)'), _('Remove token(s)'), _('Add prefix'),
                     _('Add suffix'), _('Find & replace'), _('Change case'),
                     _('Set value')]
        case_modes = ['upper', 'lower', 'title']

        entry_sep = Gtk.Entry(text='_')
        entry_positions = Gtk.Entry()
        entry_positions.set_placeholder_text(_('e.g. 2-3'))
        entry_text = Gtk.Entry()
        entry_find = Gtk.Entry()
        entry_find.set_placeholder_text(_('find'))
        entry_replace = Gtk.Entry()
        entry_replace.set_placeholder_text(_('replace with'))
        entry_value = Gtk.Entry()
        dd_case = Gtk.DropDown.new_from_strings([_('upper'), _('lower'), _('title')])
        dd_op = Gtk.DropDown.new_from_strings(op_labels)

        def labeled(text, widget):
            hbox = self.factory.create_box_horizontal(spacing=6)
            hbox.append(Gtk.Label(label=text))
            hbox.append(widget)
            return hbox

        box_positions = labeled(_('Positions'), entry_positions)
        box_sep = labeled(_('Separator'), entry_sep)
        box_text = labeled(_('Text'), entry_text)
        box_find = labeled(_('Find'), entry_find)
        box_replace = labeled(_('Replace'), entry_replace)
        box_case = labeled(_('Case'), dd_case)
        box_value = labeled(_('Value'), entry_value)

        def current_op():
            return op_keys[dd_op.get_selected()]

        def current_params():
            return {
                'sep': entry_sep.get_text() or '_',
                'positions': entry_positions.get_text(),
                'text': entry_text.get_text(),
                'find': entry_find.get_text(),
                'replace': entry_replace.get_text(),
                'mode': case_modes[dd_case.get_selected()],
                'value': entry_value.get_text(),
            }

        def target_basename(bsource, op, params):
            name, ext = self.util.filename_details(bsource)
            fields = name.split('-')
            if len(fields) != 7:
                return None
            old_concept = fields[n]
            new_concept = self.util.valid_key(apply_concept_op(op, old_concept, params))
            if not new_concept:
                return None

            if new_concept == old_concept:
                return bsource
            fields[n] = new_concept
            return f"{'-'.join(fields)}.{ext}"

        def update_visibility(*_a):
            op = current_op()
            box_positions.set_visible(op in ('keep', 'remove'))
            box_sep.set_visible(op in ('keep', 'remove', 'prefix', 'suffix'))
            box_text.set_visible(op in ('prefix', 'suffix'))
            box_find.set_visible(op == 'replace')
            box_replace.set_visible(op == 'replace')
            box_case.set_visible(op == 'case')
            box_value.set_visible(op == 'set')

        def refresh_preview(*_a):
            op = current_op()
            params = current_params()
            citems = []
            for item in items:
                bsource = item.id
                btarget = target_basename(bsource, op, params)
                title = self.util.filename_upper(btarget) if btarget is not None else bsource
                citems.append(File(id=bsource, title=title))
            cv.update(citems)

        def dialog_response_concept(dialog, response):
            if response != 'apply':
                return
            op = current_op()
            params = current_params()
            renamed = 0
            skipped = 0
            for item in items:
                bsource = item.id
                btarget = target_basename(bsource, op, params)
                if btarget is None or btarget == bsource:
                    skipped += 1
                    continue
                source = os.path.join(self.repository.docs, bsource)
                target = os.path.join(self.repository.docs, btarget)
                if self.util.filename_rename(source, target):
                    renamed += 1
                else:
                    skipped += 1
            self.srvdlg.show_toast(
                _('Renamed {r}, skipped {s}').format(r=renamed, s=skipped))

        box = self.factory.create_box_vertical(spacing=6, vexpand=True, hexpand=True)
        label = self.factory.create_label(
            _('Transform the <b>concept</b> of {count} files:\n')
            .format(count=len(items)))
        params_box = self.factory.create_box_horizontal(spacing=12)
        for child in (box_positions, box_sep, box_text, box_find,
                      box_replace, box_case, box_value):
            params_box.append(child)
        frame = Gtk.Frame()
        cv = MiAZColumnViewMassRename(self.app)
        cv.set_hexpand(True)
        cv.set_vexpand(True)
        frame.set_child(cv)
        box.append(label)
        box.append(dd_op)
        box.append(params_box)
        box.append(frame)

        dd_op.connect('notify::selected', update_visibility)
        dd_op.connect('notify::selected', refresh_preview)
        dd_case.connect('notify::selected', refresh_preview)
        for entry in (entry_sep, entry_positions, entry_text, entry_find,
                      entry_replace, entry_value):
            entry.connect('changed', refresh_preview)

        update_visibility()
        refresh_preview()
        window = self.app.get_widget('window')
        dialog = self.srvdlg.show_action(
            title=_('Mass renaming: concept'), widget=box, width=1024, height=600)
        dialog.connect('response', dialog_response_concept)
        dialog.present(window)
