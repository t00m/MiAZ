"""
Module contains functions to build generic dialogs.
"""
from gi.repository import Gtk, GLib

import guiutils

def dialog_destroy(dialog, response):
    dialog.destroy()

def default_behaviour(dialog):
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_resizable(False)

def panel_ok_dialog(title, panel):
    dialog = Gtk.Dialog(title, None,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        ( _("OK"), Gtk.ResponseType.OK))

    alignment = get_default_alignment(panel)

    dialog.vbox.pack_start(alignment, True, True, 0)
    set_outer_margins(dialog.vbox)
    default_behaviour(dialog)
    dialog.connect('response', dialog_destroy)
    dialog.show_all()

def panel_ok_cancel_dialog(title, panel, accept_text, callback, data=None):
    dialog = Gtk.Dialog(title, None,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                       (_("Cancel"), Gtk.ResponseType.CANCEL,
                       accept_text, Gtk.ResponseType.ACCEPT))

    alignment = get_default_alignment(panel)

    dialog.vbox.pack_start(alignment, True, True, 0)
    set_outer_margins(dialog.vbox)
    default_behaviour(dialog)

    if data == None:
        dialog.connect('response', callback)
    else:
        dialog.connect('response', callback, data)

    dialog.show_all()

def no_button_dialog(title, panel):
    dialog = Gtk.Dialog(title, None,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)

    alignment = get_default_alignment(panel)

    dialog.vbox.pack_start(alignment, True, True, 0)
    set_outer_margins(dialog.vbox)
    dialog.set_resizable(False)
    dialog.show_all()
    return dialog

def info_message(primary_txt, secondary_txt, parent_window):
    warning_message(primary_txt, secondary_txt, parent_window, is_info=True)

def warning_message(primary_txt, secondary_txt, parent_window, is_info=False):
    warning_message_with_callback(primary_txt, secondary_txt, parent_window, is_info, dialog_destroy)

def warning_message_with_callback(primary_txt, secondary_txt, parent_window, is_info, callback):
    content = get_warning_message_dialog_panel(primary_txt, secondary_txt, is_info)
    dialog = Gtk.Dialog("",
                        parent_window,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        ( _("OK"), Gtk.ResponseType.ACCEPT))
    alignment = get_default_alignment(content)
    dialog.vbox.pack_start(alignment, True, True, 0)
    set_outer_margins(dialog.vbox)
    dialog.set_resizable(False)
    dialog.connect('response', callback)
    dialog.show_all()

def warning_message_with_panels(primary_txt, secondary_txt, parent_window, is_info, callback, panels):
    content = get_warning_message_dialog_panel(primary_txt, secondary_txt, is_info, None, panels)
    dialog = Gtk.Dialog("",
                        parent_window,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        ( _("OK"), Gtk.ResponseType.ACCEPT))
    alignment = get_default_alignment(content)
    dialog.vbox.pack_start(alignment, True, True, 0)
    set_outer_margins(dialog.vbox)
    dialog.set_resizable(False)
    dialog.connect('response', callback)
    dialog.show_all()

def warning_confirmation(callback, primary_txt, secondary_txt, parent_window, data=None, is_info=False, use_confirm_text=False):
    content = get_warning_message_dialog_panel(primary_txt, secondary_txt, is_info)
    align = get_default_alignment(content)

    if use_confirm_text == True:
        accept_text = _("Confirm")
    else:
        accept_text = _("OK")

    dialog = Gtk.Dialog("",
                        parent_window,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        (_("Cancel"), Gtk.ResponseType.REJECT,
                         accept_text, Gtk.ResponseType.ACCEPT))
    dialog.vbox.pack_start(align, True, True, 0)
    set_outer_margins(dialog.vbox)
    dialog.set_resizable(False)
    if data == None:
        dialog.connect('response', callback)
    else:
        dialog.connect('response', callback, data)

    dialog.show_all()

