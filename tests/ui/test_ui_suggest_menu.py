#!/usr/bin/python3

"""UI: the rename dialog's Suggest menu.

Two things proposed values for the same filename fields from two different
corners of the dialog: the core's concept match on the bottom action bar, and
MiAZAIAssistant's Adw.SplitButton in the header. They live under one menu
button now, which the core owns and plugins contribute to. It sits at the right
of the header bar, labelled: the first version was an unlabelled icon on the
bottom action bar and could not be found.
"""

from gi.repository import Gtk

DOCUMENT = '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'


def section_headings(menu):
    """The heading of each section, in order."""
    found = []
    for i in range(menu.get_n_items()):
        if menu.get_item_link(i, 'section') is not None:
            label = menu.get_item_attribute_value(i, 'label', None)
            found.append(label.get_string() if label is not None else None)
    return found


def labels_of(menu):
    """Every label in a Gio.Menu, sections included."""
    found = []
    for i in range(menu.get_n_items()):
        label = menu.get_item_attribute_value(i, 'label', None)
        if label is not None:
            found.append(label.get_string())
        link = menu.get_item_link(i, 'section')
        if link is not None:
            found.extend(labels_of(link))
    return found


def walk(widget):
    child = widget.get_first_child()
    while child is not None:
        yield child
        yield from walk(child)
        child = child.get_next_sibling()


def suggest_button(dialog):
    """The Suggest menu button, found by its tooltip rather than by position."""
    for widget in walk(dialog.headerbar):
        if isinstance(widget, Gtk.MenuButton) and \
                widget.get_tooltip_text() == 'Suggest values for the filename fields':
            return widget
    return None


def open_rename(driver):
    driver.service('actions')._document_rename_single(DOCUMENT)
    driver.wait_until(lambda: driver.widget('dialog-rename') is not None,
                      message='the rename dialog')
    driver.pump(0.3)
    return driver.widget('dialog-rename')


def test_suggest_is_one_labelled_menu_button_in_the_header(clean_view):
    dialog = open_rename(clean_view)
    try:
        button = suggest_button(dialog)
        assert button is not None, 'no Suggest menu button in the header bar'
        assert button.get_menu_model() is not None
        # Labelled, not a bare icon: an unlabelled icon is not findable.
        labels = [w.get_text() for w in walk(button) if isinstance(w, Gtk.Label)]
        assert 'Suggest' in labels, labels
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_the_core_entries_are_in_the_menu(clean_view):
    """Detect used to be a second button. Its entries are here now."""
    actions = clean_view.service('actions')
    labels = labels_of(actions.build_suggest_menu())
    assert 'Sharing this concept' in labels
    for field in ('Date', 'Country', 'Sent by', 'Sent to', 'Every field'):
        assert field in labels, labels


def test_the_menu_says_which_entries_leave_the_machine(clean_view):
    """A user choosing between a guess made here and one that sends the
    document to a model has to see the difference before choosing."""
    actions = clean_view.service('actions')
    headings = section_headings(actions.build_suggest_menu())
    assert 'From this document' in headings, headings
    assert 'From documents already filed' in headings, headings


def test_a_plugin_section_is_grouped_under_its_own_heading(clean_view):
    actions = clean_view.service('actions')
    actions.build_suggest_menu()
    actions.register_suggest_item(
        owner='TestPlugin', name='test-suggest-entry', label='Ask something',
        callback=lambda *_a: None, section='With a test plugin')
    try:
        headings = section_headings(actions.build_suggest_menu())
        assert headings[-1] == 'With a test plugin', headings
    finally:
        actions.unregister_suggest_items(owner='TestPlugin')


def test_there_is_no_separate_detect_button(clean_view):
    """Two buttons offering to fill the same fields is what this replaced."""
    dialog = open_rename(clean_view)
    try:
        buttons = [w for w in walk(dialog.headerbar)
                   if isinstance(w, (Gtk.Button, Gtk.MenuButton))
                   and 'Detect' in (w.get_tooltip_text() or '')]
        assert buttons == [], [b.get_tooltip_text() for b in buttons]
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_suggest_belongs_to_the_fields_page(clean_view):
    """Nothing in it proposes a project or a periodicity, so on a plugin page
    it would offer to fill in fields the user cannot see."""
    dialog = open_rename(clean_view)
    widget = clean_view.widget('rename-widget')
    try:
        assert suggest_button(dialog).get_visible() is True

        if widget.plugin_tabs:
            widget.stack.set_visible_child_name(widget.plugin_tabs[0][0])
            clean_view.pump(0.3)
            assert suggest_button(dialog) is None or \
                suggest_button(dialog).get_visible() is False

            widget.stack.set_visible_child_name('fields')
            clean_view.pump(0.3)
            assert suggest_button(dialog).get_visible() is True
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_the_local_entry_follows_the_concept(clean_view):
    """It matches on the concept, so it is dead until there is one to match.
    The button itself stays usable: a plugin entry may not need a concept."""
    dialog = open_rename(clean_view)
    actions = clean_view.service('actions')
    widget = clean_view.widget('rename-widget')
    try:
        widget.entry_concept.set_text('')
        clean_view.pump(0.3)
        assert actions._suggest_actions['rename-suggest-local'].get_enabled() is False
        assert suggest_button(dialog).get_sensitive() is True

        widget.entry_concept.set_text('mortgage')
        clean_view.pump(0.3)
        assert actions._suggest_actions['rename-suggest-local'].get_enabled() is True
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_a_plugin_entry_is_added_and_taken_away_again(clean_view):
    """What MiAZAIAssistant does, without needing it enabled: register, appear,
    unregister, gone. A plugin that unloads must not leave a dead entry behind.
    """
    actions = clean_view.service('actions')
    actions.build_suggest_menu()
    fired = []
    actions.register_suggest_item(
        owner='TestPlugin', name='test-suggest-entry', label='With a test plugin',
        callback=lambda *_a: fired.append(True))
    try:
        labels = labels_of(actions.build_suggest_menu())
        assert 'With a test plugin' in labels
        assert 'Sharing this concept' in labels, \
            'the core entry was lost when a plugin added one'
    finally:
        actions.unregister_suggest_items(owner='TestPlugin')

    labels = labels_of(actions.build_suggest_menu())
    assert 'With a test plugin' not in labels
    assert 'Sharing this concept' in labels


