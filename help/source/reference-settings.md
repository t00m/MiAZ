---
DocType: Reference
Feature: Settings
HelpId: settings
Order: 720
Related: reference-repository-settings.md
Section: Reference
Summary: What the Settings window holds, for the whole application.
---

# Application settings

Open with <kbd>Ctrl</kbd>+<kbd>,</kbd>. These settings apply to every
repository; what belongs to one repository is in [Repository
settings](reference-repository-settings.md).

## Preferences {#preferences}

| Item | Meaning |
|---|---|
| Active repository | the repository on screen; picking another switches to it, see [Create and switch repositories](howto-repositories.md#switch) |
| Display sidebar toggle button | shows the header bar button that hides or reveals the sidebar; <kbd>F9</kbd> works either way |

## External libraries {#libraries}

Some plugins need Python libraries that MiAZ does not ship, for example the AI
providers of the [AI Assistant](plugin-miazaiassistant.md). MiAZ installs them
in a private environment in your home folder (`~/.MiAZ/opt/venv`), never into
the system Python.

| Action | Does |
|---|---|
| Install / Update | downloads and installs the libraries the enabled plugins ask for |
| Remove | deletes them |

The row lists each installed library and the plugins that need it.

## Backup & Restore {#backup}

Backs up or restores a repository's documents, configuration or both. See
[Back up and restore](howto-backup-restore.md).
