#!/usr/bin/python3

"""
# File: vocabulary.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Translatable labels for the built-in controlled vocabularies.

The default Group and Purpose descriptions ship as English strings in
data/resources/conf/MiAZ-groups.json and MiAZ-purposes.json and are copied into
each repository on creation. They are repeated here as gettext literals so
xgettext extracts them into the 'miaz' catalog; util.humanize_value() then
translates them for display, with the English string as fallback. The values
must match the JSON exactly; tests/test_vocabulary.py verifies that.

This module is not imported at runtime. It exists only for string extraction.
"""

from gettext import gettext as _

GROUP_LABELS = [
    _('Billing'),
    _('Civil Status'),
    _('Configuration'),
    _('Education'),
    _('Employment'),
    _('Financial'),
    _('Housing'),
    _('Insurance'),
    _('Legal'),
    _('Leisure'),
    _('Loans'),
    _('Medical'),
    _('Miscellaneous'),
    _('Personal'),
    _('Public Administration'),
    _('Services'),
    _('Shopping'),
    _('Social Security'),
    _('Taxes'),
    _('Travel'),
    _('Utilities'),
    _('Vehicle'),
    _('Work'),
]

PURPOSE_LABELS = [
    _('Agreement'),
    _('Analysis'),
    _('Appointment'),
    _('Authorization'),
    _('Budget'),
    _('Cancellation'),
    _('Certification'),
    _('Claim'),
    _('Confirmation'),
    _('Contract'),
    _('Curriculum Vitae'),
    _('Declaration'),
    _('Email'),
    _('Form'),
    _('Identification'),
    _('Information'),
    _('Invoice'),
    _('Letter'),
    _('Manual'),
    _('Minutes'),
    _('Notification'),
    _('Order'),
    _('Payment'),
    _('Payslip'),
    _('Picture'),
    _('Plan'),
    _('Policy'),
    _('Project'),
    _('Proof'),
    _('Receipt'),
    _('Reminder'),
    _('Report'),
    _('Request'),
    _('Schedule'),
    _('Statement'),
    _('Task'),
    _('Template'),
    _('Transfer'),
    _('Warning'),
]
