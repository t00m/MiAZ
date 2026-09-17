
"""
# File: importer.py
# Author: Tomás Vírseda
# License: GPL v3
# Description: Put documents from the filesystem into a repository
"""

import os
from gettext import gettext as _


def expand_paths(paths, recursive: bool = False):
    """The files a set of given paths would import.

    Directories are replaced by the files they hold: the ones directly inside,
    or the whole tree when recursive. Everything else is kept as it is,
    including a path that does not exist, so the import reports it as failed
    instead of silently dropping it. Symlinked directories are not followed,
    since a link pointing back up the tree would otherwise walk forever.

    The order given is preserved and each file appears once, so the count a
    dialog shows is the number of files the import then copies.
    """
    files = []
    seen = set()

    def add(path):
        if path not in seen:
            seen.add(path)
            files.append(path)

    for path in paths:
        if not path:
            # A remote URI dropped from a browser has no local path.
            continue
        if not os.path.isdir(path):
            add(path)
            continue
        if recursive:
            for folder, _dirs, names in os.walk(path, followlinks=False):
                for name in sorted(names):
                    add(os.path.join(folder, name))
        else:
            for name in sorted(os.listdir(path)):
                child = os.path.join(path, name)
                if os.path.isfile(child):
                    add(child)
    return files


def free_target(docs_dir: str, basename: str) -> str:
    """A path in the repository that nothing is using yet.

    Two directories can each hold a scan.pdf, and both normalize to the same
    repository name. The copy used to overwrite, so importing a directory tree
    kept the last file of each name and lost the others without a word.

    The number goes on the concept, which is the field a person wrote, not on
    the end of the name: the last field is who the document was sent to, and a
    suffix there would invent a recipient.
    """
    target = os.path.join(docs_dir, basename)
    if not os.path.exists(target):
        return target

    name, extension = os.path.splitext(basename)
    counter = 2
    while True:
        fields = name.split('-')
        if len(fields) == 7:
            fields[5] = f'{fields[5]}_{counter}'
            candidate = '-'.join(fields)
        else:
            candidate = f'{name}_{counter}'
        target = os.path.join(docs_dir, f'{candidate}{extension}')
        if not os.path.exists(target):
            return target
        counter += 1


def import_paths(util, docs_dir: str, paths, report=None):
    """Copy every path into the repository under its normalized name.

    Returns (imported, failed): the repository names written, in the order
    they were written, and the basenames of the ones that could not be. Both
    lists, because the caller says what happened: the window shows a toast
    and the command line prints the names.

    Nothing here draws anything, which is why `miaz add` and the window's own
    Add can be the same operation.

    `report(message, fraction)` is called once per document when given. A large
    import is one job, so without it the indicator says "1 running" for as long
    as the copy takes and nothing else. `miaz add` passes none.
    """
    imported = []
    failed = []
    total = len(paths)
    for position, source in enumerate(paths, start=1):
        if report is not None:
            report(_('Importing {name}').format(
                name=os.path.basename(source) if source else str(source)),
                position / total)
        try:
            # Uppercase here rather than leaving it to the window. A repository
            # stores its names uppercase, and filename_normalize does not do
            # that half: the workspace scan used to rename the file a second
            # time, right after the import, and there is no workspace scan
            # behind `miaz add`.
            basename = util.filename_upper(util.filename_normalize(source))
            target = free_target(docs_dir, basename)
            if util.filename_import(source, target):
                imported.append(os.path.basename(target))
            else:
                failed.append(os.path.basename(source) if source else str(source))
        except Exception as error:
            failed.append(os.path.basename(source) if source else str(source))
            util.log.error(f"Could not import '{source}': {error}")
    return imported, failed
