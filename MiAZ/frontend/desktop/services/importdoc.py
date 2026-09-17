# File: importdoc.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Core service to add documents to the repository from the
#              local filesystem.

import os
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from MiAZ.backend import importer
from MiAZ.backend.log import MiAZLog
from MiAZ.backend.tasks import run_in_background
from MiAZ.backend.tasks import run_on_main

# Above this many files, or this many bytes, an import holds the workspace
# back, turns the watcher off and runs off the main loop. Below both the copy
# is quick enough that the machinery would cost more than it saves.
BATCH_THRESHOLD = 20

# The count alone said nothing about the work. Twenty 40 MB scans is 800 MB
# copied on the main loop and never reached a threshold of twenty files, so
# GNOME put up its "not responding" dialog, which it does after about five
# seconds of a window not answering the compositor. 16 MB is roughly a second
# from a slow source, which is under that with room to spare, and on a local
# disk it is fast enough that taking the worker path costs nothing noticeable.
BATCH_BYTES = 16 * 1024 * 1024


def needs_batch(count: int, total_bytes: int = 0) -> bool:
    """Whether an import is worth the batch treatment.

    Either rule is enough on its own. Many small files are many workspace
    refreshes and many watcher events whatever they weigh; a few large ones are
    a long copy whatever they number.
    """
    return count > BATCH_THRESHOLD or total_bytes > BATCH_BYTES


def total_size(paths) -> int:
    """Bytes an import will copy, as far as they can be counted.

    A path that cannot be measured counts as nothing: it vanished between the
    chooser and here, and reporting that is the copy's job, not this one's.
    """
    total = 0
    for path in paths:
        try:
            total += os.path.getsize(path)
        except OSError:
            pass
    return total


