#!/usr/bin/python3

from gettext import gettext as _

from gi.repository import Adw, Gtk

PROVIDER_LABELS = {
    'claude': 'Claude (Anthropic)',
    'openai': 'OpenAI / OpenCode',
    'gemini': 'Gemini (Google)',
    'ollama': 'Ollama (local)',
}

# Prefilled model choices per provider, cheapest/lightest first. The first
# entry is used as the default when nothing is configured yet. A value already
# stored in the config that is not in this list is kept and shown as well, so
# custom models are never lost.
PROVIDER_MODELS = {
    'claude': ['claude-haiku-4-5', 'claude-sonnet-4-6', 'claude-opus-4-8'],
    'openai': ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
    'gemini': ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash'],
    'ollama': ['llama3.1:8b', 'llama3.2', 'mistral', 'qwen2.5'],
}


class AIAssistantSettings:
    def __init__(self, app, plugin, registry, log):
        self.app = app
        self.plugin = plugin
        self.registry = registry
        self.log = log
        self._dialog = None

    def present(self, parent):
        if self._dialog is None:
            self._dialog = self._build()
        self._dialog.present(parent)

    def _build(self):
        dialog = Adw.PreferencesDialog()
        dialog.set_title(_('AI Assistant'))
        dialog.set_content_width(640)
        dialog.set_content_height(580)

        top_page = Adw.PreferencesPage()
        top_page.set_title(_('General'))
        top_page.set_icon_name('preferences-system-symbolic')
        top_group = Adw.PreferencesGroup(title=_('Active provider'))

        ids = list(PROVIDER_LABELS.keys())
        labels = [PROVIDER_LABELS[i] for i in ids]
        active = self.plugin.get_config_key('active_provider') or 'ollama'
        combo = Adw.ComboRow(title=_('Provider'))
        combo.set_model(Gtk.StringList.new(labels))
        combo.set_selected(ids.index(active) if active in ids else ids.index('ollama'))
        combo.connect('notify::selected', self._on_active_changed, ids)

        top_group.add(combo)
        top_page.add(top_group)
        dialog.add(top_page)

        for pid, label in PROVIDER_LABELS.items():
            dialog.add(self._build_provider_page(pid, label))

        return dialog

    def _build_provider_page(self, pid, label):
        page = Adw.PreferencesPage(title=label, icon_name='applications-engineering-symbolic')
        cfg = self.plugin.get_config_key(f'provider_{pid}') or {}
        provider = self.registry[pid]

        group = Adw.PreferencesGroup(title=label)

        if provider.requires_api_key:
            row_key = Adw.PasswordEntryRow(title=_('API key'))
            row_key.set_text(cfg.get('api_key', ''))
            row_key.connect('changed', self._on_key_changed, pid)
            group.add(row_key)

        predefined = list(PROVIDER_MODELS.get(pid, []))
        current = (cfg.get('model') or '').strip()
        # The last entry is a sentinel that reveals a free-text row, so any
        # model can be entered even when it is not in the prefilled list.
        custom_label = _('Custom…')
        choices = predefined + [custom_label]
        custom_index = len(choices) - 1
        is_custom = bool(current) and current not in predefined

        row_model = Adw.ComboRow(title=_('Model'))
        row_model.set_model(Gtk.StringList.new(choices))

        row_custom = Adw.EntryRow(title=_('Custom model'))
        row_custom.set_show_apply_button(True)
        row_custom.set_text(current if is_custom else '')
        row_custom.set_visible(is_custom)

        if is_custom:
            selected = custom_index
        elif current in predefined:
            selected = predefined.index(current)
        else:
            selected = 0
        row_model.set_selected(selected)
        # Persist the default so the dropdown and the provider agree even
        # before the user touches it.
        if not current and selected != custom_index:
            self._store_model(pid, choices[selected])

        row_model.connect('notify::selected', self._on_model_selected,
                          pid, choices, custom_index, row_custom)
        row_custom.connect('apply', self._on_custom_model_apply, pid)
        group.add(row_model)
        group.add(row_custom)

        if pid == 'ollama':
            row_host = Adw.EntryRow(title=_('Base URL'))
            row_host.set_text(cfg.get('base_url', 'http://localhost:11434'))
            row_host.set_show_apply_button(True)
            row_host.connect('apply', self._on_field_apply, pid, 'base_url')
            group.add(row_host)

        page.add(group)
        return page

    def _on_active_changed(self, combo, _pspec, ids):
        idx = combo.get_selected()
        self.plugin.set_config_key('active_provider', ids[idx])

    def _on_key_changed(self, row, pid):
        cfg = self.plugin.get_config_key(f'provider_{pid}') or {}
        cfg['api_key'] = row.get_text()
        self.plugin.set_config_key(f'provider_{pid}', cfg)
        self.registry[pid].config = cfg

    def _on_model_selected(self, combo, _pspec, pid, choices, custom_index, row_custom):
        idx = combo.get_selected()
        if not 0 <= idx < len(choices):
            return
        if idx == custom_index:
            row_custom.set_visible(True)
            text = row_custom.get_text().strip()
            if text:
                self._store_model(pid, text)
            # otherwise wait for the user to type a value and apply it
        else:
            row_custom.set_visible(False)
            self._store_model(pid, choices[idx])

    def _on_custom_model_apply(self, row, pid):
        text = row.get_text().strip()
        if text:
            self._store_model(pid, text)

    def _store_model(self, pid, model):
        cfg = self.plugin.get_config_key(f'provider_{pid}') or {}
        cfg['model'] = model
        self.plugin.set_config_key(f'provider_{pid}', cfg)
        self.registry[pid].config = cfg

    def _on_field_apply(self, row, pid, key):
        cfg = self.plugin.get_config_key(f'provider_{pid}') or {}
        cfg[key] = row.get_text()
        self.plugin.set_config_key(f'provider_{pid}', cfg)
        self.registry[pid].config = cfg
