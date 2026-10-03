---
DocType: Reference
Feature: Repositories, Settings
HelpId: repository-settings
Order: 520
Related: howto-repositories.md
Section: Repositories
Summary: The four tabs of Repository settings, and what each one holds.
---

# Repository settings

Open with <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd>. Everything here
belongs to the repository on screen and is stored in its `.conf` folder.

## Repository {#repository}

| Item | Meaning |
|---|---|
| Name | the repository's name |
| Location | the folder holding its documents |
| Remote repository | for a folder on a network; see [Repositories on a network](howto-remote-repository.md) |
| Detected | the file system the folder is on, as the system reports it |

## Metadata {#metadata}

One page per vocabulary: countries, groups, purposes, senders, recipients,
and those added by plugins (currencies, periodicities, projects).

Each page has two lists:

| List | Holds |
|---|---|
| Available | every value the repository knows |
| Enabled | the values offered in the rename dialog and the filters |

**Add**, **Edit** and **Remove** act on the available values; **Enable** and
**Disable** move a value between the lists. A document whose name uses a value
that is not enabled waits for review.

## Plugins {#plugins}

The same two lists as a vocabulary: **Available** holds every installed
plugin, **Enabled** the ones this repository uses. **Enable** and **Disable**
move a plugin between them. A plugin is enabled for this repository only.

## Settings {#settings}

Settings of the enabled plugins, grouped by category, for example the default
currency, the scanner device or the workspace font.
