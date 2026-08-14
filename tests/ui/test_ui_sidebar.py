#!/usr/bin/python3

"""UI: the sidebar filters. Checklist section 3."""

DATE_ENTRIES = [
    'this-month', 'past-month', 'last-3-months', 'last-6-months',
    'last-12-months', '2-years', '3-years', '5-years', '10-years',
    'future', 'all-documents',
]


def date_presets(driver):
    dropdown = driver.dropdown('Date')
    model = dropdown.get_model()
    while hasattr(model, 'get_model'):
        model = model.get_model()
    return [model.get_item(position).preset for position in range(len(model))]


def test_the_date_dropdown_lists_eleven_entries(clean_view):
    """3.3: the entries the sidebar has always had, in the same order."""
    assert date_presets(clean_view) == DATE_ENTRIES


def test_a_field_filter_narrows_the_view(clean_view):
    """3.1: picking a country leaves only that country's documents."""
    clean_view.select_dropdown_value('Country', 'DE')
    displayed = clean_view.displayed()
    assert len(displayed) == 1
    assert '-DE-' in displayed[0]


def test_any_restores_the_view(clean_view):
    """3.1."""
    clean_view.select_dropdown_value('Country', 'DE')
    assert len(clean_view.displayed()) == 1
    clean_view.select_dropdown_value('Country', 'Any')
    assert len(clean_view.displayed()) == 3


def test_two_filters_narrow_together(clean_view):
    """3.7."""
    clean_view.select_dropdown_value('Country', 'ES')
    assert len(clean_view.displayed()) == 2
    clean_view.select_dropdown_value('Group', 'FIN')
    displayed = clean_view.displayed()
    assert len(displayed) == 1
    assert '-ES-FIN-' in displayed[0]


def test_a_date_filter_excludes_older_documents(clean_view):
    """3.4: the 2024 document is outside the last twelve months."""
    clean_view.select_dropdown_value('Date', 'last-12-months')
    displayed = clean_view.displayed()
    assert all(not name.startswith('2024') for name in displayed)
    assert any(name.startswith('2026') for name in displayed)


def test_all_documents_puts_everything_back(clean_view):
    """3.3."""
    clean_view.select_dropdown_value('Date', 'last-12-months')
    narrowed = len(clean_view.displayed())
    clean_view.select_dropdown_value('Date', 'all-documents')
    assert len(clean_view.displayed()) > narrowed


def test_future_hides_everything_dated_today_or_earlier(clean_view):
    """3.6."""
    clean_view.select_dropdown_value('Date', 'future')
    assert clean_view.displayed() == []


def test_the_sidebar_can_be_hidden_and_shown(miaz):
    """3.8."""
    sidebar = miaz.widget('sidebar')
    if sidebar is None:
        return
    was_visible = sidebar.get_visible()
    sidebar.set_visible(not was_visible)
    miaz.pump(0.2)
    assert sidebar.get_visible() is (not was_visible)
    sidebar.set_visible(was_visible)
    miaz.pump(0.2)
    assert sidebar.get_visible() is was_visible
