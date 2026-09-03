# File: dateentry.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Keyboard-first YYYYMMDD entry with verdict label and calendar popover

from datetime import datetime
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend.util import date_is_valid, UNKNOWN_DATE
from MiAZ.frontend.desktop.services.factory import calendar_select_date


class MiAZDateEntry(Gtk.Box):
    """One widget for the date field: entry, human-readable label, calendar."""
    __gtype_name__ = 'MiAZDateEntry'
    __gsignals__ = {
        'date-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'date-validated': (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    def __init__(self, app, show_label=True):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.app = app
        # Set while validate() moves the calendar, so the calendar's answer
        # is not written back into the entry.
        self._moving_calendar = False
        self.label = Gtk.Label()
        self.label.add_css_class('caption')
        self.label.set_visible(show_label)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_max_length(8)
        self.entry.set_max_width_chars(12)
        self.entry.set_width_chars(12)
        self.entry.set_placeholder_text(_('YYYYmmdd'))
        self.entry.set_alignment(1.0)
        self.calendar = Gtk.Calendar()
        self.calendar.connect('day-selected', self._on_calendar_day_selected)
        factory = self.app.get_service('factory')
        button_content = factory.create_button_content(icon_name='io.github.t00m.MiAZ-res-date')
        self.button = Gtk.MenuButton(child=button_content)
        popover = Gtk.Popover()
        popover.set_child(self.calendar)
        self.button.set_popover(popover)
        self.append(self.label)
        self.append(self.entry)
        self.append(self.button)
        self.entry.connect('changed', lambda *_a: self.emit('date-changed'))
        # The date is judged when the user is done with the field, not while
        # they are still filling it in.
        focus = Gtk.EventControllerFocus()
        focus.connect('leave', lambda *_a: self.validate())
        self.entry.add_controller(focus)

    def get_text(self) -> str:
        return self.entry.get_text()

    def set_text(self, sdate: str, validate: bool = False):
        self.entry.set_text(sdate)
        if validate:
            self.validate()

    def is_valid(self) -> bool:
        return date_is_valid(self.entry.get_text())

    def validate(self) -> bool:
        """Show the verdict: move the calendar, set the label, emit the result."""
        sdate = self.entry.get_text()
        valid = date_is_valid(sdate)
        if valid:
            adate = datetime.strptime(sdate, '%Y%m%d')
            self._move_calendar_to(adate)
            if sdate == UNKNOWN_DATE:
                self.label.set_markup(f"<i>{_('date not known')}</i>")
            else:
                self.label.set_markup(adate.strftime("%A, %B %d %Y"))
        else:
            self.label.set_markup(f"<i>{_('not a date')}</i>")
        self.emit('date-validated', valid)
        return valid

    def _move_calendar_to(self, adate):
        self._moving_calendar = True
        try:
            calendar_select_date(self.calendar, adate.year, adate.month, adate.day)
        finally:
            self._moving_calendar = False

    def _on_calendar_day_selected(self, calendar):
        if self._moving_calendar:
            return
        adate = calendar.get_date()
        y = f"{adate.get_year():04d}"
        m = f"{adate.get_month():02d}"
        d = f"{adate.get_day_of_month():02d}"
        self.entry.set_text(f"{y}{m}{d}")
        self.validate()
