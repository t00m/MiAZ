#!/usr/bin/python3
# File: screenshots.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Capture screenshots of the workspace views

"""Screenshots of the workspace views.

Run it against a throwaway HOME pointing at a test repository:

    HOME=/tmp/miaz-shots PYTHONPATH=. python3 scripts/devel/screenshots.py

with $HOME/.MiAZ/etc/{repos-used,repos-available,MiAZ-application}.json
naming the repository. Images land in ~/Documents/testing/MiAZ/screenshots.
Always checksum the results: two of the approaches that do not work still
write files that look plausible.


Two things make this work, and both were learned the hard way:

1. A real app.run() main loop. Iterating the main context by hand, the way the
   UI tests drive the app, never gets GTK to produce a render node and every
   snapshot comes back empty. Steps are chained with GLib.timeout_add instead.
2. Gtk.Widget.do_snapshot + Gsk.CairoRenderer. Gtk.WidgetPaintable is the
   obvious route and it is wrong here: a fresh one has observed no frame and
   snapshots to nothing, and a kept one hands back the first frame it ever saw,
   which silently produces identical screenshots.
"""
import os, sys
import gi
gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); gi.require_version('Gsk', '4.0')
from gi.repository import GLib, Gtk, Gsk, Adw

OUT = '/home/t00m/Documents/testing/MiAZ/screenshots'
W, H = 1360, 880
os.makedirs(OUT, exist_ok=True)

sys.argv = ['miaz']
from MiAZ.env import ENV
from MiAZ.miaz import MiAZ
MiAZ(ENV)
_o = Adw.ApplicationWindow.set_default_size
Adw.ApplicationWindow.set_default_size = lambda s, w, h: _o(s, W, H)
from MiAZ.frontend.desktop.app import MiAZApp

app = MiAZApp(application_id='io.github.t00m.MiAZ.Shots3')
app.set_env(ENV)
state = {}


def remap(widget):
    """Force a fresh layout pass.

    Nothing is painting these windows, so after the first map GTK never
    re-allocates the children: the window keeps its size while AdwDialogHost
    inside it has no allocation at all, and snapshotting gives an empty node.
    Hiding and showing the window makes it lay out again. It has to be a step
    of its own, so the main loop runs in between.
    """
    widget.set_visible(False)
    widget.set_visible(True)


def shoot(widget, name):
    snapshot = Gtk.Snapshot()
    Gtk.Widget.do_snapshot(widget, snapshot)
    node = snapshot.to_node()
    if node is None:
        print(f"  {name}: EMPTY", flush=True)
        return
    renderer = Gsk.CairoRenderer()
    renderer.realize(None)
    texture = renderer.render_texture(node, None)
    path = os.path.join(OUT, f"{name}.png")
    texture.save_to_png(path)
    renderer.unrealize()
    print(f"  {name}.png {texture.get_width()}x{texture.get_height()} "
          f"{os.path.getsize(path)//1024}KB", flush=True)


def steps():
    win = app.get_widget('window')
    ws = app.get_widget('workspace')
    view = app.get_widget('workspace-view')
    grid = app.get_widget('workspace-grid')
    dd = app.get_widget('ws-dropdowns')['Date']
    m = dd.get_model()
    dd.set_selected(next(i for i in range(len(m))
                         if getattr(m.get_item(i), 'preset', None) == 'all-documents'))
    yield 4, lambda: print(f"documents: {len(view.get_model_filter())}", flush=True)

    yield 2, lambda: ws.show_view('details')
    yield 1, lambda: remap(win)
    yield 2, lambda: shoot(win, '1-details')

    yield 1, lambda: ws.show_view('grid')
    yield 30, lambda: None
    yield 1, lambda: remap(win)
    yield 2, lambda: shoot(win, '2-grid-icons-256')

    yield 1, lambda: grid.set_icon_size(4)
    yield 26, lambda: None
    yield 1, lambda: remap(win)
    yield 2, lambda: shoot(win, '3-grid-icons-512')

    yield 1, lambda: grid.set_icon_size(0)
    yield 22, lambda: None
    yield 1, lambda: remap(win)
    yield 2, lambda: shoot(win, '4-grid-icons-128')

    yield 1, lambda: grid.set_icon_size(2)
    yield 6, lambda: ws.show_view('timeline')
    yield 15, lambda: remap(win)
    yield 2, lambda: shoot(win, '5-timeline')

    yield 1, lambda: ws.show_view('details')
    yield 1, lambda: app.get_widget('headerbar-button-preview').set_active(True)
    yield 1, lambda: view.get_selection().select_item(0, True)
    yield 13, lambda: remap(win)
    yield 2, lambda: shoot(win, '6-preview-bottom-sheet')

    # The rename dialog, with its own preview raised from the bottom.
    yield 1, lambda: app.get_widget('headerbar-button-preview').set_active(False)
    yield 1, lambda: app.get_service('actions').document_rename()
    yield 4, lambda: app.get_widget('rename-button-preview').set_active(True)
    yield 13, lambda: remap(app.get_widget('dialog-rename'))
    yield 2, lambda: shoot(app.get_widget('dialog-rename'), '7-rename-preview-sheet')
    yield 1, lambda: app.get_widget('dialog-rename').emit('response', 'cancel')
    yield 2, lambda: app.quit()


def advance():
    if 'gen' not in state:
        state['gen'] = steps()
    try:
        delay, action = next(state['gen'])
    except StopIteration:
        app.quit()
        return False

    def later():
        try:
            action()
        except Exception as error:
            print(f"  step failed: {type(error).__name__}: {error}", flush=True)
        GLib.idle_add(advance)
        return False
    GLib.timeout_add(int(delay * 1000), later)
    return False


def on_started(*args):
    def ready():
        ws = app.get_widget('workspace')
        if ws is not None and ws.is_loaded():
            advance()
            return False
        return True
    GLib.timeout_add(500, ready)


app.connect('application-started', on_started)
app.run([])
print("DONE", flush=True)
