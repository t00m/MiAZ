#!/usr/bin/python3

"""Who fills the sidebar filter dropdowns, and how often.

The sidebar owns the 'ws-dropdowns' dictionary and refills it on every
repository switch. Anything else that fills the same five widgets is doing the
work twice.

The counter is installed at import time on purpose. pytest imports every test
module during collection, before the session scoped application is built, which
is the only way to see what startup did.
"""

from collections import Counter

import pytest

from MiAZ.frontend.desktop.services.actions import MiAZActions
from MiAZ.frontend.desktop.services.workflow import MiAZWorkflow

FILTER_TYPES = ('Country', 'Group', 'SentBy', 'Purpose', 'SentTo')

# (item type name, the dropdown widget) for every call since import.
POPULATED = []

# A copy of the list taken when the first switch_finish returns, which is the
# call that builds the workspace page and emits 'repository-switch-finished'.
# Both startup fills happen inside it. Snapshotting there rather than in a
# fixture is what makes the count independent of test order: every other file
# switches repositories, and each switch appends more entries to POPULATED.
STARTUP = []

_original_populate = MiAZActions.dropdown_populate
_original_switch_finish = MiAZWorkflow.switch_finish


def _counting_populate(self, config, dropdown, item_type, *args, **kwargs):
    POPULATED.append((item_type.__gtype_name__, dropdown))
    return _original_populate(self, config, dropdown, item_type, *args, **kwargs)


def _snapshotting_switch_finish(self, *args, **kwargs):
    result = _original_switch_finish(self, *args, **kwargs)
    if not STARTUP:
        STARTUP.append(list(POPULATED))
    return result


MiAZActions.dropdown_populate = _counting_populate
MiAZWorkflow.switch_finish = _snapshotting_switch_finish


@pytest.fixture(scope='module')
def startup_fills(miaz):
    """How often each sidebar filter dropdown was filled during startup."""
    assert STARTUP, 'the first switch_finish never ran'
    sidebar = {id(widget): name
               for name, widget in miaz.widget('ws-dropdowns').items()}
    return Counter(name for name, dropdown in STARTUP[0]
                   if id(dropdown) in sidebar)


def test_startup_fills_each_sidebar_filter_dropdown_once(startup_fills):
    assert startup_fills == Counter(dict.fromkeys(FILTER_TYPES, 1)), (
        f'startup filled the sidebar dropdowns {dict(startup_fills)} times')


def test_the_sidebar_filter_dropdowns_offer_their_values(miaz, startup_fills):
    """The fill that remains has to be the one that produces usable content."""
    dropdowns = miaz.widget('ws-dropdowns')
    for name in FILTER_TYPES:
        model = dropdowns[name].get_model()
        assert model.get_n_items() > 0, f'{name} is empty'
        assert model.get_item(0).id == 'Any', f'{name} does not start on Any'


def test_a_vocabulary_change_does_not_refill_the_sidebar_dropdowns(miaz,
                                                                   clean_view):
    """A 'used-updated' already ends in _update_dropdowns_after_filter, which
    rebuilds the same models from the filter. Filling them from the config on
    the way there is work that gets thrown away."""
    sidebar = {id(widget) for widget in miaz.widget('ws-dropdowns').values()}
    before = len(POPULATED)

    config = miaz.service('repo').config['Country']
    config.emit('used-updated', ['ES'])
    miaz.pump(1.5)

    refills = [name for name, dropdown in POPULATED[before:]
               if id(dropdown) in sidebar]
    assert refills == [], f'refilled {refills} from the config'


def test_a_vocabulary_change_leaves_the_country_dropdown_usable(miaz,
                                                               clean_view):
    """The guard for the test above: dropping the config fill must not leave
    the dropdown without the values the visible documents use."""
    config = miaz.service('repo').config['Country']
    config.emit('used-updated', ['ES'])
    miaz.pump(1.5)

    model = miaz.widget('ws-dropdowns')['Country'].get_model()
    offered = {model.get_item(pos).id for pos in range(model.get_n_items())}
    shown = {miaz.widget('workspace-view').get_model_filter()
             .get_item(pos).country
             for pos in range(len(miaz.widget('workspace-view')
                                  .get_model_filter()))}
    assert 'Any' in offered
    assert shown <= offered, f'{shown - offered} is displayed but not offered'
