#!/usr/bin/env python3

# Load Gtk
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject, Gdk

import re
from uuid import UUID, uuid4
from typing import Any, Optional

# --------------------------------------------------------------------------------
# GTG NOTES
# --------------------------------------------------------------------------------

# Sorting
#
# We have to use a Gtk.SortListModel
# which takes a Gtk.Sorter object
# https://docs.gtk.org/gtk4/class.Sorter.html
# subclass that and override the compare() function
#
# Looks like we'll need a sorter class for each
# type of sorting we want to do. We should probably
# add a prop in that class to handle asc/desc order


# Filtering
#
# https://docs.gtk.org/gtk4/class.FilterListModel.html
#
# We need to use a Gtk.FilterListModel which takes a
# Gtk.Filter object, much like the sorter
# We should sublcass and override the match() method
#
# One filter for each type of filtering, and then set
# different filters on the filter list model


# We should expose sorters and filters to the plugin
# API in some way. Maybe have them in their own modules

# Search needs to be re-implemented using a filter
# list model too

# Models could be added as props to the Store classes,
# no need to subclass them and possibly run into conflicts
# and weird stuff

# Data classes need to use GObject properties
# instead of regular python props

# Need to set a source as a controller for the rows widgets
# Need to set a drop as a controller for the listview itself
# Then Connect the signals

# https://docs.gtk.org/gtk4/drag-and-drop.html
# https://gitlab.gnome.org/GNOME/gtk/-/blob/master/demos/gtk-demo/dnd.c


# --------------------------------------------------------------------------------
# GTG
# --------------------------------------------------------------------------------

# Lots of copy-pasta from GTG's core

import calendar
import locale
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from gettext import gettext as _
from gettext import ngettext

__all__ = ['Date', 'Accuracy']

# trick to obtain the timezone of the machine GTG is executed on
LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
NOW, SOON, SOMEDAY, NODATE = list(range(4))

# Localized strings for fuzzy values
STRINGS = {
    # Translators: Used for display
    NOW: _('now'),
    # Translators: Used for display
    SOON: _('soon'),
    # Translators: Used for display
    SOMEDAY: _('someday'),
    NODATE: '',
}

# Allows looking up any value which is not a date but points towards one and
# find one of the four constant for fuzzy dates: SOON, SOMEDAY, and NODATE
LOOKUP = {
    NOW: NOW,
    'now': NOW,
    # Translators: Used in parsing, made lowercased in code
    _('now'): NOW,
    SOON: SOON,
    'soon': SOON,
    # Translators: Used in parsing, made lowercased in code
    _('soon').lower(): SOON,
    SOMEDAY: SOMEDAY,
    'later': SOMEDAY,
    # Translators: Used in parsing, made lowercased in code
    _('later').lower(): SOMEDAY,
    'someday': SOMEDAY,
    # Translators: Used in parsing, made lowercased in code
    _('someday').lower(): SOMEDAY,
    NODATE: NODATE,
    '': NODATE,
    None: NODATE,
    'none': NODATE,
}


class Accuracy(Enum):
    """ GTG.core.dates.Date supported accuracies

    From less accurate to the most:
     * fuzzy is when a date is just a string not representing a real date
       (like `someday`)
     * date is a datetime.date accurate to the day (see datetime.date)
     * datetime is a datetime.datetime accurate to the microseconds
       (see datetime.datetime)
     * timezone ia a datetime.datetime accurate to the microseconds with tzinfo
    """
    fuzzy = 'fuzzy'
    date = 'date'
    datetime = 'datetime'
    timezone = 'timezone'


