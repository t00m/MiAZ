
import pathlib
from gettext import gettext as _

from gi.repository import Adw, Gdk, Gtk

from MiAZ.backend.tasks import run_in_background


def register_suggest_items(plugin, app, registry, repository, util, log):
    """Contribute this plugin's entries to the rename dialog's Suggest menu.

    There used to be an Adw.SplitButton packed into the dialog header, which
    put two ways of proposing the same fields in two different corners of the
    same window. The core owns one Suggest menu now and plugins add to it.

    Idempotent: registering the same action name twice replaces the entry
    rather than stacking a second copy, which is what the old handler-tracking
    dance existed to prevent.
    """
    # Its own section: sending the document to a model is a different thing
    # from reading it here, and the user chooses before it happens.
    section = _('With AI')
    plugin.register_suggest_item(
        name='miazai-suggest',
        label=_('Ask the model'),
        section=section,
        callback=lambda _action, _param, _data: _suggest_now(
            app, registry, repository, util, log))
    plugin.register_suggest_item(
        name='miazai-choose-model',
        label=_('Choose another model…'),
        section=section,
        callback=lambda _action, _param, _data: _open_settings(app))


def unregister_suggest_items(plugin):
    plugin.unregister_suggest_items()


def _suggest_now(app, registry, repository, util, log):
    """Run the suggestion against whichever rename dialog is open.

    The menu is shared by every rename dialog, so the widget is resolved when
    the entry is chosen rather than captured when it is registered.
    """
    rename_widget = app.get_widget('rename-widget')
    if rename_widget is None:
        return
    _on_suggest(app, rename_widget, registry, repository, util, log)


def _open_settings(app):
    plugin = app.get_widget('plugin-MiAZAIAssistant')
    if plugin is None:
        return
    # Present relative to the rename dialog so the settings open on top of it.
    plugin.show_settings(widget=app.get_widget('dialog-rename'))


def _set_busy(app, message):
    """Show what the dialog is doing, when the dialog can show it."""
    dialog = app.get_widget('dialog-rename')
    if dialog is not None and hasattr(dialog, 'set_busy'):
        dialog.set_busy(message)


def _clear_busy(app):
    dialog = app.get_widget('dialog-rename')
    if dialog is not None and hasattr(dialog, 'clear_busy'):
        dialog.clear_busy()


def _set_entry_enabled(app, enabled):
    """Grey out this plugin's Suggest entry while its request is in flight.

    It used to disable its own button and relabel it 'Thinking…'. There is no
    button any more, only an entry in the shared Suggest menu, so the action
    behind the entry is what gets disabled.
    """
    actions = app.get_service('actions')
    if actions is not None:
        actions.set_suggest_item_enabled('miazai-suggest', enabled)


def _on_suggest(app, rename_widget, registry, repository, util, log):
    from miazai.providers import active_provider, MissingDependencyError
    from miazai.extractor import extract
    from miazai.vocab import load_vocabulary
    import miazai.prompt as P

    plugin = app.get_widget('plugin-MiAZAIAssistant')
    if plugin is None:
        log.error('MiAZAIAssistant plugin object not found')
        return

    _set_entry_enabled(app, False)

    doc = rename_widget.get_filepath_source()
    abs_path = pathlib.Path(repository.docs) / doc
    conf_dir = pathlib.Path(repository.conf)
    vocab = load_vocabulary(conf_dir)
    provider = active_provider(plugin.plugin, registry)

    model = (provider.config.get('model') or '').strip() or '(default)'
    log.info(f'AI suggest requested: provider={provider.name} '
             f'model={model} document={doc}')

    # A provider call takes seconds and used to say nothing while it ran. The
    # model is named because which one answered is the thing worth knowing.
    _set_busy(app, _('Guessing with AI ({model})').format(model=model))

    def _run():
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
            system_prompt=P.suggest_system_prompt(vocab),
            user_prompt=P.suggest_user_prompt(),
            schema=P.schema(),
        )
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
        return suggestion

    def _done(suggestion):
        _finish(suggestion, None, False, app, rename_widget)

    def _failed(exc):
        # Every failure lands here, including the one raised above for a
        # document with no text. The entry has to be re-enabled whatever went
        # wrong, or it stays greyed out for the rest of the session.
        log.error(f'AI provider failed: {exc}')
        _finish(None, str(exc), isinstance(exc, MissingDependencyError),
                app, rename_widget)

    run_in_background(_run, on_done=_done, on_error=_failed,
                      name='miazai-suggest')


