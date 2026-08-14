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
