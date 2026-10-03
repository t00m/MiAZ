---
DocType: Explanation
Feature: Development
HelpId: dev-architecture
Level: advanced
Order: 910
Section: For developers
Summary: "How MiAZ is built: the filename as database, three layers, services and signals."
---

# How MiAZ is built

MiAZ is a Python application on GTK 4 and libadwaita, through PyGObject. It
needs Python 3.9, GTK 4.10 and libadwaita 1.7 at least, and is built with Meson.

## The directory is the database {#no-database}

There is no database. A document's metadata is its file name, seven fields
separated by `-`:

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}
```

The repository's vocabularies (countries, groups, people, purposes) and the
plugin data live in a `.conf` folder inside the repository. Everything else is
recomputed from the file names.

## Three layers {#layers}

| Layer | Folder | May use |
|---|---|---|
| Backend | `MiAZ/backend/` | Python, GLib, Gio, GObject signals. No GTK, Adw or Gdk widgets |
| Services | `MiAZ/frontend/desktop/services/` | GTK, for application-wide behaviour (actions, dialogs, plugins) |
| Widgets | `MiAZ/frontend/desktop/widgets/` | GTK and libadwaita widgets |

The command line (`MiAZ/frontend/console/`) runs on the backend alone, with no
display. `tests/test_boundaries.py` fails the build when the backend imports a
toolkit or when the command line imports GTK.

## Services and widgets {#registry}

The application object keeps two registries:

```python
util = app.get_service('util')            # backend and frontend services
workspace = app.get_widget('workspace')   # named widgets
```

The most used services are `util` (file operations), `repo` (the open
repository), `index` (file name to document item), `actions`, `dialogs` and
`plugin-system`.

## Signals {#signals}

The backend tells the frontend what happened through GObject signals, for
example `filename-added`, `filename-renamed` and `filename-deleted` on `util`,
`repository-switched` on `repo`, and `index-changed` on `index`. Connect to
them instead of polling, and disconnect what you connected when you are done.

## Background work {#threads}

Never block the main loop. Run slow work with `run_in_background` from
`MiAZ/backend/tasks.py`, which hands the result back on the main loop:

```python
from MiAZ.backend.tasks import run_in_background

run_in_background(lambda: scan(path), on_done=self._apply, name='scan')
```

## Where to read more {#more}

`AGENTS.md` at the top of the repository is the full reference: every service,
signal, plugin helper and known pitfall.
