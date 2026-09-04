#!/usr/bin/python3

"""UI: the reusable widgets added in 0.3."""

from gi.repository import GLib
from gi.repository import Gtk

from MiAZ.frontend.desktop.widgets.chip import MiAZChip
from MiAZ.frontend.desktop.widgets.pills import MiAZFieldTable
from MiAZ.frontend.desktop.widgets.timelineview import TimelineCard


def _tags(driver):
    """Every filter tag currently in the banner, in order."""
    flowbox = driver.widget('workspace-filter-tags')
    tags = []
    child = flowbox.get_first_child()
    while child is not None:
        tags.append(child.get_child())
        child = child.get_next_sibling()
    return tags


def _tag(driver, dropdown_key):
    # The Date tag is always shown, so a tag is looked up by its field.
    for chip in _tags(driver):
        if chip.has_css_class(f'miaz-chip-{dropdown_key}'):
            return chip
    return None


def test_filter_tag_is_a_chip_and_removes_its_filter(clean_view):
    clean_view.select_dropdown_value('Group', 'FIN')
    clean_view.wait_until(lambda: _tag(clean_view, 'Group') is not None,
                          message='a filter tag appears')
    chip = _tag(clean_view, 'Group')
    assert isinstance(chip, MiAZChip)
    assert chip.has_css_class('miaz-chip')
    chip.emit('clicked')
    clean_view.wait_until(lambda: _tag(clean_view, 'Group') is None,
                          message='the tag goes away')
    assert clean_view.dropdown('Group').get_selected() == 0


