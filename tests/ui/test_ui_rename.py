#!/usr/bin/python3

"""UI: the rename dialog. Checklist sections 4 and 11."""

import pytest

DOCUMENT = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'
# Its sender is not in the configuration, which is what makes the dialog open
# invalid, as it does for a real document that needs review.
UNKNOWN_DOCUMENT = '20260401-ES-FIN-STRANGER-INV-unknown-JOHNDOE.pdf'


@pytest.fixture
def rename_dialog(clean_view):
    """Open the real rename dialog, and close it however the test ends."""
    actions = clean_view.service('actions')
    actions._document_rename_single(DOCUMENT)
    clean_view.wait_until(lambda: clean_view.widget('dialog-rename') is not None,
                          message='the rename dialog')
    dialog = clean_view.widget('dialog-rename')
    widget = clean_view.widget('rename-widget')
    clean_view.pump(0.3)
    yield clean_view, dialog, widget
    dialog.emit('response', 'cancel')
    clean_view.pump(0.3)


def rename_button(dialog):
    return dialog._buttons['apply']


def test_the_dialog_opens_with_the_fields_filled(rename_dialog):
    """4.1."""
    _driver, _dialog, widget = rename_dialog
    assert widget.entry_date.get_text() == '20260612'
    assert widget.entry_concept.get_text().upper().startswith('MORTGAGE')


def test_rename_is_insensitive_while_values_are_unknown(clean_view):
    """4.2: an unknown sender leaves that dropdown on Any, so the name cannot
    be built and the button must not pretend otherwise."""
    actions = clean_view.service('actions')
    actions._document_rename_single(UNKNOWN_DOCUMENT)
    clean_view.wait_until(
        lambda: clean_view.widget('dialog-rename') is not None,
        message='the rename dialog')
    dialog = clean_view.widget('dialog-rename')
    widget = clean_view.widget('rename-widget')
    clean_view.pump(0.4)
    try:
        assert widget.is_valid() is False
        assert rename_button(dialog).get_sensitive() is False
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_rename_becomes_sensitive_once_the_fields_are_valid(rename_dialog):
    """4.3."""
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    assert widget.is_valid() is True
    assert rename_button(dialog).get_sensitive() is True


def test_rename_goes_insensitive_again_when_the_concept_is_cleared(rename_dialog):
    """4.4."""
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    widget.entry_concept.set_text('')
    driver.pump(0.3)
    assert rename_button(dialog).get_sensitive() is False


def test_group_and_purpose_do_not_block(rename_dialog):
    """4.5: they are advisory, and the button must not wait for them."""
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    widget.dpdGroup.set_selected(0)
    widget.dpdPurpose.set_selected(0)
    driver.pump(0.3)
    assert rename_button(dialog).get_sensitive() is True


def test_the_preview_follows_the_fields(rename_dialog):
    """4.10."""
    driver, _dialog, widget = rename_dialog
    widget.entry_concept.set_text('somethingelse')
    driver.pump(0.3)
    assert 'SOMETHINGELSE' in widget.lblFilenameNew.get_text().upper()


def test_the_suggest_button_needs_two_characters(rename_dialog):
    """4.18."""
    driver, _dialog, widget = rename_dialog
    button = driver.widget('rename-button-suggest')
    if button is None:
        pytest.skip('the Suggest button is not registered under a widget name')
    widget.entry_concept.set_text('a')
    driver.pump(0.3)
    assert button.get_sensitive() is False
    widget.entry_concept.set_text('ab')
    driver.pump(0.3)
    assert button.get_sensitive() is True


def test_cancel_writes_nothing(rename_dialog, sandbox):
    """4.16."""
    import os
    driver, dialog, widget = rename_dialog
    fill_required(driver, widget)
    widget.entry_concept.set_text('cancelled')
    driver.pump(0.2)
    dialog.emit('response', 'cancel')
    driver.pump(0.4)
    assert os.path.exists(os.path.join(sandbox['Alpha'], DOCUMENT))


def fill_required(driver, widget):
    """Set the five fields that block a rename, as a user would."""
    widget.entry_date.set_text('20260612')
    for dropdown in (widget.dpdCountry, widget.dpdSentBy, widget.dpdSentTo):
        pick_first_real_value(dropdown)
    widget.entry_concept.set_text('mortgage')
    driver.pump(0.4)


def pick_first_real_value(dropdown):
    model = dropdown.get_model()
    for position in range(len(model)):
        if model.get_item(position).id != 'Any':
            dropdown.set_selected(position)
            return
    raise AssertionError('the dropdown offers no real value')


# ---------------------------------------------------------------------------
# 4.6: the date field
# ---------------------------------------------------------------------------

def test_an_impossible_date_is_refused_and_kept(rename_dialog):
    """4.6: 20261301 has no month 13.

    Refused means the field keeps what was typed, so the user can see and fix
    it, and Rename stays insensitive. Replacing it with a valid date is the
    one thing that must not happen: the dialog would then be ready to rename
    the document to a date nobody chose.
    """
    driver, dialog, widget = rename_dialog

    widget.entry_date.set_text('20261301')
    driver.pump(0.4)

    assert widget.entry_date.get_text() == '20261301'
    assert widget.validate_date('20261301') is False
    assert rename_button(dialog).get_sensitive() is False
    # And nothing next to the field may still read as a real date.
    assert 'not a date' in widget.label_date.get_text()


def test_a_valid_date_typed_by_hand_is_accepted(rename_dialog):
    driver, dialog, widget = rename_dialog

    widget.entry_date.set_text('20260301')
    driver.pump(0.4)

    assert widget.entry_date.get_text() == '20260301'
    assert '2026' in widget.label_date.get_text()
    assert rename_button(dialog).get_sensitive() is True


def test_a_half_typed_date_does_not_become_a_real_one(rename_dialog):
    """Typing goes through incomplete states. None of them may be completed
    for the user: '2026' is not 2026-01-01."""
    driver, dialog, widget = rename_dialog

    for text in ('2', '20', '202', '2026', '20261', '202613'):
        widget.entry_date.set_text(text)
        driver.pump(0.15)
        assert widget.entry_date.get_text() == text


# ---------------------------------------------------------------------------
# 4.9: the manage button next to a restricted field
# ---------------------------------------------------------------------------

def open_manage(driver, widget, button):
    """Click a field's manage button and return the window it opens."""
    driver.app.add_widget('dialog-manage-resource', None)
    button.emit('clicked')
    driver.wait_until(
        lambda: driver.widget('dialog-manage-resource') is not None,
        message='the manage window')
    driver.pump(0.3)
    return driver.widget('dialog-manage-resource')


def test_the_manage_window_is_populated_every_time(rename_dialog):
    """4.9: it used to come up empty from the second click on.

    The selector was built once, when the button was connected, and the first
    window took ownership of it. The second window packed a widget that was
    already spoken for, so it showed nothing until the rename dialog itself
    was closed and rebuilt.
    """
    driver, _dialog, widget = rename_dialog

    for attempt in ('first', 'second'):
        window = open_manage(driver, widget, widget.btnCountry)
        # The window holds the configuration view: it must have rows both times.
        views = [child for child in _walk(window) if hasattr(child, 'get_config_for')]
        assert views, f'{attempt} opening has no configuration view'
        view = views[0]
        assert len(view.viewSl.get_model_filter()) > 0, \
            f'{attempt} opening shows an empty list'
        window.close()
        driver.pump(0.3)


def _walk(widget):
    """Every widget under this one, itself included."""
    yield widget
    child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
    while child is not None:
        yield from _walk(child)
        child = child.get_next_sibling()