class MiAZImportDoc(GObject.GObject):
    """Add documents to the repository from the local filesystem.

    The 'Add new document(s)' action every repository needs on day one, so
    it lives in core rather than behind a togglable plugin. It builds its
    own menu item so the headerbar 'Add' menu can show it regardless of
    which Import plugins are enabled.
    """
    __gtype_name__ = 'MiAZImportDoc'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.log = MiAZLog('MiAZImportDoc')
        self.util = app.get_service('util')
        self.factory = app.get_service('factory')
        self.repository = app.get_service('repo')
        self.srvdlg = app.get_service('dialogs')
        self.menuitem = self.factory.create_menuitem(
            name='import-doc', label=_('Add new document(s)'),
            callback=self.import_files, shortcuts=['<Control>Insert'])
        self.menuitem_dir = self.factory.create_menuitem(
            name='import-dir', label=_('Add documents from a directory'),
            callback=self.import_directory, shortcuts=['<Shift>Insert'])

    def import_files(self, *args):
        self.factory.create_filechooser_for_files(self._on_filechooser_response)

    def import_directory(self, *args):
        self.factory.create_filechooser_for_directories(
            self._on_folderchooser_response)

    def _on_folderchooser_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error as error:
            # Closing the folder chooser is a normal action, not an error.
            dismissed = (
                error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED)
                or error.matches(Gtk.DialogError.quark(), Gtk.DialogError.CANCELLED)
            )
            if dismissed:
                self.log.debug("Directory import cancelled by the user")
                self.srvdlg.show_toast(_('Document import cancelled'))
                return
            self.log.error(f"Could not open the folder chooser: {error.message}")
            self.srvdlg.show_error(
                title=_('Could not open folder'),
                body=_('The folder chooser could not be opened.\n\n{error}').format(
                    error=error.message))
            return

        path = folder.get_path() if folder is not None else None
        if not path:
            return
        # Straight through the drop path: a chosen folder and a dropped one
        # raise the same question about subfolders, and answer it once.
        self.import_dropped([path])

    def _on_filechooser_response(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error as error:
            # Closing the file chooser is a normal action, not an error.
            dismissed = (
                error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED)
                or error.matches(Gtk.DialogError.quark(), Gtk.DialogError.CANCELLED)
            )
            if dismissed:
                self.log.debug("Document import cancelled by the user")
                self.srvdlg.show_toast(_('Document import cancelled'))
                return
            self.log.error(f"Could not open the file chooser: {error.message}")
            self.srvdlg.show_error(
                title=_('Could not open files'),
                body=_('The file chooser could not be opened.\n\n{error}').format(
                    error=error.message))
            return

        if not files:
            return

        self.import_paths([file.get_path() for file in files])

    def import_paths(self, paths):
        """Copy files into the repository and report how it went.

        Shared by every entry point (the file chooser, the directory chooser
        and the workspace drop target), so a document imported by dropping it
        is the same operation, with the same reporting, as one picked from a
        chooser.

        A big import goes to a worker instead, with the workspace held back
        and the watcher off. Big means many files or many bytes: see
        needs_batch. That path reports from the main loop when it ends and
        returns None, since there is nothing to return yet.
        """
        if needs_batch(len(paths), total_size(paths)):
            self._import_batch(paths)
            return None
        imported, failed = self._copy_all(paths)
        self._report(imported, failed)
        return imported, failed

    def _copy_all(self, paths):
        """Copy every path, counting what worked and naming what did not.

        The copying itself is MiAZ.backend.importer, which `miaz add` calls
        too, so a document added from the window and one added from a terminal
        arrive the same way. No GTK here: this is the half the worker runs.
        """
        imported, failed = importer.import_paths(
            self.util, self.repository.docs, paths)
        return len(imported), failed

    def _report(self, imported, failed):
        if imported > 0:
            self.srvdlg.show_toast(
                _('{count} documents imported successfully').format(count=imported))
        if failed:
            self.srvdlg.show_error(
                title=_('Some documents could not be imported'),
                body=_('These documents could not be imported:\n\n{items}').format(
                    items='\n'.join(failed)))

    def _import_batch(self, paths):
        """Import many files without freezing the window.

        The workspace is held back and the watcher turned off for the whole
        run, so a hundred files cause one refresh rather than a hundred. Both
        are released from the main loop in _copy_batch's finally block, which
        is what keeps a failure halfway through from leaving the workspace
        suspended for the rest of the session.
        """
        workspace = self.app.get_widget('workspace')
        suspend = workspace.suspend_updates() if workspace is not None else None
        watcher = self.app.get_service('watcher')
        if watcher is not None:
            watcher.set_active(False)
        self.log.debug(f"Importing {len(paths)} documents in the background")
        run_in_background(
            lambda: self._copy_batch(paths, suspend, watcher),
            on_error=self._on_batch_failed,
            name='importdoc-batch')

    def _copy_batch(self, paths, suspend, watcher):
        try:
            imported, failed = self._copy_all(paths)
            GLib.idle_add(self._report, imported, failed)
        finally:
            workspace = self.app.get_widget('workspace')
            if watcher is not None:
                GLib.idle_add(watcher.set_active, True)
            if workspace is not None:
                # Asked while still suspended: the gate records the request and
                # runs one refresh when the last holder releases.
                GLib.idle_add(workspace.update)
            if suspend is not None:
                run_on_main(suspend.release)

    def _on_batch_failed(self, error):
        """Report an import that died before _copy_all could count anything.

        _copy_batch releases the watcher and the update gate in its finally
        block, so by the time this runs the workspace is usable again. What
        was missing was any sign that the import stopped early.
        """
        self.log.error(f"Document import failed: {error}")
        self.srvdlg.show_error(
            title=_('Could not import the documents'),
            body=_('The import stopped before finishing.\n\n{error}').format(
                error=error))

    def import_dropped(self, paths):
        """Import what the user dropped on the workspace.

        Files are imported straight away. Folders are not: how many documents
        a folder means depends on whether its subfolders count, so the user is
        asked first and told how many files each answer would import.
        """
        paths = [path for path in paths if path]
        if not paths:
            return
        folders = [path for path in paths if os.path.isdir(path)]
        if not folders:
            self.import_paths(paths)
            return None
        return self._ask_recursive(paths, folders)

    def _ask_recursive(self, paths, folders):
        check = Gtk.CheckButton(label=_('Include subfolders'))
        label = Gtk.Label(xalign=0)
        label.set_wrap(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.append(check)
        box.append(label)

        def update_count(*args):
            count = len(importer.expand_paths(paths, recursive=check.get_active()))
            label.set_text(
                _('{count} files would be imported').format(count=count))
        check.connect('toggled', update_count)
        update_count()
        self.app.add_widget('import-drop-recursive', check)
        self.app.add_widget('import-drop-count', label)

        names = '\n'.join(os.path.basename(os.path.normpath(folder))
                          for folder in folders)
        title = _('Import documents')
        body = _('You dropped these folders:\n\n{folders}').format(folders=names)
        dialog = self.srvdlg.show_question(
            title=title, body=body, widget=box,
            callback=self._on_recursive_response, data=(paths, check))
        dialog.present(self.app.get_widget('window'))
        return dialog

    def _on_recursive_response(self, dialog, response, data):
        paths, check = data
        if response != 'apply':
            self.log.debug("Document import cancelled by the user")
            self.srvdlg.show_toast(_('Document import cancelled'))
            return
        files = importer.expand_paths(paths, recursive=check.get_active())
        if not files:
            self.srvdlg.show_toast(_('There was nothing to import'))
            return
        self.import_paths(files)
