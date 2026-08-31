#!/usr/bin/python3

"""UI: the progress dialog that backup and restore run behind.

The operations themselves are covered headless in tests/test_dr.py. What needs
the running application is what used to be wrong: the work ran on the main loop,
so the window froze with nothing on screen to say why, and the outcome was a
toast that faded before it could be read.
"""

import threading


def test_the_ui_is_held_until_the_dialog_is_closed(miaz):
    progress = miaz.service('progress')
    content = miaz.widget('window-mainbox')
    release = threading.Event()

    def work(report):
        report('halfway', 0.5)
        release.wait(10)
        return 'It worked.'

    dialog = progress.run(work, title='Testing')
    try:
        assert dialog is not None
        miaz.pump(0.3)
        assert progress.is_busy() is True
        assert content.get_sensitive() is False
        # The dialog lives beside the content it disables, not inside it, so it
        # stays usable. Disabling the window itself would take the dialog with
        # it, Close button included.
        assert dialog.is_sensitive() is True
        assert dialog.get_response_enabled('close') is False
        # Nothing dismisses it while the files are still moving, Escape
        # included: close() reports that it did not close.
        assert dialog.close() is False

        release.set()
        miaz.wait_until(lambda: dialog.get_response_enabled('close'),
                        message='the work to finish')
        assert dialog.get_body() == 'It worked.'
        # Still held: the outcome waits to be read.
        assert content.get_sensitive() is False
        assert progress.is_busy() is True
    finally:
        release.set()
        dialog.close()
        miaz.pump(0.3)

    assert content.get_sensitive() is True
    assert progress.is_busy() is False


def test_a_failure_says_what_happened_and_gives_the_ui_back(miaz):
    progress = miaz.service('progress')
    content = miaz.widget('window-mainbox')
    closed = []

    def work(_report):
        raise RuntimeError('the disk is on fire')

    dialog = progress.run(work, title='Testing',
                          on_close=lambda ok, result: closed.append((ok, result)))
    try:
        miaz.wait_until(lambda: dialog.get_response_enabled('close'),
                        message='the failure to be reported')
        assert 'the disk is on fire' in dialog.get_body()
    finally:
        dialog.close()
        miaz.pump(0.3)

    assert content.get_sensitive() is True
    assert closed and closed[0][0] is False


def test_a_second_operation_is_refused_while_one_runs(miaz):
    """One dialog holds the UI. A second operation started behind it would
    write to the same files with nothing on screen to say so."""
    progress = miaz.service('progress')
    release = threading.Event()

    dialog = progress.run(lambda _report: release.wait(10), title='First')
    try:
        miaz.pump(0.2)
        assert progress.run(lambda _report: 'second', title='Second') is None
    finally:
        release.set()
        miaz.wait_until(lambda: dialog.get_response_enabled('close'),
                        message='the first operation to finish')
        dialog.close()
        miaz.pump(0.3)

    assert miaz.widget('window-mainbox').get_sensitive() is True


def test_the_outcome_falls_back_to_a_plain_done(miaz):
    """Work that returns nothing, or something that is not text, still has to
    say it finished. A dialog that cannot word its outcome must not become the
    thing that traps the UI, so Close is enabled before the wording is tried."""
    progress = miaz.service('progress')
    for result in (None, 42):
        dialog = progress.run(lambda _report, value=result: value, title='Testing')
        try:
            miaz.wait_until(lambda: dialog.get_response_enabled('close'),
                            message='the work to finish')
            assert dialog.get_body() == 'Done.'
        finally:
            dialog.close()
            miaz.pump(0.3)

    assert miaz.widget('window-mainbox').get_sensitive() is True