def _finish(suggestion, error, needs_libs, app, rename_widget):
    _set_entry_enabled(app, True)
    _clear_busy(app)
    if error:
        _show_error_dialog(app, rename_widget, str(error), needs_libs)
        return
    _apply_suggestion(rename_widget, suggestion, app)


def _show_error_dialog(app, rename_widget, details, needs_libs=False):
    """Report a provider failure with the full, selectable error text.

    The message is shown in a scrollable, selectable label so the user can read
    long errors and copy them for a bug report. A Copy button copies without
    closing the dialog. When the failure is a missing Python library, an
    'Enable external libraries…' button installs it into the venv.
    """
    parent = rename_widget.get_root()
    if needs_libs:
        body = _('This provider needs an external library that is not '
                 'installed. Enable external libraries to install it.')
    else:
        body = _('The AI provider could not complete the request. '
                 'Full error details are below.')
    dialog = Adw.AlertDialog(heading=_('AI suggestion failed'), body=body)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

    copy_btn = Gtk.Button(label=_('Copy details'))
    copy_btn.add_css_class('flat')
    copy_btn.set_halign(Gtk.Align.END)
    copy_btn.connect('clicked', _on_copy_details, app, details)
    box.append(copy_btn)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_min_content_height(120)
    scrolled.set_max_content_height(320)
    scrolled.add_css_class('card')

    label = Gtk.Label(label=details)
    label.set_selectable(True)
    label.set_wrap(True)
    label.set_xalign(0.0)
    label.set_yalign(0.0)
    label.add_css_class('monospace')
    label.set_margin_top(8)
    label.set_margin_bottom(8)
    label.set_margin_start(8)
    label.set_margin_end(8)
    scrolled.set_child(label)
    box.append(scrolled)

    dialog.set_extra_child(box)
    if needs_libs:
        dialog.add_response('enable', _('Enable external libraries…'))
        dialog.set_response_appearance('enable', Adw.ResponseAppearance.SUGGESTED)
    dialog.add_response('close', _('Close'))
    dialog.set_default_response('enable' if needs_libs else 'close')
    dialog.set_close_response('close')
    if needs_libs:
        dialog.connect('response', _on_error_response, app, rename_widget)
    dialog.present(parent)


def _on_error_response(dialog, response, app, rename_widget):
    if response == 'enable':
        app.get_service('extlibs').install(rename_widget.get_root())


def _on_copy_details(button, app, details):
    try:
        Gdk.Display.get_default().get_clipboard().set(details)
        app.get_service('dialogs').show_toast(_('Error details copied'))
    except Exception:
        pass


