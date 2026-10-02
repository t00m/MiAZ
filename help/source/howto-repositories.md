---
DocType: How-to guide
Feature: Repositories
HelpId: repositories
Level: basic
Order: 510
Related: reference-repository-settings.md
Section: Repositories
Summary: Create a repository, switch between repositories, and choose the one MiAZ opens.
---

# Create and switch repositories

A repository is a folder of documents with its own vocabularies, plugins and
settings. You can keep several, for example one for home and one for work.

## Create the first one {#first}

The first time MiAZ starts, an assistant creates it. See [Get started with
MiAZ](getting-started.md#create-repository).

## Add another repository {#add}

1. Open **Repository management** (<kbd>Ctrl</kbd>+<kbd>R</kbd>).
2. Press **Add** above the available list.
3. Type a **Repository name** and choose its **Location**, an existing folder.
4. Select it in the available list and press **Enable**.

## Switch to another repository {#switch}

1. Open **Settings** (<kbd>Ctrl</kbd>+<kbd>,</kbd>).
2. In **Active repository**, pick the repository.
3. Confirm. Tick **Set as the default repository** to open it the next time
   MiAZ starts too.

The documents, vocabularies and plugins of the new repository replace the ones
on screen. MiAZ does not restart.

## Rename or remove a repository {#edit}

In **Repository management**, select it and press **Edit** to change its
description or location.

To remove it, **Disable** it first, then select it in the available list and
press **Remove**. MiAZ forgets the repository; its folder and its documents
stay where they are.

## Turn plugins on and off {#plugins}

Plugins are enabled per repository, so a work archive and a family archive can
use different tools, each with its own settings.

1. Open **Repository settings** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd>).
2. Go to **Plugins**.
3. Select the plugin in the available list and press **Enable**, or select it
   in the enabled list and press **Disable**.

If a plugin needs another one, MiAZ asks to enable both.

Settings of enabled plugins appear in the **Settings** tab of the same window.
Some plugins need extra Python libraries; MiAZ offers to install them, see
[Application settings](reference-settings.md#libraries).