def test_rename_dialog_uses_the_date_entry_widget(clean_view):
    from MiAZ.frontend.desktop.widgets.dateentry import MiAZDateEntry
    from MiAZ.frontend.desktop.widgets.rename import MiAZRenameDialog
    widget = MiAZRenameDialog(clean_view.app)
    widget.set_data('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    clean_view.pump(0.3)
    assert isinstance(widget.date_entry, MiAZDateEntry)
    assert widget.entry_date.get_text() == '20260612'
    assert widget.date_entry.validate() is True
    widget.entry_date.set_text('20261301')
    assert widget.date_entry.validate() is False
    widget.dispose()


def test_preview_sheet_toggles_from_the_headerbar(clean_view):
    button = clean_view.widget('headerbar-button-preview')
    sheet = clean_view.widget('workspace-preview-sheet')
    assert sheet.get_open() is False
    button.set_active(True)
    clean_view.pump(0.3)
    assert sheet.get_open() is True
    button.set_active(False)
    clean_view.pump(0.3)
    assert sheet.get_open() is False


def test_closing_the_sheet_untoggles_the_headerbar_button(clean_view):
    # The sheet can be dragged shut, so the button cannot be the only thing
    # that knows whether the preview is up.
    button = clean_view.widget('headerbar-button-preview')
    sheet = clean_view.widget('workspace-preview-sheet')
    button.set_active(True)
    clean_view.pump(0.3)
    sheet.set_open(False)
    clean_view.pump(0.3)
    assert button.get_active() is False


def test_preview_follows_the_selection(clean_view):
    button = clean_view.widget('headerbar-button-preview')
    button.set_active(True)
    clean_view.pump(0.3)
    clean_view.select_documents('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    preview = clean_view.widget('workspace-preview')
    clean_view.wait_until(
        lambda: preview.stack.get_visible_child_name() in ('picture', 'none'),
        message='the preview settles')
    # Sandbox documents are text files named .pdf, so there is nothing to render.
    assert preview.stack.get_visible_child_name() == 'none'
    assert preview.get_document().endswith('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    button.set_active(False)
    clean_view.pump(0.2)


def test_preview_shows_field_pills(clean_view):
    button = clean_view.widget('headerbar-button-preview')
    button.set_active(True)
    clean_view.pump(0.3)
    clean_view.select_documents('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    preview = clean_view.widget('workspace-preview')
    clean_view.wait_until(lambda: preview.pills.get_visible(), message='pills appear')
    labels = []
    child = preview.pills.get_first_child()
    while child is not None:
        labels.append(child.get_label())
        child = child.get_next_sibling()
    # Descriptions, since a pill is for reading; the key is in the tooltip.
    assert labels == ['12/06/2026', 'Spain', 'Finance', 'Bank X', 'Invoice',
                      'mortgage', 'John Doe']
    assert preview.pills.get_first_child().has_css_class('miaz-pill-Date')
    assert preview.pills.get_first_child().get_tooltip_text() == 'Date: 20260612'
    button.set_active(False)
    clean_view.pump(0.2)


def test_timeline_page_exists_and_orders_by_date(clean_view):
    stack = clean_view.workspace.get_stack()
    assert stack.get_child_by_name('workspace-timeline') is None, (
        'the timeline is a view of the Documents page, not a tab of its own')
    assert clean_view.workspace.get_view_stack().get_child_by_name('timeline') is not None
    timeline = clean_view.widget('workspace-timeline')
    clean_view.wait_until(
        lambda: timeline.sort_model.get_n_items() == len(clean_view.displayed()),
        message='the timeline follows the filtered set')
    dates = [timeline.sort_model.get_item(i).date
             for i in range(timeline.sort_model.get_n_items())]
    assert dates == sorted(dates)


def test_a_long_concept_does_not_widen_the_timeline_card(clean_view):
    """Every card asks for the same width, so the spine sits in one place.

    The headline used to wrap, which meant a card asked for its whole concept
    on one line: a document called HOURLY LEAVE RATE CORRECTION RETROACTIVE
    RECALCULATION PAYSLIPS JAN AUG 2025 made its card half as wide again as
    the one under it, and the rule down the middle stepped sideways at every
    such row.

    The width is measured rather than the ellipsize setting read, so this
    still holds if the pills or the preview change size: what matters is that
    the headline asks for less than the rest of the card, not the number the
    cap happens to be.
    """
    card = TimelineCard()
    window = Gtk.Window()
    window.set_child(card)
    try:
        widths = []
        for concept in ('RE 1', 'FM BUCH 2026',
                        'HOURLY LEAVE RATE CORRECTION RETROACTIVE '
                        'RECALCULATION PAYSLIPS JAN AUG 2025'):
            card.label_concept.set_text(concept)
            card.label_date.set_text('01/09/2025')
            card.fields.set_fields(['20250901', 'ES', 'FIN', 'BANKX', 'INV',
                                    'a-concept-of-a-fairly-usual-length',
                                    'JOHNDOE'])
            clean_view.pump(0.1)
            widths.append(card.card.measure(Gtk.Orientation.HORIZONTAL, -1))
        assert len(set(widths)) == 1, f'the concept changes the card width: {widths}'
    finally:
        window.destroy()


def test_timeline_is_single_sided_with_many_parties(clean_view):
    # Alpha has three senders, so no two-party conversation.
    timeline = clean_view.widget('workspace-timeline')
    clean_view.wait_until(lambda: timeline.sort_model.get_n_items() > 0,
                          message='timeline has items')
    assert timeline.get_split() is None


def test_timeline_splits_a_two_party_exchange(clean_view):
    clean_view.select_dropdown_value('SentBy', 'BANKX')
    timeline = clean_view.widget('workspace-timeline')
    clean_view.wait_until(lambda: timeline.get_split() == ('BANKX', 'JOHNDOE'),
                          message='two parties split the timeline')


def _timeline_rows(timeline):
    rows = 0
    child = timeline.listview.get_first_child()
    while child is not None:
        rows += 1
        child = child.get_next_sibling()
    return rows


def test_timeline_builds_nothing_while_another_page_is_shown(clean_view):
    """The page nobody is looking at must cost nothing.

    An Adw.ViewStack measures the pages it is not showing, which was enough to
    make the timeline build a row per document, each one rendering a PDF, while
    the user sat on the document list. On a real repository that froze the
    window for twelve seconds every time the filter widened.
    """
    workspace = clean_view.workspace
    timeline = clean_view.widget('workspace-timeline')
    assert workspace.get_current_view() == 'details'
    assert timeline.listview.get_model() is None
    assert _timeline_rows(timeline) == 0

    workspace.show_view('timeline')
    clean_view.wait_until(lambda: timeline.listview.get_model() is not None,
                          message='the timeline takes its model when shown')
    clean_view.wait_until(lambda: _timeline_rows(timeline) > 0,
                          message='the timeline builds rows when shown')

    # Switching away has to give the model back: an Adw.ViewStack never unmaps
    # a page it has shown once, so nothing else would.
    workspace.show_view('details')
    clean_view.pump(0.4)
    assert timeline.listview.get_model() is None
    assert _timeline_rows(timeline) == 0


def _find_widget(widget, wtype):
    if isinstance(widget, wtype):
        return widget
    child = widget.get_first_child()
    while child is not None:
        found = _find_widget(child, wtype)
        if found is not None:
            return found
        child = child.get_next_sibling()
    return None


def test_mass_rename_date_dialog_uses_the_date_entry_widget(clean_view):
    from MiAZ.backend.models import Date
    from MiAZ.frontend.desktop.widgets.dateentry import MiAZDateEntry
    clean_view.select_documents(
        '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf',
        '20260505-ES-HOU-ACME-INV-electricity-JOHNDOE.pdf')
    clean_view.service('massrename').rename_date(None, None, Date)
    clean_view.pump(0.5)
    entry = _find_widget(clean_view.widget('window'), MiAZDateEntry)
    assert entry is not None, 'the dialog carries a MiAZDateEntry'
    assert len(entry.get_text()) == 8
    # The date can be typed now, not only clicked for in the calendar.
    entry.set_sensitive(True)
    entry.set_text('20250102')
    clean_view.pump(0.3)
    assert entry.get_text() == '20250102'


def test_calendar_moves_to_a_short_month_from_a_31st(clean_view):
    """A month change must not be dropped because the day does not fit.

    Each Gtk.Calendar setter builds a date from the two fields it is not
    changing and refuses one that does not exist, so moving a calendar sitting
    on the 31st to February asked for February 31. GTK logged
    'gtk_calendar_set_month: assertion date != NULL failed', kept the old
    month, and the calendar quietly showed a date nobody asked for.
    """
    from MiAZ.frontend.desktop.services.factory import calendar_select_date
    calendar = Gtk.Calendar()
    calendar_select_date(calendar, 2026, 1, 31)
    assert calendar.get_date().format('%Y-%m-%d') == '2026-01-31'
    calendar_select_date(calendar, 2026, 2, 15)
    assert calendar.get_date().format('%Y-%m-%d') == '2026-02-15'
    # The leap day is the same trap one setter along: February 29 into a year
    # that has no February 29.
    calendar_select_date(calendar, 2024, 2, 29)
    assert calendar.get_date().format('%Y-%m-%d') == '2024-02-29'
    calendar_select_date(calendar, 2025, 3, 1)
    assert calendar.get_date().format('%Y-%m-%d') == '2025-03-01'


def test_preview_leads_with_the_concept_then_the_date(clean_view):
    """What names a document is its concept, so that is the heading.

    The filename is what the document is filed as, not what it is, and on a
    narrow screen there is room for one line that matters.
    """
    button = clean_view.widget('headerbar-button-preview')
    button.set_active(True)
    clean_view.pump(0.3)
    clean_view.select_documents('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    preview = clean_view.widget('workspace-preview')
    clean_view.wait_until(lambda: preview.label_title.get_text() != '',
                          message='the preview names the document')
    assert preview.label_title.get_text() == 'mortgage'
    assert preview.label_subtitle.get_text() == '12/06/2026'
    button.set_active(False)
    clean_view.pump(0.2)


def test_preview_zoom_buttons_change_the_page_width(clean_view):
    from MiAZ.frontend.desktop.widgets.docpreview import ZOOM_STEPS
    preview = clean_view.widget('workspace-preview')
    start = preview.get_zoom_width()
    assert start in ZOOM_STEPS

    preview.zoom_in()
    clean_view.pump(0.2)
    assert preview.get_zoom_width() > start

    preview.zoom_out()
    clean_view.pump(0.2)
    assert preview.get_zoom_width() == start

    # The ends clamp rather than running off the list.
    for _ in range(len(ZOOM_STEPS) + 3):
        preview.zoom_in()
    assert preview.get_zoom_width() == ZOOM_STEPS[-1]
    assert preview.button_zoom_in.get_sensitive() is False
    for _ in range(len(ZOOM_STEPS) + 3):
        preview.zoom_out()
    assert preview.get_zoom_width() == ZOOM_STEPS[0]
    assert preview.button_zoom_out.get_sensitive() is False
    assert preview.button_zoom_in.get_sensitive() is True
    preview._set_zoom(ZOOM_STEPS.index(start))


def _visible_widget(driver, name):
    widget = driver.widget(name)
    return widget is not None and widget.get_visible()


def test_narrow_collapses_the_headerbar(clean_view):
    """Narrow, the header bar has to fit a phone.

    The window could not be made narrower than 805px, so the breakpoint that
    rearranges MiAZ could never be reached. What costs the width is the page
    switcher, the window controls, the word on the Review toggle and the four
    per-selection buttons, so narrow mode takes all four out.
    """
    mainwindow = clean_view.widget('mainwindow')
    headerbar = clean_view.widget('headerbar')
    clean_view.select_documents('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')

    assert mainwindow.get_property('narrow') is False
    assert headerbar.get_title_widget() is not None
    assert headerbar.get_show_end_title_buttons() is True
    assert _visible_widget(clean_view, 'headerbar-button-rename') is True
    assert _visible_widget(clean_view, 'headerbar-button-actions') is False

    mainwindow.set_property('narrow', True)
    clean_view.pump(0.3)
    try:
        assert headerbar.get_show_end_title_buttons() is False
        assert headerbar.get_show_start_title_buttons() is False
        # The four buttons become one menu holding the same actions.
        assert _visible_widget(clean_view, 'headerbar-button-rename') is False
        assert _visible_widget(clean_view, 'headerbar-button-delete') is False
        actions = clean_view.widget('headerbar-button-actions')
        assert actions.get_visible() is True
        assert actions.get_menu_model().get_n_items() == 3
    finally:
        mainwindow.set_property('narrow', False)
        clean_view.pump(0.3)
    assert _visible_widget(clean_view, 'headerbar-button-rename') is True
    assert _visible_widget(clean_view, 'headerbar-button-actions') is False
    assert headerbar.get_title_widget() is not None
    assert headerbar.get_show_end_title_buttons() is True


def test_workspace_stack_does_not_size_to_its_widest_page(clean_view):
    """One wide page must not set the floor for the whole window.

    An Adw.ViewStack is homogeneous by default, so it asks every page how wide
    it wants to be and takes the largest. A plugin page wanting 519px made a
    narrow window impossible even though it was not on screen.
    """
    stack = clean_view.workspace.get_stack()
    assert stack.get_hhomogeneous() is False
    assert stack.get_vhomogeneous() is False


def _grid_cells(grid):
    """Count the document cells, not every child widget.

    Gtk.GridView keeps internal children of its own (the rubberband, for one),
    so counting direct children answered 1 for an empty grid.
    """
    from MiAZ.frontend.desktop.widgets.gridview import GridCell

    def walk(widget):
        found = 0
        child = widget.get_first_child()
        while child is not None:
            found += 1 if isinstance(child, GridCell) else walk(child)
            child = child.get_next_sibling()
        return found

    return walk(grid.gridview)


def _first_grid_cell(grid):
    from MiAZ.frontend.desktop.widgets.gridview import GridCell

    def walk(widget):
        child = widget.get_first_child()
        while child is not None:
            if isinstance(child, GridCell):
                return child
            found = walk(child)
            if found is not None:
                return found
            child = child.get_next_sibling()
        return None

    return walk(grid.gridview)


def test_grid_cell_carries_the_seven_fields(clean_view):
    """A cell is the whole filename, read: the country and the date above the
    page with the group, the purpose and the sender under them, then the
    concept below. Descriptions on the cell, keys in the tooltip, and the
    recipient only there."""
    workspace = clean_view.workspace
    grid = clean_view.widget('workspace-grid')
    workspace.show_view('grid')
    clean_view.wait_until(lambda: _grid_cells(grid) > 0,
                          message='the grid builds cells when shown')
    clean_view.select_dropdown_value('SentBy', 'BANKX')
    clean_view.wait_until(
        lambda: clean_view.displayed() == [
            '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf'],
        message='one document left')
    clean_view.wait_until(lambda: _grid_cells(grid) == 1,
                          message='one cell left')

    cell = _first_grid_cell(grid)
    assert cell.label_group.get_text() == 'Finance'
    assert cell.label_sentby.get_text() == 'Invoice sent by Bank X'
    assert cell.label_concept.get_text() == 'mortgage'
    assert not hasattr(cell, 'label_sentto'), (
        'the recipient is in the tooltip, not a line of its own')
    assert '2026' in cell.label_date.get_text()
    assert cell.flag.get_visible(), 'the country is a flag, not a code'
    assert cell.label_group.get_tooltip_text() == 'Group: FIN'
    assert cell.label_sentby.get_tooltip_text() == (
        'Purpose: INV\nSent by: BANKX\nSent to: JOHNDOE')
    for label in (cell.label_group, cell.label_sentby, cell.label_concept):
        assert 'dim-label' not in label.get_css_classes(), (
            'the fields that name the document are not dimmed')

    workspace.show_view('details')
    clean_view.pump(0.3)


def test_grid_page_shows_documents_as_pages(clean_view):
    from MiAZ.frontend.desktop.widgets.gridview import ICON_SIZES
    workspace = clean_view.workspace
    assert workspace.get_stack().get_child_by_name('workspace-grid') is None, (
        'the grid is a view of the Documents page, not a tab of its own')
    assert workspace.get_view_stack().get_child_by_name('grid') is not None
    grid = clean_view.widget('workspace-grid')

    # Hidden, it costs nothing: no model, no cells, no page rendered.
    assert grid.gridview.get_model() is None
    assert _grid_cells(grid) == 0

    workspace.show_view('grid')
    clean_view.wait_until(lambda: _grid_cells(grid) > 0,
                          message='the grid builds cells when shown')
    assert grid.get_icon_size() == 256, 'the default page is 256px'

    cell = grid.gridview.get_first_child()
    while cell is not None and not hasattr(cell, 'get_child'):
        cell = cell.get_next_sibling()
    workspace.show_view('details')
    clean_view.pump(0.4)
    assert grid.gridview.get_model() is None
    assert _grid_cells(grid) == 0
    assert ICON_SIZES[0] < 256 < ICON_SIZES[-1], 'it goes smaller and larger'


def test_grid_size_buttons_clamp_and_resize(clean_view):
    from MiAZ.frontend.desktop.widgets.gridview import ICON_SIZES
    grid = clean_view.widget('workspace-grid')
    start = grid.get_icon_size()

    grid.bigger()
    clean_view.pump(0.2)
    assert grid.get_icon_size() > start

    grid.smaller()
    clean_view.pump(0.2)
    assert grid.get_icon_size() == start

    for _ in range(len(ICON_SIZES) + 3):
        grid.bigger()
    assert grid.get_icon_size() == ICON_SIZES[-1]
    assert grid.button_bigger.get_sensitive() is False
    for _ in range(len(ICON_SIZES) + 3):
        grid.smaller()
    assert grid.get_icon_size() == ICON_SIZES[0]
    assert grid.button_smaller.get_sensitive() is False
    assert grid.button_bigger.get_sensitive() is True
    grid.set_icon_size(ICON_SIZES.index(start))


def test_grid_columns_follow_the_icon_size(clean_view):
    """Gtk.GridView keeps a buffer of about 32 rows, so cells built is 32 times
    max-columns however small the window is. A fixed 24 meant 769 cells and 769
    pages queued to render for a screen holding a dozen."""
    grid = clean_view.widget('workspace-grid')
    start = grid.get_icon_size()
    columns = {}
    for level, size in enumerate([128, 256, 512]):
        from MiAZ.frontend.desktop.widgets.gridview import ICON_SIZES
        grid.set_icon_size(ICON_SIZES.index(size))
        clean_view.pump(0.2)
        columns[size] = grid.gridview.get_max_columns()
    assert columns[512] < columns[256] <= columns[128]
    assert columns[128] <= 12, 'never more than a real screen could show'
    from MiAZ.frontend.desktop.widgets.gridview import ICON_SIZES
    grid.set_icon_size(ICON_SIZES.index(start))


def test_rename_preview_is_a_bottom_sheet_raised_by_the_preview_button(clean_view):
    """The fields keep the width of the dialog until the page is asked for.

    The preview used to sit to the left of the seven fields and read the
    document as the dialog opened, so every rename paid for a rendered page
    whether or not anyone wanted to look at one.
    """
    clean_view.select_documents('20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')
    clean_view.service('actions').document_rename()
    clean_view.wait_until(lambda: clean_view.widget('dialog-rename') is not None,
                          message='the rename dialog opens')
    dialog = clean_view.widget('dialog-rename')
    sheet = clean_view.widget('rename-preview-sheet')
    preview = clean_view.widget('rename-preview')
    button = clean_view.widget('rename-button-preview')
    try:
        assert sheet.get_open() is False, 'the sheet starts closed'
        assert button.get_active() is False
        assert preview.get_document() is None, 'nothing is read until it is asked for'

        button.set_active(True)
        clean_view.pump(0.4)
        assert sheet.get_open() is True
        clean_view.wait_until(lambda: preview.get_document() is not None,
                              message='the document reaches the preview')
        assert preview.get_document().endswith(
            '20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf')

        # Dragging the sheet shut has to release the button too.
        sheet.set_open(False)
        clean_view.pump(0.4)
        assert button.get_active() is False
    finally:
        dialog.emit('response', 'cancel')
        clean_view.pump(0.4)


def test_view_toolbar_switches_the_documents_page(clean_view):
    """Details, grid and timeline are one page with a toolbar, not three tabs.

    They are three shapes of the same documents under the same filters, and a
    tab says "somewhere else" when none of them is.
    """
    workspace = clean_view.workspace
    buttons = clean_view.widget('workspace-view-buttons')
    assert buttons is not None, 'the Documents page carries a view toolbar'
    assert workspace.get_current_view() == 'details'

    # Only Documents, Browser and whatever plugins add are tabs.
    stack = workspace.get_stack()
    tabs = set()
    child = stack.get_first_child()
    while child is not None:
        page = stack.get_page(child)
        if page is not None:
            tabs.add(page.get_name())
        child = child.get_next_sibling()
    assert 'workspace-default' in tabs
    assert 'workspace-grid' not in tabs
    assert 'workspace-timeline' not in tabs

    for name in ('grid', 'timeline', 'details'):
        workspace.show_view(name)
        clean_view.pump(0.3)
        assert workspace.get_current_view() == name
        assert workspace._view_buttons[name].get_active() is True


def test_grid_shares_the_selection_with_the_document_list(clean_view):
    """Selecting in the grid is selecting in the workspace.

    The grid had a selection model of its own, so a document picked there was
    invisible to the header bar buttons, to the plugins and to the preview.
    """
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')
    grid = clean_view.widget('workspace-grid')
    workspace.show_view('grid')
    clean_view.wait_until(lambda: grid.gridview.get_model() is not None,
                          message='the grid takes its model')
    assert grid.gridview.get_model() is view.get_selection(), (
        'the grid must use the document list selection, not a copy of it')

    model = view.get_model_filter()
    target = None
    for position in range(len(model)):
        if model.get_item(position).id.startswith('20260612'):
            target = position
            break
    assert target is not None
    grid.gridview.get_model().unselect_all()
    grid.gridview.get_model().select_item(target, True)
    clean_view.pump(0.5)
    selected = [item.id for item in workspace.get_selected_items()]
    assert selected == ['20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf']
    workspace.show_view('details')
    clean_view.pump(0.3)


def test_grid_has_the_same_context_menu_as_the_document_list(clean_view):
    grid = clean_view.widget('workspace-grid')
    assert grid._context_popover is not None
    grid._on_right_click(None, 1, 10, 10)
    clean_view.pump(0.3)
    assert grid._context_popover.get_menu_model() is clean_view.widget(
        'workspace-menu-selection'), 'the grid shows the workspace selection menu'
    grid._context_popover.popdown()
    clean_view.pump(0.2)


def test_timeline_fields_say_descriptions_and_keep_the_key_in_the_tooltip(clean_view):
    """A card is for reading, so it says Spain, not ES, one field per row
    with its name in front. The key is one hover away, and the Filenames
    view has all of them at once."""
    workspace = clean_view.workspace
    timeline = clean_view.widget('workspace-timeline')
    workspace.show_view('timeline')
    clean_view.wait_until(lambda: _timeline_rows(timeline) > 0,
                          message='the timeline builds rows when shown')
    row = timeline.listview.get_first_child()
    while row is not None and _find_widget(row, MiAZFieldTable) is None:
        row = row.get_next_sibling()
    table = _find_widget(row, MiAZFieldTable)
    keys = [key.get_text() for key in table.keys]
    assert keys == ['Date:', 'Country:', 'Group:', 'Sent by:',
                    'Purpose:', 'Concept:', 'Sent to:']
    texts = [value.get_text() for value in table.values]
    assert 'ES' not in texts and 'DE' not in texts, texts
    assert 'Spain' in texts or 'Germany' in texts, texts
    assert table.values[1].get_tooltip_text() in ('Country: ES', 'Country: DE')
    workspace.show_view('details')
    clean_view.pump(0.3)


def test_filenames_view_shows_raw_names_and_shares_the_selection(clean_view):
    """The keys have a view of their own: the filename as it is on disk."""
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')
    names = clean_view.widget('workspace-filenames')
    assert names.listview.get_model() is None, 'nothing is built while hidden'

    workspace.show_view('filenames')
    clean_view.wait_until(lambda: names.listview.get_model() is not None,
                          message='the view takes its model when shown')
    assert names.listview.get_model() is view.get_selection()
    clean_view.wait_until(lambda: names.listview.get_first_child() is not None,
                          message='rows are built')
    row = names.listview.get_first_child().get_first_child()
    text = row.label.get_text()
    assert text in clean_view.displayed(), 'the row is the filename itself'
    assert '-' in text and text.endswith('.pdf')

    model = view.get_model_filter()
    target = next(p for p in range(len(model))
                  if model.get_item(p).id.startswith('20260612'))
    names.listview.get_model().unselect_all()
    names.listview.get_model().select_item(target, True)
    clean_view.pump(0.5)
    selected = [item.id for item in workspace.get_selected_items()]
    assert selected == ['20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf']

    names._on_right_click(None, 1, 10, 10)
    clean_view.pump(0.3)
    assert names._context_popover.get_menu_model() is clean_view.widget(
        'workspace-menu-selection')
    names._context_popover.popdown()
    workspace.show_view('details')
    clean_view.pump(0.3)
    assert names.listview.get_model() is None, 'hidden again, no model'


def test_filenames_view_sorts_by_any_field(clean_view):
    """The header sorts the documents, not a copy of them.

    Sorting is one thing in this workspace: the views are shapes of the same
    ordered set, so the header drives the document list's own sorter and the
    Details view agrees with what the Filenames view shows.
    """
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')
    names = clean_view.widget('workspace-filenames')
    workspace.show_view('filenames')
    clean_view.wait_until(lambda: names.listview.get_model() is not None,
                          message='the view takes its model when shown')

    names._header_buttons['Concept'].emit('clicked')
    clean_view.pump(0.4)
    concepts = [name.split('-')[5] for name in clean_view.displayed()]
    assert concepts == sorted(concepts), concepts
    sorter = view.cv.get_sorter()
    assert sorter.get_primary_sort_column() is view.column_subtitle
    assert names._header_arrows['Concept'].get_visible()
    assert names._header_buttons['Concept'].has_css_class('miaz-header-active')

    names._header_buttons['Concept'].emit('clicked')
    clean_view.pump(0.4)
    reversed_concepts = [name.split('-')[5] for name in clean_view.displayed()]
    assert reversed_concepts == sorted(concepts, reverse=True), reversed_concepts

    names._header_buttons['Date'].emit('clicked')
    clean_view.pump(0.4)
    dates = [name.split('-')[0] for name in clean_view.displayed()]
    assert dates == sorted(dates), dates
    assert not names._header_arrows['Concept'].get_visible()
    assert names._header_arrows['Date'].get_visible()

    # The extension is not one of the seven fields, but the row ends with it.
    names._header_buttons['Extension'].emit('clicked')
    clean_view.pump(0.4)
    assert sorter.get_primary_sort_column() is view.column_extension
    assert names._header_arrows['Extension'].get_visible()
    assert not names._header_arrows['Date'].get_visible()

    # Sorting from the document list moves the header, since it is one sorter.
    view.cv.sort_by_column(view.column_sentby, Gtk.SortType.ASCENDING)
    clean_view.pump(0.4)
    assert names._header_arrows['SentBy'].get_visible()
    assert not names._header_arrows['Extension'].get_visible()

    workspace.show_view('details')
    clean_view.pump(0.3)


def _in_box(box, widget):
    child = box.get_first_child()
    while child is not None:
        if child is widget:
            return True
        child = child.get_next_sibling()
    return False


def test_document_actions_live_on_the_workspace_toolbar(clean_view):
    """What acts on documents belongs with the documents.

    The buttons were in the header bar, away from the list they act on, and
    they were most of what stopped the window fitting a narrow screen.
    """
    center = clean_view.widget('workspace-toolbar-center')
    assert center is not None
    for key in ('headerbar-button-add', 'headerbar-button-preview',
                'headerbar-button-actions', 'headerbar-right-box'):
        widget = clean_view.widget(key)
        assert widget is not None, key
        assert _in_box(center, widget), f'{key} should sit on the workspace toolbar'
    # Plugins add their buttons to this box, so they travel with it.
    assert clean_view.widget('headerbar-right-box').get_parent() is center


def test_toolbar_end_follows_the_view(clean_view):
    """Columns belong to the table, page size to the grid."""
    workspace = clean_view.workspace
    columns = clean_view.widget('workspace-button-columns')
    grid = clean_view.widget('workspace-grid')
    controls = workspace._grid_controls

    workspace.show_view('details')
    clean_view.pump(0.3)
    assert columns.get_visible() is True
    assert controls.get_visible() is False

    workspace.show_view('grid')
    clean_view.pump(0.3)
    assert columns.get_visible() is False
    assert controls.get_visible() is True
    assert _in_box(clean_view.widget('workspace-toolbar-end'), controls)

    workspace.show_view('timeline')
    clean_view.pump(0.3)
    assert columns.get_visible() is False
    assert controls.get_visible() is False
    workspace.show_view('details')
    clean_view.pump(0.3)


def test_view_menu_toggles_column_visibility(clean_view):
    """The View menu says what the table is actually doing."""
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')
    action = workspace._column_actions['column_purpose']
    column = view.column_purpose

    assert action.get_state().get_boolean() == column.get_visible()
    was = column.get_visible()
    action.change_state(GLib.Variant.new_boolean(not was))
    clean_view.pump(0.3)
    assert column.get_visible() is (not was)
    assert action.get_state().get_boolean() is (not was)

    action.change_state(GLib.Variant.new_boolean(was))
    clean_view.pump(0.3)
    assert column.get_visible() is was


def test_preview_hide_button_closes_the_sheet(clean_view):
    button = clean_view.widget('headerbar-button-preview')
    sheet = clean_view.widget('workspace-preview-sheet')
    preview = clean_view.widget('workspace-preview')
    button.set_active(True)
    clean_view.pump(0.3)
    assert sheet.get_open() is True
    preview.button_hide.emit('clicked')
    clean_view.pump(0.4)
    assert sheet.get_open() is False
    assert button.get_active() is False


def test_preview_panel_grows_with_the_page(clean_view):
    """Zooming in has to make room for the bigger page, or it cannot be seen."""
    preview = clean_view.widget('workspace-preview')
    button = clean_view.widget('headerbar-button-preview')
    button.set_active(True)
    clean_view.pump(0.3)
    start_zoom = preview.get_zoom_width()
    small = preview.get_size_request().height
    preview.zoom_in()
    clean_view.pump(0.3)
    assert preview.get_size_request().height > small
    preview.zoom_out()
    clean_view.pump(0.3)
    assert preview.get_size_request().height == small
    assert preview.get_zoom_width() == start_zoom
    button.set_active(False)
    clean_view.pump(0.2)


def test_showing_an_explicit_list_of_documents(clean_view):
    """A report that names documents has to be able to put them on screen.

    The documents a health check finds are usually the broken ones, which the
    ordinary view hides: they are pending, or their date does not parse. Both
    checks are lifted while an explicit list is being shown.
    """
    workspace = clean_view.workspace
    everything = clean_view.displayed()
    assert len(everything) > 1, 'need more than one document to narrow to one'
    wanted = everything[0]

    workspace.show_documents([wanted], label='A health check')
    clean_view.wait_until(lambda: clean_view.displayed() == [wanted],
                          message='the view narrows to the named document')
    assert workspace.get_shown_documents() == frozenset({wanted})
    assert workspace.get_current_view() == 'details'

    # It is a filter like any other: visible in the bar, removable there.
    tag = _tag(clean_view, 'Concept')
    assert tag is not None, 'the restriction shows as a tag'
    assert 'A health check' in tag.label.get_text()

    tag.emit('clicked')
    clean_view.wait_until(lambda: len(clean_view.displayed()) == len(everything),
                          message='removing the tag brings everything back')
    assert workspace.get_shown_documents() is None


def test_clearing_filters_drops_the_explicit_list(clean_view):
    """Clear filters after a Doctor "Show" used to leave the workspace empty.

    The explicit list survived the reset, and the date dropdown went back to
    its first preset, which rarely holds a document. Both are filters, so
    clearing them has to bring the ordinary documents back.
    """
    workspace = clean_view.workspace
    sidebar = clean_view.widget('sidebar')
    # The oldest document: outside every recent preset, so the list is the
    # only reason it is on screen.
    oldest = '20240101-DE-ADM-CITY-NTF-permit-JOHNDOE.pdf'
    assert oldest in clean_view.displayed()
    workspace.show_documents([oldest], label='A health check')
    clean_view.wait_until(lambda: clean_view.displayed() == [oldest],
                          message='the view narrows to the named document')

    sidebar.clear_filters()
    clean_view.wait_until(
        lambda: clean_view.displayed() and oldest not in clean_view.displayed(),
        message='clearing filters shows what the date preset holds')
    assert workspace.get_shown_documents() is None
    assert _tag(clean_view, 'Concept') is None, 'the "Showing" tag is gone'
    preset = clean_view.dropdown('Date').get_selected_item().preset
    assert preset != 'this-month', 'moved off the empty first preset'


def test_showing_documents_the_ordinary_view_hides(clean_view):
    """The sandbox keeps one document whose sender the configuration lacks."""
    workspace = clean_view.workspace
    hidden = '20260401-ES-FIN-STRANGER-INV-unknown-JOHNDOE.pdf'
    assert hidden not in clean_view.displayed(), 'it is pending, so it is hidden'

    workspace.show_documents([hidden], label='Pending')
    clean_view.wait_until(lambda: clean_view.displayed() == [hidden],
                          message='a pending document can still be shown')
    workspace.clear_documents()
    clean_view.wait_until(lambda: hidden not in clean_view.displayed(),
                          message='and hidden again afterwards')


def test_review_toggle_sits_next_to_the_view_buttons(clean_view):
    """Review chooses which documents are on screen, like the view buttons do."""
    start = clean_view.widget('workspace-toolbar-start')
    review = clean_view.widget('workspace-togglebutton-pending-docs')
    views = clean_view.widget('workspace-view-buttons')
    assert start is not None
    assert review.get_parent() is start
    assert views.get_parent() is start
    assert views.get_next_sibling() is review, 'Review comes right after the views'


def _bubbles(conversation):
    count = 0
    child = conversation.thread.get_first_child()
    while child is not None:
        count += 1
        child = child.get_next_sibling()
    return count


def test_conversation_view_groups_by_concept_and_reads_as_an_exchange(clean_view):
    workspace = clean_view.workspace
    view = clean_view.widget('workspace-view')
    conversation = clean_view.widget('workspace-conversation')
    assert workspace.get_view_stack().get_child_by_name('conversation') is conversation

    # Hidden, it has built nothing.
    assert conversation.get_conversations() == []
    assert _bubbles(conversation) == 0

    workspace.show_view('conversation')
    clean_view.pump(0.5)
    # The sandbox holds one document per concept, so nothing is an exchange
    # until single documents are let in.
    assert conversation.get_conversations() == []
    conversation.check_exchanges.set_active(False)
    clean_view.pump(0.5)
    titles = [c.title for c in conversation.get_conversations()]
    assert titles == ['mortgage', 'electricity', 'permit'], 'newest activity first'
    assert conversation.get_owner() == 'JOHNDOE', 'the party on most documents'
    assert conversation.get_open().title == 'mortgage'
    assert _bubbles(conversation) == 1

    # Clicking a bubble selects the document in the workspace.
    bubble = conversation.thread.get_first_child()
    assert bubble.has_css_class('miaz-bubble-in'), 'the bank sent it, so it is incoming'

    # The sandbox "PDF" is a text file, so there is no page to render: the
    # bubble says what the file is instead of leaving a hole.
    clean_view.wait_until(lambda: bubble.badge.get_visible(),
                          message='the file type badge stands in for the page')
    assert bubble.badge.label.get_text() == 'PDF'
    assert not bubble.thumbnail.get_visible()
    item = conversation.get_open().messages[0].payload
    conversation._select(item)
    clean_view.pump(0.4)
    selected = [i.id for i in workspace.get_selected_items()]
    assert selected == ['20260612-ES-FIN-BANKX-INV-mortgage-JOHNDOE.pdf']

    # Opening another conversation replaces the bubbles.
    conversation.list_selection.set_selected(2)
    clean_view.pump(0.3)
    assert conversation.get_open().title == 'permit'
    assert _bubbles(conversation) == 1

    conversation.check_exchanges.set_active(True)
    workspace.show_view('details')
    clean_view.pump(0.3)


def test_a_view_can_be_added_and_taken_away(clean_view):
    """A plugin gets the same deal the built-in views have: a toggle on the
    toolbar, a page in the stack, and no model while it is not on screen."""
    workspace = clean_view.workspace
    stack = workspace.get_view_stack()
    built_in = workspace.get_views()
    assert 'details' in built_in and 'timeline' in built_in

    class Probe(Gtk.Box):
        def __init__(self):
            super().__init__()
            self.active = None

        def set_active(self, active):
            self.active = active

    probe = Probe()
    workspace.add_view('probe', 'system-users-symbolic', 'Probe', probe)
    assert workspace.get_views()[-1] == 'probe'
    assert stack.get_child_by_name('probe') is probe

    workspace.show_view('probe')
    clean_view.pump(0.3)
    assert stack.get_visible_child_name() == 'probe'
    assert probe.active is True

    workspace.show_view('details')
    clean_view.pump(0.3)
    assert probe.active is False

    workspace.show_view('probe')
    clean_view.pump(0.3)
    workspace.remove_view('probe')
    clean_view.pump(0.3)
    assert 'probe' not in workspace.get_views()
    assert stack.get_child_by_name('probe') is None
    assert stack.get_visible_child_name() == 'details'
