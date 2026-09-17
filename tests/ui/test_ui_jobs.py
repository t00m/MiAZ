#!/usr/bin/python3

"""UI: the headerbar indicator for background work.

The queue itself is backend and tested headlessly in tests/test_jobs.py. What
needs a window is the part that decides when to appear: a spinner that flickered
through ordinary browsing would be worse than no spinner at all, because
housekeeping runs constantly.
"""

import pytest


@pytest.fixture
def indicator(clean_view):
    widget = clean_view.widget('headerbar-widget-jobs')
    assert widget is not None, 'the headerbar has no background work indicator'
    return widget


def test_the_indicator_is_hidden_when_nothing_is_running(indicator, clean_view):
    clean_view.pump(0.8)
    assert indicator.get_visible() is False


def test_short_work_never_shows_the_indicator(indicator, clean_view):
    """workspace-scan and index-reload run in well under half a second, all the
    time. They are counted and never seen."""
    queue = clean_view.service('jobs')
    job = queue.add('workspace-scan')
    queue.start(job)
    clean_view.pump(0.2)
    queue.finish(job)
    clean_view.pump(0.5)
    assert indicator.get_visible() is False


def test_long_work_shows_the_indicator(indicator, clean_view):
    queue = clean_view.service('jobs')
    job = queue.add('importdoc-batch', label='Importing documents')
    queue.start(job)
    try:
        clean_view.wait_until(lambda: indicator.get_visible() is True,
                              message='the indicator to appear')
    finally:
        queue.finish(job)
        clean_view.pump(0.5)


def test_the_indicator_goes_away_when_the_work_ends(indicator, clean_view):
    queue = clean_view.service('jobs')
    job = queue.add('importdoc-batch', label='Importing documents')
    queue.start(job)
    clean_view.wait_until(lambda: indicator.get_visible() is True,
                          message='the indicator to appear')
    queue.finish(job)
    clean_view.wait_until(lambda: indicator.get_visible() is False,
                          message='the indicator to go away')


def test_the_count_says_how_many_are_in_flight(indicator, clean_view):
    queue = clean_view.service('jobs')
    first = queue.add('importdoc-batch', label='Importing documents')
    second = queue.add('importfromzip', label='Importing a ZIP file')
    queue.start(first)
    queue.start(second)
    try:
        clean_view.wait_until(lambda: indicator.get_visible() is True,
                              message='the indicator to appear')
        assert indicator.count_label.get_text() == '2'
    finally:
        queue.finish(first)
        queue.finish(second)
        clean_view.pump(0.5)


def test_the_popover_names_the_running_job(indicator, clean_view):
    queue = clean_view.service('jobs')
    job = queue.add('importdoc-batch', label='Importing documents')
    queue.start(job)
    queue.report(job, '340 of 1322', 0.257)
    try:
        clean_view.wait_until(lambda: indicator.get_visible() is True,
                              message='the indicator to appear')
        clean_view.pump(0.3)
        text = indicator.describe()
        assert 'Importing documents' in text
        assert '340 of 1322' in text
    finally:
        queue.finish(job)
        clean_view.pump(0.5)