def get_warning_message_dialog_panel(primary_txt, secondary_txt, is_info=False, alternative_icon=None, panels=None):

    if is_info == True:
        icon = "dialog-information"
    else:
        icon = "dialog-warning"

    if alternative_icon != None:
        icon = alternative_icon

    warning_icon = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
    icon_box = Gtk.VBox(False, 2)
    icon_box.pack_start(warning_icon, False, False, 0)
    icon_box.pack_start(Gtk.Label(), True, True, 0)

    p_label = guiutils.bold_label(primary_txt)
    s_label = Gtk.Label(label=secondary_txt)
    s_label.set_use_markup(True)
    texts_pad = Gtk.Label()
    texts_pad.set_size_request(12,12)

    pbox = Gtk.HBox(False, 1)
    pbox.pack_start(p_label, False, False, 0)
    pbox.pack_start(Gtk.Label(), True, True, 0)

    sbox = Gtk.HBox(False, 1)
    sbox.pack_start(s_label, False, False, 0)
    sbox.pack_start(Gtk.Label(), True, True, 0)

    text_box = Gtk.VBox(False, 0)
    text_box.pack_start(pbox, False, False, 0)
    text_box.pack_start(texts_pad, False, False, 0)
    text_box.pack_start(sbox, False, False, 0)
    if panels != None:
        for panel in panels:
            text_box.pack_start(panel, False, False, 0)
    text_box.pack_start(Gtk.Label(), True, True, 0)

    hbox = Gtk.HBox(False, 12)
    hbox.pack_start(icon_box, False, False, 0)
    hbox.pack_start(text_box, True, True, 0)

    return hbox

def get_single_line_text_input_dialog(chars, label_width, title, ok_button_text,
                                      label, default_text):
    dialog = Gtk.Dialog(title, None,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (_("Cancel"), Gtk.ResponseType.CANCEL,
                            ok_button_text, Gtk.ResponseType.ACCEPT))

    entry = Gtk.Entry()
    entry.set_width_chars(chars)
    entry.set_text(default_text)
    entry.set_activates_default(True)

    entry_row = guiutils.get_two_column_box(Gtk.Label(label=label),
                                               entry,
                                               label_width)

    vbox = Gtk.VBox(False, 2)
    vbox.pack_start(entry_row, False, False, 0)
    vbox.pack_start(guiutils.get_pad_label(12, 12), False, False, 0)

    alignment = guiutils.set_margins(vbox, 6, 24, 24, 24)

    dialog.vbox.pack_start(alignment, True, True, 0)
    set_outer_margins(dialog.vbox)

    default_behaviour(dialog)
    dialog.set_default_response(Gtk.ResponseType.ACCEPT)

    return (dialog, entry)

def get_default_alignment(panel): # Ok, why are we doing new Gtk.Frame here and then removing shadow?
                                  # We may need to change this for Gtk4.
    alignment = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    alignment.add(panel)
    guiutils.set_margins(alignment, 12, 24, 12, 18)
    return alignment

def get_alignment2(panel):
    alignment = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    alignment.add(panel)
    guiutils.set_margins(alignment, 6, 24, 12, 12)

    return alignment

def set_outer_margins(cont):
    guiutils.set_margins(cont, 0, 6, 0, 6)

def set_default_behaviour(dialog):
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_resizable(False)

def get_ok_cancel_button_row(ok_button, cancel_button):
    lbox = Gtk.HBox(True, 2)
    lbox.pack_start(cancel_button, True, True, 0)
    lbox.pack_start(ok_button, True, True, 0)
    cancel_button.set_size_request(88, 3)

    hbox = Gtk.HBox(False, 2)
    hbox.pack_start(Gtk.Label(), True, True, 0)
    hbox.pack_start(lbox, False, False, 0)

    return hbox


# ------------------------------------------------------------------ delayed window destroying
def delay_destroy_window(window, delay):
    GLib.timeout_add(int(delay * 1000), _window_destroy_event, window)

def _window_destroy_event(window):
    window.destroy()

