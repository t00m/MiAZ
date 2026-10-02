---
DocType: How-to guide
Feature: Plugins, Repositories
HelpId: plugin-history
Order: 682
Plugin: MiAZHistory
Section: Plugins for the repository
Summary: Undo and redo changes to the repository, one at a time.
---

# Undo and redo changes

MiAZHistory keeps every change to the repository, so any of them can be taken
back: a rename, an added or deleted document, a change of settings.

## Turn it on {#enable}

1. Enable the plugin in **Repository settings > Plugins**.
2. MiAZ asks **Keep a history of this repository?** and says how much disk
   space it needs. Accept. The first copy takes a few minutes.

The history is stored with the `git` program. If it is not installed, the
plugin says that one program is missing.

## Undo and redo {#undo}

Two buttons in the header bar step back and forward. Hover one to see which
change it would undo or redo and when it was made; MiAZ asks before applying
it, then reloads the repository.

## What it costs {#size}

**Repository settings > Settings** shows how many changes are kept and the
disk space they use. Nothing is pruned.