# ISO 8601 date format
# get date format from locale
DATE_FORMATS = [(locale.nl_langinfo(locale.D_T_FMT), Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S.%f%z', Accuracy.timezone),
                ('%Y-%m-%d %H:%M%S.%f%z', Accuracy.timezone),
                ('%Y-%m-%dT%H:%M%S.%f', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S.%f', Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S', Accuracy.datetime),
                (locale.nl_langinfo(locale.D_FMT), Accuracy.date),
                ('%Y-%m-%d', Accuracy.date)]


class Date:
    """A date class that supports fuzzy dates.

    A Date can be constructed with:
      - the fuzzy strings 'now', 'soon', '' (no date, default), or 'someday'
      - a string containing an ISO format date: YYYY-MM-DD
      - a datetime.date instance
      - a datetime.datetime instance
      - a GTG.core.dates.Date instance
      - a string containing a locale format date.
    """

    __slots__ = ['dt_value']

    def __init__(self, value=None):
        self.dt_value = None
        if isinstance(value, (date, datetime)):
            self.dt_value = value
        elif isinstance(value, Date):
            # Copy internal values from other Date object
            self.dt_value = value.dt_value
        elif value in {'None', None, ''}:
            self.dt_value = NODATE
        elif isinstance(value, str):
            self.dt_value = self.__parse_dt_str(value)
        elif value == 0:  # support for dropped falsly fuzzy NOW
            self.dt_value = datetime.now()
        elif value in LOOKUP:
            self.dt_value = LOOKUP[value]
        if self.dt_value is None:
            raise ValueError(f"Unknown value for date: '{value}'")

    @staticmethod
    def __parse_dt_str(string):
        """Will try casting given string into a datetime or a date."""
        for cls in date, datetime:
            try:
                return cls.fromisoformat(string)
            except (ValueError,  # ignoring no iso format value
                    AttributeError):  # ignoring python < 3.7
                pass
        for date_format, accuracy in DATE_FORMATS:
            try:
                dt_value = datetime.strptime(string, date_format)
                if accuracy is Accuracy.date:
                    dt_value = dt_value.date()
                return dt_value
            except ValueError:
                pass
        if string in {'now', _('now').lower()}:
            return datetime.now()
        return LOOKUP.get(str(string).lower(), None)

    @property
    def accuracy(self):
        if isinstance(self.dt_value, datetime):
            if self.dt_value.tzinfo:
                return Accuracy.timezone
            return Accuracy.datetime
        if isinstance(self.dt_value, date):
            return Accuracy.date
        return Accuracy.fuzzy

    def date(self):
        """ Map date into real date, i.e. convert fuzzy dates """
        return self.dt_by_accuracy(Accuracy.date)

    @staticmethod
    def _dt_by_accuracy(dt_value, accuracy: Accuracy,
                        wanted_accuracy: Accuracy):
        if wanted_accuracy is Accuracy.timezone:
            if accuracy is Accuracy.date:
                return datetime(dt_value.year, dt_value.month, dt_value.day,
                                tzinfo=LOCAL_TIMEZONE)
            assert accuracy is Accuracy.datetime, f"{accuracy} wasn't expected"
            # datetime is naive and assuming local timezone
            return dt_value.replace(tzinfo=LOCAL_TIMEZONE)
        if wanted_accuracy is Accuracy.datetime:
            if accuracy is Accuracy.date:
                return datetime(dt_value.year, dt_value.month, dt_value.day)
            assert accuracy is Accuracy.timezone, f"{accuracy} wasn't expected"
            # returning UTC naive
            return dt_value.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)
        if wanted_accuracy is Accuracy.date:
            return dt_value.date()
        raise AssertionError(f"Couldn't process {dt_value!r} with actual "
                             f"accuracy is {accuracy.value} "
                             f"and we wanted {wanted_accuracy.value}")

    def dt_by_accuracy(self, wanted_accuracy: Accuracy):
        """Cast Date to the desired accuracy and returns either string
        for fuzzy, date, datetime or datetime with tzinfo.
        """
        if wanted_accuracy == self.accuracy:
            return self.dt_value
        if self.accuracy is Accuracy.fuzzy:
            now = datetime.now()
            delta_days = {SOON: 15, SOMEDAY: 365, NODATE: 9999}
            gtg_date = Date(now + timedelta(delta_days[self.dt_value]))
            if gtg_date.accuracy is wanted_accuracy:
                return gtg_date.dt_value
            return self._dt_by_accuracy(gtg_date.dt_value, gtg_date.accuracy,
                                        wanted_accuracy)
        return self._dt_by_accuracy(self.dt_value, self.accuracy,
                                    wanted_accuracy)

    def _cast_for_operation(self, other, is_comparison: bool = True):
        """Returns two values compatibles for operation or comparison.
        Will settle for the less accuracy: comparing a date and a datetime
        will cast the datetime to a date to allow comparison.
        """
        if isinstance(other, timedelta):
            if is_comparison:
                raise ValueError("can't compare with %r" % other)
            return self.dt_value, other
        if not isinstance(other, self.__class__):
            other = self.__class__(other)
        if self.accuracy is other.accuracy:
            return self.dt_value, other.dt_value
        for accuracy in Accuracy.date, Accuracy.datetime, Accuracy.timezone:
            if accuracy in {self.accuracy, other.accuracy}:
                return (self.dt_by_accuracy(accuracy),
                        other.dt_by_accuracy(accuracy))
        return (self.dt_by_accuracy(Accuracy.fuzzy),
                other.dt_by_accuracy(Accuracy.fuzzy))

    def __add__(self, other):
        a, b = self._cast_for_operation(other, is_comparison=False)
        return a + b

    def __sub__(self, other):
        a, b = self._cast_for_operation(other, is_comparison=False)
        return a - b

    __radd__ = __add__
    __rsub__ = __sub__

    def __lt__(self, other):
        a, b = self._cast_for_operation(other)
        return a < b

    def __le__(self, other):
        a, b = self._cast_for_operation(other)
        return a <= b

    def __eq__(self, other):
        a, b = self._cast_for_operation(other)
        return a == b

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        a, b = self._cast_for_operation(other)
        return a > b

    def __ge__(self, other):
        a, b = self._cast_for_operation(other)
        return a >= b

    def __str__(self):
        """ String representation - fuzzy dates are in English """
        if self.accuracy is Accuracy.fuzzy:
            strs = {SOON: 'soon', SOMEDAY: 'someday', NODATE: ''}
            return strs[self.dt_value]
        return self.dt_value.isoformat()

    @property
    def localized_str(self):
        """Will return displayable and localized string representation
        of the GTG.core.dates.Date.
        """
        if self.accuracy is Accuracy.fuzzy:
            return STRINGS[self.dt_value]
        if self.accuracy is Accuracy.datetime:
            span = timedelta(hours=1)
            now = datetime.now()
            if now - span <= self.dt_value < now + span:
                return _('now')
        return self.date().strftime(locale.nl_langinfo(locale.D_FMT))

    def __repr__(self):
        return f"<Date({self})>"

    def __bool__(self):
        return self.dt_value != NODATE

    def is_fuzzy(self):
        """
        True if the Date is one of the fuzzy values:
        now, soon, someday or no_date
        """
        return self.accuracy is Accuracy.fuzzy

    def days_left(self):
        """ Return the difference between the date and today in dates """
        if self.dt_value == NODATE:
            return None
        return (self.dt_by_accuracy(Accuracy.date) - date.today()).days

    @classmethod
    def today(cls):
        """ Return date for today """
        return cls(date.today())

    @classmethod
    def tomorrow(cls):
        """ Return date for tomorrow """
        return cls(date.today() + timedelta(days=1))

    @classmethod
    def now(cls):
        """ Return date representing fuzzy date now """
        return cls.today()

    @staticmethod
    def no_date():
        """ Return date representing no (set) date """
        return _GLOBAL_DATE_NODATE

    @staticmethod
    def soon():
        """ Return date representing fuzzy date soon """
        return _GLOBAL_DATE_SOON

    @staticmethod
    def someday():
        """ Return date representing fuzzy date someday """
        return _GLOBAL_DATE_SOMEDAY

    @staticmethod
    def _parse_only_month_day(string):
        """ Parse next Xth day in month """
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        today = date.today()
        try:
            result = today.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= today:
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year

            try:
                result = date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    @staticmethod
    def _parse_numerical_format(string):
        """ Parse numerical formats like %Y/%m/%d, %Y%m%d or %m%d """
        result = None
        today = date.today()
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                result = datetime.strptime(string, fmt).date()
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if result.month > today.month or \
                            (result.month == today.month and result.day >= today.day):
                        year = today.year
                    else:
                        year = today.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    @staticmethod
    def _parse_text_representation(string):
        """ Match common text representation for date """
        today = date.today()

        # accepted date formats
        formats = {
            'today': 0,
            # Translators: Used in parsing, made lowercased in code
            _('today').lower(): 0,
            'tomorrow': 1,
            # Translators: Used in parsing, made lowercased in code
            _('tomorrow').lower(): 1,
            'next week': 7,
            # Translators: Used in parsing, made lowercased in code
            _('next week').lower(): 7,
            'next month': calendar.mdays[today.month],
            # Translators: Used in parsing, made lowercased in code
            _('next month').lower(): calendar.mdays[today.month],
            'next year': 365 + int(calendar.isleap(today.year)),
            # Translators: Used in parsing, made lowercased in code
            _('next year').lower(): 365 + int(calendar.isleap(today.year)),
        }

        # add week day names in the current locale
        for i, (english, local) in enumerate([
            ("Monday", _("Monday")),
            ("Tuesday", _("Tuesday")),
            ("Wednesday", _("Wednesday")),
            ("Thursday", _("Thursday")),
            ("Friday", _("Friday")),
            ("Saturday", _("Saturday")),
            ("Sunday", _("Sunday")),
        ]):
            offset = i - today.weekday() + 7 * int(i <= today.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        offset = formats.get(string, None)
        if offset is None:
            return None
        return today + timedelta(offset)

    @classmethod
    def parse(cls, string):
        """Return a Date corresponding to string, or None.

        string may be in one of the following formats:
            - YYYY/MM/DD, YYYYMMDD, MMDD, D
            - fuzzy dates
            - 'today', 'tomorrow', 'next week', 'next month' or 'next year' in
                English or the system locale.
        """
        # sanitize input
        if string is None:
            string = ''
        else:
            string = string.lower()

        # try the default formats
        try:
            return cls(string)
        except ValueError:
            pass

        # do several parsing
        result = cls._parse_only_month_day(string)
        if result is None:
            result = cls._parse_numerical_format(string)
        if result is None:
            result = cls._parse_text_representation(string)

        # Announce the result
        if result is not None:
            return cls(result)
        else:
            raise ValueError(f"Can't parse date '{string}'")

    def _parse_only_month_day_for_recurrency(self, string, newtask=True):
        """ Parse next Xth day in month from a certain date"""
        self_date = self.dt_by_accuracy(Accuracy.date)
        if not newtask:
            self_date += timedelta(1)
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        try:
            result = self_date.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= self_date:
            if self_date.month == 12:
                next_month = 1
                next_year = self_date.year + 1
            else:
                next_month = self_date.month + 1
                next_year = self_date.year

            try:
                result = date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    def _parse_numerical_format_for_recurrency(self, string, newtask=True):
        """ Parse numerical formats like %Y/%m/%d,
        %Y%m%d or %m%d and calculated from a certain date"""
        self_date = self.dt_by_accuracy(Accuracy.date)
        result = None
        if not newtask:
            self_date += timedelta(1)
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                result = datetime.strptime(string, fmt).date()
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if (result.month > self_date.month or
                            (result.month == self_date.month and
                             result.day >= self_date.day)):
                        year = self_date.year
                    else:
                        year = self_date.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    def _parse_text_representation_for_recurrency(self, string, newtask=False):
        """Match common text representation from a certain date(self)

        Args:
            string (str): text representation.
            newtask (bool, optional): depending on the task if it is new, the offset changes
        """
        # accepted date formats
        self_date = self.dt_by_accuracy(Accuracy.date)
        formats = {
            # change the offset depending on the task.
            'day': 0 if newtask else 1,
            # Translators: Used in recurring parsing, made lowercased in code
            _('day').lower(): 0 if newtask else 1,
            'other-day': 0 if newtask else 2,
            # Translators: Used in recurring parsing, made lowercased in code
            _('other-day').lower(): 0 if newtask else 2,
            'week': 0 if newtask else 7,
            # Translators: Used in recurring parsing, made lowercased in code
            _('week').lower(): 0 if newtask else 7,
            'month': 0 if newtask else calendar.mdays[self_date.month],
            # Translators: Used in recurring parsing, made lowercased in code
            _('month').lower(): 0 if newtask else calendar.mdays[self_date.month],
            'year': 0 if newtask else 365 + int(calendar.isleap(self_date.year)),
            # Translators: Used in recurring parsing, made lowercased in code
            _('year').lower(): 0 if newtask else 365 + int(calendar.isleap(self_date.year)),
        }

        # add week day names in the current locale
        for i, (english, local) in enumerate([
            ("Monday", _("Monday")),
            ("Tuesday", _("Tuesday")),
            ("Wednesday", _("Wednesday")),
            ("Thursday", _("Thursday")),
            ("Friday", _("Friday")),
            ("Saturday", _("Saturday")),
            ("Sunday", _("Sunday")),
        ]):
            offset = i - self_date.weekday() + 7 * int(i <= self_date.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        offset = formats.get(string, None)
        if offset is None:
            return None
        else:
            return self_date + timedelta(offset)

    def parse_from_date(self, string, newtask=False):
        """parse_from_date returns the date from a string
        but counts since a given date"""
        if string is None:
            string = ''
        else:
            string = string.lower()

        try:
            return Date(string)
        except ValueError:
            pass

        result = self._parse_only_month_day_for_recurrency(string, newtask)
        if result is None:
            result = self._parse_numerical_format_for_recurrency(string, newtask)
        if result is None:
            result = self._parse_text_representation_for_recurrency(string, newtask)

        if result is not None:
            return Date(result)
        else:
            raise ValueError(f"Can't parse date '{string}'")

    def to_readable_string(self):
        """ Return nice representation of date.

        Fuzzy dates => localized version
        Close dates => Today, Tomorrow, In X days
        Other => with locale dateformat, stripping year for this year
        """
        if self.accuracy is Accuracy.fuzzy:
            return STRINGS[self.dt_value]

        days_left = self.days_left()
        if days_left == 0:
            return _('Today')
        elif days_left < 0:
            abs_days = abs(days_left)
            return ngettext('Yesterday', '%(days)d days ago', abs_days) % \
                   {'days': abs_days}
        elif days_left > 0 and days_left <= 15:
            return ngettext('Tomorrow', 'In %(days)d days', days_left) % \
                   {'days': days_left}
        else:
            locale_format = locale.nl_langinfo(locale.D_FMT)
            if calendar.isleap(date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(days_left) / year_len < 1.0:
                # if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y', '')
                locale_format = locale_format.replace('.%Y', '.')
            return self.dt_by_accuracy(Accuracy.date).strftime(locale_format)


_GLOBAL_DATE_SOON = Date(SOON)
_GLOBAL_DATE_NODATE = Date(NODATE)
_GLOBAL_DATE_SOMEDAY = Date(SOMEDAY)


class Status(Enum):
    """Status for a task."""

    ACTIVE = 'Active'
    DONE = 'Done'
    DISMISSED = 'Dismissed'


class Filter(Enum):
    """Types of filters."""

    ACTIVE = 'Active'
    ACTIONABLE = 'Actionable'
    CLOSED = 'Closed'
    STATUS = 'Status'
    TAG = 'Tag'
    PARENT = 'Parent'
    CHILDREN = 'Children'


class Tag2(GObject.Object):
    """A tag that can be applied to a Task."""

    __gtype_name__ = 'gtg_Tag'

    # __slots__ = ['id', 'name', 'icon', 'color', 'actionable', 'children']

    def __init__(self, id: UUID, name: str) -> None:
        self.id = id
        self._name = name

        self._icon = None
        self._color = None
        self.actionable = True
        self.children = []
        self.parent = None

        super(Tag2, self).__init__()

    @GObject.Property(type=str)
    def name(self) -> str:
        """Read only property."""

        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @GObject.Property(type=str)
    def icon(self) -> str:
        """Read only property."""

        return self._icon

    @GObject.Property(type=str)
    def color(self) -> str:
        """Read only property."""

        return self._color

    def __str__(self) -> str:
        """String representation."""

        return f'Tag: {self.name} ({self.id})'

    def __repr__(self) -> str:
        """String representation."""

        return (f'Tag "{self.name}" with id "{self.id}"')

    def __eq__(self, other) -> bool:
        """Equivalence."""

        return self.id == other.id


TAG_REGEX = re.compile(r'^\B\@\w+(\-\w+)*\,+')
SUB_REGEX = re.compile(r'\{\!.+\!\}')


class Task2(GObject.Object):
    """A single task."""

    __gtype_name__ = 'gtg_Task'

    # __slots__ = ['id', 'raw_title', 'content', 'tags',
    #              'children', 'status', 'parent', '_date_added',
    #              '_date_due', '_date_start', '_date_closed',
    #              '_date_modified']

    def __init__(self, id: UUID, title: str) -> None:
        self.id = id
        self.raw_title = title.strip('\t\n')
        self.content = ''
        self.tags = []
        self.children = []
        self.status = Status.ACTIVE
        self.parent = None

        self._date_added = Date.no_date()
        self._date_due = Date.no_date()
        self._date_start = Date.no_date()
        self._date_closed = Date.no_date()
        self._date_modified = Date(datetime.now())

        super(Task2, self).__init__()

    def is_actionable(self) -> bool:
        """Determine if this task is actionable."""

        actionable_tags = all(t.actionable for t in self.tags)
        active_children = all(t.status != Status.ACTIVE for t in self.children)
        days_left = self._date_start.days_left()
        can_start = True if not days_left else days_left <= 0

        return (self.status == Status.ACTIVE
                and self._date_due != Date.someday()
                and actionable_tags
                and active_children
                and can_start)

    def toggle_status(self, propagate: bool = True) -> None:
        """Toggle between possible statuses."""

        if self.status is Status.ACTIVE:
            self.status = Status.DONE
            self.date_closed = Date.today()

        else:
            self.status = Status.ACTIVE
            self.date_closed = Date.no_date()

            if self.parent and self.parent.status is not Status.ACTIVE:
                self.parent.toggle_status(propagate=False)

        if propagate:
            for child in self.children:
                child.toggle_status()

    def dismiss(self) -> None:
        """Set this task to be dismissed."""

        self.set_status(Status.DISMISSED)

    def set_status(self, status: Status) -> None:
        """Set status for task."""

        self.status = status

        for child in self.children:
            child.set_status(status)

    @property
    def date_due(self) -> Date:
        return self._date_due

    @date_due.setter
    def date_due(self, value: Date) -> None:
        self._date_due = value

        if not value or value.is_fuzzy():
            return

        for child in self.children:
            if (child.date_due
                    and not child.date_due.is_fuzzy()
                    and child.date_due > value):
                child.date_due = value

        if (self.parent
                and self.parent.date_due
                and self.parent.date_due.is_fuzzy()
                and self.parent.date_due < value):
            self.parent.date_due = value

    @property
    def date_added(self) -> Date:
        return self._date_added

    @date_added.setter
    def date_added(self, value: Any) -> None:
        self._date_added = Date(value)

    @property
    def date_start(self) -> Date:
        return self._date_start

    @date_start.setter
    def date_start(self, value: Any) -> None:
        self._date_start = Date(value)

    @property
    def date_closed(self) -> Date:
        return self._date_closed

    @date_closed.setter
    def date_closed(self, value: Any) -> None:
        self._date_closed = Date(value)

    @property
    def date_modified(self) -> Date:
        return self._date_modified

    @date_modified.setter
    def date_modified(self, value: Any) -> None:
        self._date_modified = Date(value)

    @GObject.Property(type=str)
    def title(self) -> str:
        return self.raw_title

    @title.setter
    def title(self, value) -> None:
        self.raw_title = value.strip('\t\n') or _('(no title)')

    @GObject.Property(type=str)
    def excerpt(self) -> str:
        if not self.content:
            return ''

        # Strip tags
        txt = TAG_REGEX.sub('', self.content)

        # Strip subtasks
        txt = SUB_REGEX.sub('', txt)

        # Strip blank lines and set within char limit
        return f'{txt.strip()[:80]}…'

    def add_tag(self, tag: Tag2) -> None:
        """Add a tag to this task."""

        if isinstance(tag, Tag2):
            if tag not in self.tags:
                self.tags.append(tag)
        else:
            raise ValueError

    def remove_tag(self, tag_name: str) -> None:
        """Remove a tag from this task."""

        for t in self.tags:
            if t.name == tag_name:
                self.tags.remove(t)
                (self.content.replace(f'{tag_name}\n\n', '')
                 .replace(f'{tag_name},', '')
                 .replace(f'{tag_name}', ''))

    @property
    def days_left(self) -> Optional[Date]:
        return self.date_due.days_left()

    def update_modified(self) -> None:
        """Update the modified property."""

        self.modified = Date(datetime.now())

    def __str__(self) -> str:
        """String representation."""

        return f'Task: {self.title} ({self.id})'

    def __repr__(self) -> str:
        """String representation."""

        tags = ', '.join([t.name for t in self.tags])
        return (f'Task "{self.title}" with id "{self.id}".'
                f'Status: {self.status}, tags: {tags}')

    def __eq__(self, other) -> bool:
        """Equivalence."""

        return self.id == other.id

    def __hash__(self) -> int:
        """Hash (used for dicts and sets)."""

        return hash(self.id)


# --------------------------------------------------------------------------------
# SORTING AND FILTERING
# --------------------------------------------------------------------------------


class MySorter(Gtk.Sorter):
    __gtype_name__ = 'MySorter'

    def __init__(self):
        print('Sorter started')
        super(MySorter, self).__init__()

    # To override virtual methods we have to name
    # them do_XXX.
    def do_compare(self, a, b) -> Gtk.Ordering:

        while type(a) is not Task2:
            a = a.get_item()

        while type(b) is not Task2:
            b = b.get_item()

        # Compare the last letter of name for testing
        first = a.props.title[-1]
        second = b.props.title[-1]

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class DueSorter(Gtk.Sorter):
    __gtype_name__ = 'DueSorter'

    def __init__(self):
        print('Sorter started')
        super(DueSorter, self).__init__()

    def do_compare(self, a, b) -> Gtk.Ordering:

        while type(a) is not Task2:
            a = a.get_item()

        while type(b) is not Task2:
            b = b.get_item()

        # Compare the last letter of name for testing
        first = a.date_due
        second = b.date_due

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class StartSorter(Gtk.Sorter):
    __gtype_name__ = 'StartSorter'

    def __init__(self):
        print('Sorter started')
        super(StartSorter, self).__init__()

    def do_compare(self, a, b) -> Gtk.Ordering:

        while type(a) is not Task2:
            a = a.get_item()

        while type(b) is not Task2:
            b = b.get_item()

        # Compare the last letter of name for testing
        first = a.date_start
        second = b.date_start

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class ModifiedSorter(Gtk.Sorter):
    __gtype_name__ = 'ModifiedSorter'

    def __init__(self):
        print('Sorter started')
        super(ModifiedSorter, self).__init__()

    def do_compare(self, a, b) -> Gtk.Ordering:

        while type(a) is not Task2:
            a = a.get_item()

        while type(b) is not Task2:
            b = b.get_item()

        # Compare the last letter of name for testing
        first = a.date_modified
        second = b.date_modified

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TagSorter(Gtk.Sorter):
    __gtype_name__ = 'TagSorter'

    def __init__(self):
        print('Sorter started')
        super(TagSorter, self).__init__()

    def do_compare(self, a, b) -> Gtk.Ordering:

        while type(a) is not Task2:
            a = a.get_item()

        while type(b) is not Task2:
            b = b.get_item()

        # Compare the last letter of name for testing
        if a.tags:
            first = a.tags[0].name[0]
        else:
            first = 'zzzzzzz'

        if b.tags:
            second = b.tags[0].name[0]
        else:
            second = 'zzzzzzz'

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class AddedSorter(Gtk.Sorter):
    __gtype_name__ = 'AddedSorter'

    def __init__(self):
        print('Sorter started')
        super(AddedSorter, self).__init__()

    def do_compare(self, a, b) -> Gtk.Ordering:

        while type(a) is not Task2:
            a = a.get_item()

        while type(b) is not Task2:
            b = b.get_item()

        # Compare the last letter of name for testing
        first = a.date_added
        second = b.date_added

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TitleFilter(Gtk.Filter):
    __gtype_name__ = 'TitleFilter'

    def __init__(self, title: str):
        print('Filter started')
        self.title = title
        super(TitleFilter, self).__init__()

    def do_match(self, item) -> bool:
        while type(item) is not Task2:
            item = item.get_item()

        # Yeah really basic, but should do
        return self.title in item.props.title


class ContentFilter(Gtk.Filter):
    __gtype_name__ = 'ContentFilter'

    def __init__(self, content: str):
        print('Filter started')
        self.content = content
        super(ContentFilter, self).__init__()

    def do_match(self, item) -> bool:
        while type(item) is not Task2:
            item = item.get_item()

        # Yeah really basic, but should do
        return self.content in item.content


class TagFilter(Gtk.Filter):
    __gtype_name__ = 'TagFilter'

    def __init__(self, tag: Tag2):
        print('Tag Filter started')

        self.tag = tag
        super(TagFilter, self).__init__()

    def do_match(self, item) -> bool:
        while type(item) is not Task2:
            item = item.get_item()

        print(item.props.title, self.tag in item.tags)

        return self.tag in item.tags


class StatusFilter(Gtk.Filter):
    __gtype_name__ = 'StatusFilter'

    def __init__(self, status: Status):
        print('Actionable Filter started')

        self.status = status
        super(StatusFilter, self).__init__()

    def do_match(self, item) -> bool:
        while type(item) is not Task2:
            item = item.get_item()

        return item.status == self.status


class ActionableFilter(Gtk.Filter):
    __gtype_name__ = 'ActionableFilter'

    def __init__(self):
        print('Actionable Filter started')

        super(ActionableFilter, self).__init__()

    def do_match(self, item) -> bool:
        while type(item) is not Task2:
            item = item.get_item()

        return item.is_actionable()


# --------------------------------------------------------------------------------
# DnD
# --------------------------------------------------------------------------------

def prepare(source, x, y):
    """Callback to prepare for the DnD operation"""

    print('Prearing DnD')

    # Get item somehow
    # Get content from source
    data = source.get_widget().props.obj

    # Set it as content provider
    content = Gdk.ContentProvider.new_for_value(data)

    return content


def drag_begin(source, drag):
    """Callback when DnD beings"""

    print('Begining DnD')
    source.get_widget().set_opacity(0.3)


def drag_end(source, drag, unused):
    """Callback when DnD ends"""

    print('Ending DnD')
    source.get_widget().set_opacity(1)


def drag_drop(self, value, x, y):
    """Callback when dropping onto a target"""

    print('Dropped', value, 'on', self.get_widget().props.obj)


def drop_enter(self, x, y, user_data=None):
    """Callback when the mouse hovers over the drop target."""

    expander = self.get_widget().get_first_child()
    expander.activate_action('listitem.expand')

    # There's a funny bug in here. If the expansion of the row
    # makes the window larger, Gtk won't recognize the new drop areas
    # and will think you're dragging outside the window.

    return Gdk.DragAction.COPY


# --------------------------------------------------------------------------------
# BASIC STUFF
# --------------------------------------------------------------------------------


class SomeType(GObject.Object):
    """Some basic type to test stuff"""

    __gtype_name__ = 'SomeType'
    int_prop = GObject.Property(default='OOO', type=str)

    def __init__(self, val):
        super(SomeType, self).__init__()
        self.set_property('int_prop', val)
        self.int_prop = val

    def __str__(self) -> str:
        return f'Sometype [{self.int_prop}]'


class MyBox(Gtk.Box):
    """Box subclass to keep a pointer to the SomeType prop"""

    obj = GObject.Property(type=Task2)


def selection_changed(self, position, n_items):
    print(self, position, n_items)
    bit = self.get_selection()

    print(bit)

    bititer = Gtk.BitsetIter()
    print('o', bititer.init_first(bit))
    print('is valid', bititer.is_valid())
    print('private', bititer.private_data)
    print('value', bititer.get_value())
    # print('next', bititer.next())


class TagPill(Gtk.DrawingArea):
    __gtype_name__ = 'TagPill'

    def __init__(self):
        super(TagPill, self).__init__()
        self.colors = [Gdk.RGBA()]
        self.set_draw_func(self.do_draw_function)

    def draw_rect(self, context, x, w, h, color=None):

        # center
        # x = 8
        # y = 8
        y = 0

        # w -= 16
        # h -= 16

        r = 10  # radius

        print(w, h)

        # Gdk.cairo_set_source_rgba(context, color)
        if color:
            context.set_source_rgba(color.red, color.green, color.blue)
        else:
            context.set_source_rgba(0, 0, 0, 0.2)

        #   A  *  BQ
        #  H       C
        #  *       *
        #  G       D
        #   F  *  E

        context.move_to(x + r, y)  # Move to A
        context.line_to(x + w - r, y)  # Line to B

        context.curve_to(
            x + w, y,
            x + w, y,
            x + w, y + r
        )  # Curve to C
        context.line_to(x + w, y + h - r)  # Line to D

        context.curve_to(
            x + w, y + h,
            x + w, y + h,
            x + w - r, y + h
        )  # Curve to E
        context.line_to(x + r, y + h)  # Line to F

        context.curve_to(
            x, y + h,
            x, y + h,
            x, y + h - r
        )  # Curve to G
        context.line_to(x, y + r)  # Line to H

        context.curve_to(
            x, y,
            x, y,
            x + r, y
        )  # Curve to A

    def do_draw_function(self, area, context, w, h, user_data=None):
        for i, color in enumerate(self.colors):
            x = i * (16 + 6)
            print('x', x, 'w', w)
            self.draw_rect(context, x, 16, h, color)
            context.fill()

            context.set_line_width(1.0)
            self.draw_rect(context, x, 16, h, None)
            context.stroke()


def model_func(item):
    """Callback when the tree expander is clicked or shown

        Should return none or an empty list if there are no
        children, otherwise return a Gio.ListStore or
        a TreeListModel
    """

    # print('Called model_func (', item, ')')

    model = Gio.ListStore.new(Task2)

    if type(item) == Gtk.TreeListRow:
        item = item.get_item()

    # Shows we can use tag2 children list in here to
    # populate the child model
    # print('children', item.children)

    # open the first one
    if item.children:
        for child in item.children:
            model.append(child)

        return Gtk.TreeListModel.new(model, False, False, model_func)
    else:
        return None

    # if item.props.name == 'test':
    #     print('Returning children')
    #     model.append(Tag2(uuid4(), 'test5'))
    #     model.append(Tag2(uuid4(), 'test6'))
    #     model.append(Tag2(uuid4(), 'test7'))

    #     return Gtk.TreeListModel.new(model, False, False, model_func)

    # # A nested one
    # if item.props.name == 'test7':
    #     model.append(Tag2(uuid4(), 'test8'))
    #     model.append(Tag2(uuid4(), 'test9'))

    #     return Gtk.TreeListModel.new(model, False, False, model_func)


# def add_color(color: str) -> Gtk.Button:
#     """Create a color pill for tags."""

#     pill = Gtk.Button()
#     pill.set_sensitive(False)
#     pill.set_margin_end(6)
#     pill.set_valign(Gtk.Align.CENTER)
#     pill.set_halign(Gtk.Align.CENTER)
#     pill.set_vexpand(False)

#     background = str.encode('* { background: #' + item.props.color + ' ; padding: 0; min-height: 16px; min-width: 16px; border: none;}')

#     cssProvider = Gtk.CssProvider()
#     cssProvider.load_from_data(background)
#     color.get_style_context().add_provider(cssProvider,
#                                         Gtk.STYLE_PROVIDER_PRIORITY_USER)


#     return pill

def setup_cb(factory, listitem, user_data=None):
    """Setup widgets for rows"""

    box = MyBox()
    label = Gtk.Label()
    expander = Gtk.TreeExpander()
    icons = Gtk.Label()
    check = Gtk.CheckButton()
    color = TagPill()
    due = Gtk.Label()
    start = Gtk.Label()

    padding = str.encode('box { padding: 12px; }')

    cssProvider = Gtk.CssProvider()
    cssProvider.load_from_data(padding)
    box.get_style_context().add_provider(cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    # color.set_margin_top(7)
    # color.set_margin_bottom(7)
    color.set_size_request(16, 16)

    # Does this even work?
    color.set_vexpand(False)
    color.set_valign(Gtk.Align.CENTER)

    expander.set_margin_end(6)
    icons.set_margin_end(6)
    check.set_margin_end(6)

    # DnD stuff
    source = Gtk.DragSource()
    source.connect('prepare', prepare)
    source.connect('drag-begin', drag_begin)
    source.connect('drag-end', drag_end)
    box.add_controller(source)

    # Set drop for DnD
    drop = Gtk.DropTarget.new(Task2, Gdk.DragAction.COPY)
    drop.connect('drop', drag_drop)
    drop.connect('enter', drop_enter)

    box.add_controller(drop)

    box.append(expander)
    box.append(check)
    box.append(label)
    box.append(color)
    box.append(icons)
    box.append(due)
    box.append(start)
    listitem.set_child(box)


# def generate_css(tags: list) -> bytes:
#     """Generate CSS styles for tags."""

#     style = []

#     for tag in tags:
#         if tag.color:
#             color_text = 'rgba(255, 0, 0, 0.25)'
#             style.append(f'.tag-{tag.name}' + '{' + color_text + '; }')

#     return str.encode('\n'.join(style))


def bind(self, listitem, user_data=None):
    """Bind values to the widgets in setup_cb"""

    # Kind of ugly
    expander = listitem.get_child().get_first_child()
    check = expander.get_next_sibling()
    label = check.get_next_sibling()
    color = label.get_next_sibling()
    icons = color.get_next_sibling()
    due = icons.get_next_sibling()
    start = due.get_next_sibling()

    box = listitem.get_child()

    # icons.set_visible(False)
    # color.set_visible(False)

    # HACK: Ugly! But apparently necessary
    item = listitem.get_item()
    while type(item) is not Task2:
        item = item.get_item()

    # LMAO why did I make this so confusing
    colors = []
    for t in item.tags:
        if t.color:
            colorstr = Gdk.RGBA()
            colorstr.parse('#' + t.color[:-2])
            colors.append(colorstr)

    color.set_size_request((16 + 6) * len(colors), 16)
    color.colors = colors

    box.props.obj = item
    expander.set_list_row(listitem.get_item())

    # Set icons from tags
    icons_text = ''
    for t in item.tags:
        if t.icon:
            icons_text += t.icon

    icons.set_text(icons_text)

    # Set row color
    for t in item.tags:
        if t.color:
            color = Gdk.RGBA()
            color.parse('#' + t.color[:-2])
            color.alpha = 0.25
            background = str.encode('* { background:' + color.to_string() + '; }')

            cssProvider = Gtk.CssProvider()
            cssProvider.load_from_data(background)
            box.get_style_context().add_provider(cssProvider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER)

    label.set_text(item.props.title)
    label.set_hexpand(True)
    label.set_margin_end(6)
    label.set_xalign(0)
    box.set_tooltip_text(item.props.excerpt)

    if item.date_due:
        due.set_text('Due: ' + str(item.date_due))

    due.set_margin_end(12)

    if item.date_start:
        start.set_text('Start: ' + str(item.date_start))


# When the application is launched…
def on_activate(app):
    # … create a new window…
    win = Gtk.ApplicationWindow(application=app)
    main = Gtk.Box()
    box = Gtk.Box()

    # Create the tags
    tag1 = Tag2(uuid4(), 'test')
    tag1._icon = '😎️'

    tag2 = Tag2(uuid4(), 'test2-nofilterbro')
    tag2._icon = '👹️'

    tag3 = Tag2(uuid4(), 'test5')
    tag3._color = 'b6d7a8be'

    tag4 = Tag2(uuid4(), 'test3-nofilterbro')

    tag5 = Tag2(uuid4(), 'test5')
    tag5._color = '0fdfe8be'

    tag6 = Tag2(uuid4(), 'test6')
    tag7 = Tag2(uuid4(), 'test7')

    tag8 = Tag2(uuid4(), 'test8')
    tag9 = Tag2(uuid4(), 'test9')

    tag2._color = 'f6eeaebe'

    tag1.children = [tag4, tag5, tag6, tag7]
    tag7.children = [tag8, tag9]

    # Create the tasks
    task1 = Task2(uuid4(), 'test')
    task1.content = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed placerat finibus massa sit amet suscipit. Fusce pharetra elit ex, accumsan faucibus nisl hendrerit et. Mauris consequat, est ac tempus euismod, tortor diam dapibus ante, ac gravida est urna ac risus. Sed feugiat, nibh nec porta luctus, diam ex ullamcorper felis, at congue magna nisi id lorem. Pellentesque venenatis gravida consectetur. Suspendisse suscipit ligula ut risus dictum, et accumsan dolor pretium. Nam aliquam nulla vel pulvinar efficitur. Praesent tincidunt euismod accumsan.
Fusce blandit viverra orci, a venenatis mauris venenatis auctor. Morbi in sodales orci. Donec nec turpis at lectus aliquet interdum. Nullam sit amet dui ut velit facilisis ullamcorper a eget ex. Pellentesque lacinia efficitur massa vel feugiat. Etiam luctus leo at lorem pretium, eu pellentesque turpis porta. Sed commodo nulla ac lacus ultrices tempus. Duis volutpat lacinia augue. Ut vel accumsan urna, eget mattis diam. Cras egestas ante urna, sit amet condimentum augue rhoncus non.
'''

    task1.add_tag(tag1)
    task1.add_tag(tag2)

    task2 = Task2(uuid4(), 'test2-nofilterbro')
    task2.date_due = Date('soon')

    task3 = Task2(uuid4(), 'test5')

    task3.add_tag(tag3)
    task3.add_tag(tag5)

    task4 = Task2(uuid4(), 'test3-nofilterbro')
    task5 = Task2(uuid4(), 'test5')
    task6 = Task2(uuid4(), 'test6')
    task7 = Task2(uuid4(), 'test7')
    task8 = Task2(uuid4(), 'test8')
    task9 = Task2(uuid4(), 'test9')

    task8.add_tag(tag2)
    task4.toggle_status()
    task5.dismiss()

    task2.date_due = Date('soon')
    task4.date_start = Date('2018-12-20')
    task4.date_due = Date('2019-12-21')
    task1.date_start = Date('someday')

    task1.children = [task5, task6, task7]
    task7.children = [task8, task9]

    # Root Model with some items
    model = Gio.ListStore.new(Task2)
    model.append(task1)
    model.append(task2)
    model.append(task3)
    model.append(task4)

    # Init Tree model
    treeModel = Gtk.TreeListModel.new(model, False, False, model_func)

    # Filter model
    filtered = Gtk.FilterListModel()
    filtered.set_model(treeModel)
    # filtered.set_filter(TagFilter(tag3))
    # filtered.set_filter(StatusFilter(Status.ACTIVE))
    # filtered.set_filter(ActionableFilter())

    # Sort model
    # But first wrap it in a TreeListRowSorter
    # so it doesn't break the hierarchy in the view
    # when sorting
    tree_sort = Gtk.TreeListRowSorter()
    # tree_sort.set_sorter(MySorter())
    # tree_sort.set_sorter(TagSorter())
    # tree_sort.set_sorter(DueSorter())

    sort = Gtk.SortListModel()
    sort.set_sorter(tree_sort)

    # Change commented line to try filter
    sort.set_model(filtered)
    # sort.set_model(treeModel)

    # Wrap it in a selection model
    selection = Gtk.MultiSelection.new(sort)
    selection.connect('selection-changed', selection_changed)

    fac = Gtk.SignalListItemFactory()
    fac.connect('setup', setup_cb)
    fac.connect('bind', bind)

    # Init the listview
    view = Gtk.ListView.new(selection, fac)
    view.set_vexpand(True)
    view.set_hexpand(True)

    # view.get_style_context().add_class('rich-list')

    btns = Gtk.Box()

    btn_sorter1 = Gtk.Button.new_with_label('Sort by tag')
    btn_sorter1.connect('clicked', lambda _: sort.set_sorter(TagSorter()))
    btn_sorter1.set_margin_bottom(6)
    btns.append(btn_sorter1)

    btn_sorter2 = Gtk.Button.new_with_label('Sort by title')
    btn_sorter2.set_margin_bottom(6)
    btn_sorter2.connect('clicked', lambda _: sort.set_sorter(MySorter()))
    btns.append(btn_sorter2)

    btn_sorter3 = Gtk.Button.new_with_label('Sort by Due date')
    btn_sorter3.set_margin_bottom(6)
    btn_sorter3.connect('clicked', lambda _: sort.set_sorter(DueSorter()))
    btns.append(btn_sorter3)

    btn_sorter4 = Gtk.Button.new_with_label('Sort by start date')
    btn_sorter4.set_margin_bottom(6)
    btn_sorter4.connect('clicked', lambda _: sort.set_sorter(StartSorter()))
    btns.append(btn_sorter4)

    btn_sorter5 = Gtk.Button.new_with_label('Sort by modified date')
    btn_sorter5.set_margin_bottom(6)
    btn_sorter5.connect('clicked', lambda _: sort.set_sorter(ModifiedSorter()))
    btns.append(btn_sorter5)

    btn_sorter6 = Gtk.Button.new_with_label('Sort by added date')
    btn_sorter6.set_margin_bottom(20)
    btn_sorter6.connect('clicked', lambda _: sort.set_sorter(AddedSorter()))
    btns.append(btn_sorter6)

    btn_filter1 = Gtk.Button.new_with_label('Filter by title')
    btn_filter1.set_margin_bottom(6)
    btn_filter1.connect('clicked', lambda _: filtered.set_filter(TitleFilter('nofilter')))
    btns.append(btn_filter1)

    btn_filter2 = Gtk.Button.new_with_label('Filter by tag')
    btn_filter2.connect('clicked', lambda _: filtered.set_filter(TagFilter(tag3)))
    btn_filter2.set_margin_bottom(6)
    btns.append(btn_filter2)

    btn_filter3 = Gtk.Button.new_with_label('Filter by content')
    btn_filter3.connect('clicked', lambda _: filtered.set_filter(ContentFilter('lorem')))
    btn_filter3.set_margin_bottom(6)
    btns.append(btn_filter3)

    btn_filter4 = Gtk.Button.new_with_label('Filter only active')
    btn_filter4.connect('clicked', lambda _: filtered.set_filter(StatusFilter(Status.ACTIVE)))
    btn_filter4.set_margin_bottom(6)
    btns.append(btn_filter4)

    btn_filter5 = Gtk.Button.new_with_label('Filter only actionable')
    btn_filter5.connect('clicked', lambda _: filtered.set_filter(ActionableFilter()))
    btn_filter5.set_margin_bottom(6)
    btns.append(btn_filter5)

    btn_filter6 = Gtk.Button.new_with_label('No filter')
    btn_filter6.connect('clicked', lambda _: filtered.set_filter(None))
    btn_filter6.set_margin_bottom(6)
    btns.append(btn_filter6)

    btns.set_orientation(Gtk.Orientation.VERTICAL)

    # cssProvider = Gtk.CssProvider()
    # cssProvider.load_from_data(generate_css([tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9]))
    # view.get_style_context().add_provider(cssProvider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    # Seal the deal
    box.append(view)
    box.set_vexpand(True)
    box.set_hexpand(True)

    main.append(btns)
    main.append(box)
    win.set_child(main)

    win.set_default_size(800, 600)
    win.present()


# Create a new application
app = Gtk.Application(application_id='com.example.GtkApplication')
app.connect('activate', on_activate)

# Run the application
app.run(None)
