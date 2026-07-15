#!/usr/bin/python3

import pathlib
import threading
from gettext import gettext as _

from gi.repository import Adw, GLib, Gtk

from MiAZ.frontend.desktop.widgets.markdownview import MiAZMarkdownView

from miazaic.providers import active_provider, MissingDependencyError
from miazaic.extractor import extract
from miazaic.prompt import system_prompt


class MiAZAIChatDialog(Adw.Window):
    """Per-document chat window. Conversation is ephemeral: it lives only
    while the window is open. The transcript is rendered as Markdown. When the
    MiAZNotes plugin is active, each answer can be saved as a note (the title
    is the question, the body is the answer)."""

    def __init__(self, app, document_id, registry, plugin, log):
        super().__init__()
        self.app = app
        self.document_id = document_id
        self.registry = registry
        self.plugin = plugin
        self.log = log
        self.repository = app.get_service('repo')
        self.history = []      # provider-facing conversation
        self.turns = []        # rendered transcript turns
        self.document_text = None
        self.file_path = None
        self.provider = active_provider(self.plugin, self.registry)
        self._notes = self._get_notes_plugin()
        self._status = ''
        self._awaiting = False
        self._next_idx = 0

        self.set_title(_('Chat: {doc}').format(doc=document_id))
        self.set_default_size(720, 640)
        self.set_destroy_with_parent(True)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title=_('Chat with document'), subtitle=document_id))
        toolbar.add_top_bar(header)

        self._view = MiAZMarkdownView(app=app, on_command=self._on_command)
        self._view.set_vexpand(True)

        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text(_('Ask something about this document…'))
        self._entry.connect('activate', self._on_send)
        self._send = Gtk.Button(label=_('Send'))
        self._send.add_css_class('suggested-action')
        self._send.connect('clicked', self._on_send)
        inputbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        inputbar.set_margin_top(6)
        inputbar.set_margin_bottom(12)
        inputbar.set_margin_start(12)
        inputbar.set_margin_end(12)
        inputbar.append(self._entry)
        inputbar.append(self._send)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self._view)
        content.append(inputbar)

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(content)
        toolbar.set_content(self._toast_overlay)
        self.set_content(toolbar)

        self._set_input_enabled(False)
        self._set_status(_('Loading document…'))
        self._prepare_document()

    # Document preparation
    def _prepare_document(self):
        path = pathlib.Path(self.repository.docs) / self.document_id

        def _work():
            text = None
            try:
                result = extract(path)
                text = result.text if result.is_useful else None
            except Exception as error:
                self.log.error(f"Could not extract text: {error}")
            GLib.idle_add(self._set_document, text, str(path))

        threading.Thread(target=_work, daemon=True).start()

    def _set_document(self, text, path):
        self.document_text = text
        if text:
            self.file_path = None
            self._set_status(_('Document loaded. Ask your questions.'))
        elif self.provider.supports_files:
            self.file_path = path
            self._set_status(
                _('No text was extracted; the file will be sent to the provider.'))
        else:
            self.file_path = None
            self._set_status(
                _('No text could be extracted and this provider cannot read files '
                  'directly. Install pdftotext or tesseract, or pick a provider '
                  'that supports file upload in the plugin settings.'))
        self._set_input_enabled(True)
        self._entry.grab_focus()
        return False

    # Notes integration (optional)
    def _get_notes_plugin(self):
        notes = self.app.get_widget('plugin-MiAZNotes')
        if notes is not None and callable(getattr(notes, 'add_note', None)):
            return notes
        return None

    def _on_command(self, command):
        if command == 'enablelibs':
            self.app.get_service('extlibs').install(self)
            return False
        if command.startswith('save:'):
            try:
                idx = int(command[len('save:'):])
            except ValueError:
                return False
            self._save_turn(idx)
        return False

    def _save_turn(self, idx):
        turn = next((t for t in self.turns if t.get('idx') == idx), None)
        if turn is None or self._notes is None:
            return
        # MiAZNotes derives the note title from the first line of the body, so
        # put the question as a heading and the answer below it.
        body = f"# {turn['question']}\n\n{turn['content']}"
        path = self._notes.add_note(self.document_id, body, category='General')
        if path:
            turn['saved'] = True
            self._toast(_('Saved to notes'))
            self._rerender()
        else:
            self._toast(_('Could not save the note'))

    # Sending
    def _on_send(self, *_args):
        question = self._entry.get_text().strip()
        if not question:
            return
        self._entry.set_text('')
        self.turns.append({'role': 'user', 'content': question})
        self.history.append({'role': 'user', 'content': question})
        self._awaiting = True
        self._set_input_enabled(False)
        self._rerender()

        provider = self.provider
        doc_text = self.document_text
        file_path = self.file_path
        sysp = system_prompt(self.document_id)
        snapshot = list(self.history)

        def _work():
            try:
                result = provider.chat(messages=snapshot, system_prompt=sysp,
                                       document_text=doc_text, file_path=file_path)
            except Exception as exc:
                self.log.error(f'AI chat failed: {exc}')
                needs_libs = isinstance(exc, MissingDependencyError)
                GLib.idle_add(self._on_error, str(exc), needs_libs)
                return
            GLib.idle_add(self._on_answer, question, result)

        threading.Thread(target=_work, daemon=True).start()

    def _on_answer(self, question, result):
        text = (result.get('text') or '').strip() or _('(no answer)')
        usage = result.get('usage') or {}
        self.history.append({'role': 'assistant', 'content': text})
        idx = self._next_idx
        self._next_idx += 1
        self.turns.append({'role': 'assistant', 'content': text,
                           'question': question, 'idx': idx, 'saved': False})
        self._awaiting = False
        self._set_input_enabled(True)
        self._rerender()
        self._entry.grab_focus()

        model = (self.provider.config.get('model') or '').strip() or '(default)'
        if usage:
            self.log.info(
                f'AI chat: provider={self.provider.name} model={model} '
                f"tokens input={usage.get('input_tokens', '?')} "
                f"output={usage.get('output_tokens', '?')} "
                f"total={usage.get('total_tokens', '?')}")
        else:
            self.log.info(f'AI chat: provider={self.provider.name} model={model} '
                          f'(token usage not reported)')
        return False

    def _on_error(self, message, needs_libs=False):
        self._awaiting = False
        self._set_input_enabled(True)
        # Error turn carries no idx, so no save link is rendered for it.
        content = _('Error: {err}').format(err=message)
        if needs_libs:
            content += ('\n\n[' + _('Enable external libraries…')
                        + '](miazcmd:enablelibs)')
        self.turns.append({'role': 'assistant', 'content': content})
        self._rerender()
        self._toast(_('Chat failed: {err}').format(err=message))
        return False

    # Rendering
    def _set_status(self, text):
        self._status = text
        self._rerender()

    def _set_input_enabled(self, enabled):
        self._entry.set_sensitive(enabled)
        self._send.set_sensitive(enabled)
        self._send.set_label(_('Send') if enabled else _('Thinking…') if self._awaiting else _('Send'))

    def _rerender(self):
        parts = []
        if self._status:
            parts.append('*' + self._status + '*')
        for turn in self.turns:
            if turn['role'] == 'user':
                parts.append('**' + _('You') + '**\n\n' + turn['content'])
            else:
                parts.append('**' + self.provider.name + '**\n\n' + turn['content'])
                if self._notes is not None and 'idx' in turn:
                    if turn.get('saved'):
                        parts.append('*' + _('Saved to notes') + '*')
                    else:
                        parts.append('[' + _('Save to notes')
                                     + '](miazcmd:save:' + str(turn['idx']) + ')')
        if self._awaiting:
            parts.append('*' + _('Thinking…') + '*')
        self._view.set_markdown('\n\n---\n\n'.join(parts))

    def _toast(self, message):
        toast = Adw.Toast(title=GLib.markup_escape_text(message))
        toast.set_timeout(3)
        self._toast_overlay.add_toast(toast)
