# File: vocabulary.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: The currencies a repository uses, as a MiAZ vocabulary

import os
from gettext import gettext as _

from MiAZ.backend.config import MiAZConfig
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.models import MiAZModel
from MiAZ.frontend.desktop.widgets.columnview import MiAZColumnViewSelector
from MiAZ.frontend.desktop.widgets.configview import MiAZConfigView

from oikos.money import CURRENCIES, DEFAULT_CURRENCY


class Currency(MiAZModel):
    __gtype_name__ = 'MiAZOikosCurrency'
    __title__ = _('Currency')
    __title_plural__ = _('Currencies')
    __config_name__ = 'currency'
    __config_name_available__ = 'currency'
    __config_name_used__ = 'currency'


CONFIG_NAME = Currency.__config_name__


class MiAZConfigCurrency(MiAZConfig):
    """Available: every ISO currency the plugin knows. Used: the enabled ones."""

    def __init__(self, app, plugin):
        config_dir = plugin.get_config_dir()
        super().__init__(
            app=app,
            log=MiAZLog('MiAZ.Config.Currency'),
            config_for=CONFIG_NAME,
            used=os.path.join(config_dir, f'{CONFIG_NAME}-used.json'),
            available=os.path.join(config_dir, f'{CONFIG_NAME}-available.json'),
            default=plugin.get_config_file_default_available_data(),
            model=Currency,
            must_copy=False)

    def ensure_used(self, code=DEFAULT_CURRENCY):
        """Make sure a currency can be chosen, enabling it if it is not."""
        title = CURRENCIES.get(code, code)
        if not self.exists_available(code):
            self.add_available(code, title)
        if not self.exists_used(code):
            self.add_used(code, title)


def currency_label(code, used):
    """EUR · Euro, or the bare code when the repository has no name for it."""
    name = used.get(code) if isinstance(used, dict) else None
    return f'{code} · {name}' if name and name != code else code


class MiAZColumnViewCurrency(MiAZColumnViewSelector):
    __gtype_name__ = 'MiAZOikosColumnViewCurrency'

    def __init__(self, app, available=True):
        super().__init__(app, Currency)
        self.cv.append_column(self.column_id)
        self.column_id.set_title(_('Code'))
        self.cv.append_column(self.column_title)
        if available:
            title = _('{title} available').format(title=Currency.__title_plural__)
        else:
            title = _('{title} enabled').format(title=Currency.__title_plural__)
        self.column_title.set_title(title)


class MiAZCurrencyView(MiAZConfigView):
    """The currencies, in Repository Settings > Metadata."""
    __gtype_name__ = 'MiAZOikosCurrencyView'

    def __init__(self, app, config):
        self.config = config
        super().__init__(app, config_name=CONFIG_NAME, custom_config=config)

    def _setup_view_finish(self):
        self.viewAv = MiAZColumnViewCurrency(self.app)
        self._add_columnview_available(self.viewAv)
        self.viewSl = MiAZColumnViewCurrency(self.app, available=False)
        self._add_columnview_used(self.viewSl)
        self._add_config_menubutton(self.config.config_for)
        self.update_views()