def test_registering_the_same_entry_twice_does_not_stack_it(clean_view):
    """Plugins are unloaded and loaded again on every repository switch."""
    actions = clean_view.service('actions')
    actions.build_suggest_menu()
    for _ in range(3):
        actions.register_suggest_item(
            owner='TestPlugin', name='test-suggest-entry', label='Once only',
            callback=lambda *_a: None)
    try:
        assert labels_of(actions.build_suggest_menu()).count('Once only') == 1
    finally:
        actions.unregister_suggest_items(owner='TestPlugin')


def test_the_plugin_no_longer_packs_a_button_of_its_own(clean_view):
    """MiAZAIAssistant used to add an Adw.SplitButton beside the core's
    button. There must be exactly one suggestion control, the shared menu."""
    dialog = open_rename(clean_view)
    try:
        buttons = [w for w in walk(dialog.headerbar)
                   if isinstance(w, (Gtk.Button, Gtk.MenuButton))
                   and (w.get_tooltip_text() or '').startswith('Suggest')]
        assert len(buttons) == 1, [b.get_tooltip_text() for b in buttons]
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_the_menu_entries_are_actually_usable(clean_view):
    """Every entry came up greyed out: the menus point at app.* actions, and
    the rename dialog is a top-level Adw.Window that was never attached to the
    application, so GTK could not resolve them and disabled the lot. It hit the
    Detect menu the same way.
    """
    dialog = open_rename(clean_view)
    widget = clean_view.widget('rename-widget')
    try:
        widget.entry_concept.set_text('mortgage')
        clean_view.pump(0.3)

        assert dialog.get_application() is not None, (
            "the dialog is not attached to the application, so GTK cannot "
            "resolve the app.* actions its menus point at and renders every "
            "entry insensitive")

        # End to end: open the menu and look at what the user would click.
        button = suggest_button(dialog)
        button.popup()
        clean_view.pump(0.4)
        items = [w for w in walk(button.get_popover())
                 if type(w).__name__ == 'GtkModelButton']
        assert items, 'the Suggest menu rendered no items'
        assert any(w.get_sensitive() for w in items), \
            'every entry in the Suggest menu is greyed out'
        button.popdown()
        clean_view.pump(0.2)
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_cancel_moved_to_the_bottom_left(clean_view):
    """Cancel is a dismissal, so it belongs with the responses at the bottom,
    on the left, not in the header."""
    dialog = open_rename(clean_view)
    try:
        header = [w.get_tooltip_text() for w in walk(dialog.headerbar)
                  if isinstance(w, Gtk.Button)]
        assert 'Cancel renaming' not in header, header
        bottom = [w.get_tooltip_text() for w in walk(dialog._action_bar)
                  if isinstance(w, Gtk.Button)]
        assert 'Cancel renaming' in bottom, bottom
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_the_busy_indicator_shows_and_hides(clean_view):
    """It says what the dialog is doing while work that reads a document runs,
    and it must not stay behind once that work is over."""
    dialog = open_rename(clean_view)
    try:
        assert dialog._busy_box.get_visible() is False

        dialog.set_busy('Detecting all fields')
        clean_view.pump(0.2)
        assert dialog._busy_box.get_visible() is True
        assert dialog._busy_label.get_text() == 'Detecting all fields'
        assert dialog._busy_spinner.get_spinning() is True

        dialog.clear_busy()
        clean_view.pump(0.2)
        assert dialog._busy_box.get_visible() is False
        assert dialog._busy_spinner.get_spinning() is False
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)


def test_the_detection_message_names_one_field_or_all_of_them(clean_view):
    dialog = open_rename(clean_view)
    widget = clean_view.widget('rename-widget')
    try:
        assert widget._detection_message(['country']) == 'Detecting country'
        assert widget._detection_message(
            ['country', 'sentby', 'sentto']) == 'Detecting all fields'
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.3)