def _apply_suggestion(rename_widget, suggestion, app):
    from MiAZ.backend.models import Country, Group, SentBy, Purpose, SentTo

    util = rename_widget.util
    # Only accept an 8-digit date. The model may return a placeholder such as
    # "<UNKNOWN>" that must never reach the filename.
    date = (suggestion.date or '').strip()
    if date.isdigit() and len(date) == 8:
        rename_widget.entry_date.set_text(date)

    field_map = [
        ('country', rename_widget.dpdCountry,  rename_widget._cfg_country,  Country),
        ('group',   rename_widget.dpdGroup,    rename_widget._cfg_group,    Group),
        ('sentby',  rename_widget.dpdSentBy,   rename_widget._cfg_sentby,   SentBy),
        ('purpose', rename_widget.dpdPurpose,  rename_widget._cfg_purpose,  Purpose),
        ('sentto',  rename_widget.dpdSentTo,   rename_widget._cfg_sentto,   SentTo),
    ]

    for key, dropdown, cfg, item_type in field_map:
        # Sanitize the suggested value the same way keys are stored, so a
        # placeholder or stray character ("<UNKNOWN>") becomes a clean key
        # ("UNKNOWN") before it is matched, enabled or added.
        value = util.valid_key(getattr(suggestion, key, '')).upper()
        if not value:
            continue
        # The model is asked for an upper-case key, but the repository may
        # already hold the same name written differently. Suggesting ALLIANZ
        # where Allianz exists used to add a second sender for one company.
        value = _existing_key(cfg, value) or value
        if _select_in_dropdown(dropdown, value):
            continue
        # The value is not enabled for this repository. If it already exists in
        # the available pool (for example a valid ISO country like DE), offer to
        # enable it and keep its description; only truly new values are added.
        if cfg.exists_available(value):
            _ask_to_enable(app, rename_widget, item_type, cfg, value)
        else:
            _ask_to_add(app, rename_widget, item_type, cfg, value)

    if suggestion.concept:
        rename_widget.entry_concept.set_text(suggestion.concept)

    rename_widget._on_changed_entry()


def _existing_key(cfg, value):
    """The key this repository already has for `value`, ignoring case.

    Returns None when there is no such key, so the caller can go on to offer
    adding it. The used values are searched before the available ones: a value
    already enabled here is the better answer when a repository somehow holds
    both spellings.
    """
    wanted = value.casefold()
    for load in (cfg.load_used, cfg.load_available):
        try:
            entries = load()
        except Exception:
            continue
        for key in entries or {}:
            if key.casefold() == wanted:
                return key
    return None


def _select_in_dropdown(dropdown, key) -> bool:
    """Select the entry whose id is `key`, ignoring case.

    The dropdown lists what the repository actually holds, so comparing
    exactly would skip past an entry that is there under another spelling and
    fall through to offering to add it again.
    """
    model = dropdown.get_model()
    if model is None:
        return False
    wanted = (key or '').casefold()
    for i in range(model.get_n_items()):
        item = model.get_item(i)
        if item is not None and (item.id or '').casefold() == wanted:
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
    # Sanitize whatever the user accepted: strip characters that are not valid
    # in a filename field, so "<UNKNOWN>" becomes "UNKNOWN".
    key = rename_widget.util.valid_key(helper.get_value1()).upper()
    value = helper.get_value2().strip()
    if not key or not value:
        return
    cfg.add_available(key, value)
    cfg.add_used(key, value)
    rename_widget._select_value(item_type, key)
    rename_widget._on_changed_entry()


def _ask_to_enable(app, rename_widget, item_type, cfg, value):
    from gettext import gettext as _
    from MiAZ.backend.util import humanize_value

    description = cfg.load_available().get(value, '')
    name = humanize_value(item_type.__gtype_name__, description) or value
    i_title = _(item_type.__title__)
    parent = rename_widget.get_root()
    dialog = Adw.AlertDialog(
        heading=_('Enable {title}?').format(title=i_title.lower()),
        body=_('"{name}" ({key}) already exists but is not enabled for this '
               'repository. Enable it?').format(name=name, key=value))
    dialog.add_response('cancel', _('Cancel'))
    dialog.add_response('enable', _('Enable'))
    dialog.set_response_appearance('enable', Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response('enable')
    dialog.set_close_response('cancel')
    dialog.connect('response', _on_enable_response,
                   item_type, cfg, value, description, rename_widget)
    dialog.present(parent)


def _on_enable_response(_dialog, response, item_type, cfg, value, description, rename_widget):
    if response != 'enable':
        return
    # Preserve the existing description; do not overwrite it with an empty value.
    cfg.add_used(value, description)
    rename_widget._select_value(item_type, value)
    rename_widget._on_changed_entry()
