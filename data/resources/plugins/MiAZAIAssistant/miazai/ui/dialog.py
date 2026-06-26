#!/usr/bin/python3

import pathlib
import threading
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk


def inject_suggest_button(app, registry, repository, util, log):
    actions = app.get_service('actions')
    handler_id = actions.connect(
        'rename-dialog-built',
        lambda _src, dialog, rename_widget: _add_button(
            app, dialog, rename_widget, registry, repository, util, log),
    )
    app.add_widget('miazai-rename-handler', (actions, handler_id))


def remove_suggest_button(app):
    pair = app.get_widget('miazai-rename-handler')
    if pair is not None:
        obj, handler_id = pair
        try:
            obj.disconnect(handler_id)
        except Exception:
            pass


def _add_button(app, dialog, rename_widget, registry, repository, util, log):
    btn = Adw.SplitButton(label=_('Suggest with AI'))
    btn.add_css_class('suggested-action')
    btn.set_tooltip_text(_('Ask AI to propose filename fields'))
    btn.connect('clicked', _on_suggest, app, rename_widget,
                registry, repository, util, log)

    # Dropdown side: open the plugin settings to pick another model.
    popover = Gtk.Popover()
    pbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    pbox.set_margin_top(6)
    pbox.set_margin_bottom(6)
    pbox.set_margin_start(6)
    pbox.set_margin_end(6)
    settings_btn = Gtk.Button(label=_('Choose another model…'))
    settings_btn.add_css_class('flat')
    settings_btn.connect('clicked', _on_open_settings, app, dialog, popover)
    pbox.append(settings_btn)
    popover.set_child(pbox)
    btn.set_popover(popover)

    # Place it on the right of the dialog header bar so it sits apart from
    # the built-in 'Suggest' button on the bottom action bar.
    dialog.pack_header_end(btn)
    app.add_widget('miazai-suggest-button', btn)


def _on_open_settings(button, app, dialog, popover):
    popover.popdown()
    plugin = app.get_widget('plugin-MiAZAIAssistant')
    if plugin is None:
        return
    # Present relative to the rename dialog so the settings open on top of it.
    plugin.show_settings(widget=dialog)


def _on_suggest(button, app, rename_widget, registry, repository, util, log):
    from miazai.providers import active_provider
    from miazai.extractor import extract
    from miazai.vocab import load_vocabulary
    import miazai.prompt as P

    plugin = app.get_widget('plugin-MiAZAIAssistant')
    if plugin is None:
        log.error('MiAZAIAssistant plugin object not found')
        return

    button.set_sensitive(False)
    button.set_label(_('Thinking…'))

    doc = rename_widget.get_filepath_source()
    abs_path = pathlib.Path(repository.docs) / doc
    conf_dir = pathlib.Path(repository.conf)
    vocab = load_vocabulary(conf_dir)
    provider = active_provider(plugin.plugin, registry)

    model = (provider.config.get('model') or '').strip() or '(default)'
    log.info(f'AI suggest requested: provider={provider.name} '
             f'model={model} document={doc}')

    def _run():
        try:
            extracted = extract(abs_path)
            text = extracted.text if extracted.is_useful else None
            file_arg = None if text else abs_path
            if not text and not provider.supports_files:
                raise RuntimeError(
                    _('No extractable text found and provider "{p}" does not '
                      'support file upload. Install pdftotext or tesseract.').format(
                        p=provider.name))
            suggestion = provider.suggest(
                text=text,
                file_path=file_arg,
                vocab=vocab,
                system_prompt=P.system_prompt(vocab),
                user_prompt=P.user_prompt(),
                schema=P.schema(),
            )
        except Exception as exc:
            log.error(f'AI provider failed: {exc}')
            GLib.idle_add(_finish, button, None, str(exc), app, rename_widget)
            return
        usage = getattr(suggestion, 'usage', {}) or {}
        if usage:
            log.info(
                f'AI suggest done: provider={provider.name} model={model} '
                f"tokens input={usage.get('input_tokens', '?')} "
                f"output={usage.get('output_tokens', '?')} "
                f"total={usage.get('total_tokens', '?')}")
        else:
            log.info(f'AI suggest done: provider={provider.name} model={model} '
                     f'(token usage not reported)')
        GLib.idle_add(_finish, button, suggestion, None, app, rename_widget)

    threading.Thread(target=_run, daemon=True).start()


def _finish(button, suggestion, error, app, rename_widget):
    button.set_sensitive(True)
    button.set_label(_('Suggest with AI'))
    if error:
        app.get_service('dialogs').show_toast(
            _('AI suggestion failed: {err}').format(
                err=GLib.markup_escape_text(str(error))))
        return False
    _apply_suggestion(rename_widget, suggestion, app)
    return False


def _apply_suggestion(rename_widget, suggestion, app):
    from MiAZ.backend.models import Country, Group, SentBy, Purpose, SentTo

    if suggestion.date:
        rename_widget.entry_date.set_text(suggestion.date)

    field_map = [
        ('country', rename_widget.dpdCountry,  rename_widget._cfg_country,  Country),
        ('group',   rename_widget.dpdGroup,    rename_widget._cfg_group,    Group),
        ('sentby',  rename_widget.dpdSentBy,   rename_widget._cfg_sentby,   SentBy),
        ('purpose', rename_widget.dpdPurpose,  rename_widget._cfg_purpose,  Purpose),
        ('sentto',  rename_widget.dpdSentTo,   rename_widget._cfg_sentto,   SentTo),
    ]

    for key, dropdown, cfg, item_type in field_map:
        value = getattr(suggestion, key, '').strip().upper()
        if not value:
            continue
        if _select_in_dropdown(dropdown, value):
            continue
        _ask_to_add(app, rename_widget, item_type, cfg, value)

    if suggestion.concept:
        rename_widget.entry_concept.set_text(suggestion.concept)

    rename_widget._on_changed_entry()


def _select_in_dropdown(dropdown, key) -> bool:
    model = dropdown.get_model()
    if model is None:
        return False
    for i in range(model.get_n_items()):
        item = model.get_item(i)
        if item is not None and item.id == key:
            dropdown.set_selected(i)
            return True
    return False


def _ask_to_add(app, rename_widget, item_type, cfg, value):
    from MiAZ.frontend.desktop.services.dialogs import MiAZDialogAdd
    from gettext import gettext as _

    i_title = _(item_type.__title__)
    parent = rename_widget.get_root()
    helper = MiAZDialogAdd(app)
    title = _('Add new {title}').format(title=i_title.lower())
    key1 = _('{title} key').format(title=i_title.title())
    key2 = _('Description')
    dialog = helper.create(parent=parent, title=title, key1=key1, key2=key2)
    helper.set_value1(value)
    dialog.connect('response', _on_add_response, helper, item_type, cfg, rename_widget)
    dialog.present(parent)


def _on_add_response(_dialog, response, helper, item_type, cfg, rename_widget):
    if response != 'apply':
        return
    key = helper.get_value1().strip().upper()
    value = helper.get_value2().strip()
    if not key:
        return
    cfg.add_available(key, value)
    cfg.add_used(key, value)
    rename_widget._select_value(item_type, key)
    rename_widget._on_changed_entry()
