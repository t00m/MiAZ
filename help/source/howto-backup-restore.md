---
DocType: How-to guide
Feature: Repositories
HelpId: backup
Level: basic
Order: 530
Section: Repositories
Summary: Back up the documents, the configuration or the whole repository, and restore them.
---

# Back up and restore

## Back up {#backup}

1. Open **Settings** (<kbd>Ctrl</kbd>+<kbd>,</kbd>) and go to **Backup &
   Restore**.
2. Pick the **Target repository**.
3. Choose **Backup** and what to process:
   - **Backup files**: copies the documents into a folder.
   - **Backup configuration**: saves the `.conf` folder (vocabularies,
     plugins, notes, plugin data) as one archive.
   - **Backup repository**: saves documents and configuration as one archive.
4. Press **Proceed** and choose the destination folder.

## Restore {#restore}

1. In the same page, choose **Restore** and what to bring back: **Restore
   files**, **Restore configuration** or **Restore repository**.
2. Press **Proceed** and choose the backup.

MiAZ restarts when you close the result of a restore.

!!! warning
    Restoring the configuration replaces the current one. Back it up first if
    you may want it again.

## Notes only {#notes}

To save just the notes, see [Back up and restore
notes](howto-notes.md#backup).

## Other copies {#other}

The documents are ordinary files, so any backup tool can copy the repository
folder as well. The [History plugin](plugin-miazhistory.md) keeps a record of
changes inside MiAZ, so a single change can be undone.
