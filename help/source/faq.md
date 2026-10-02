---
DocType: Reference
Feature: Getting started, Repositories
HelpId: faq
Layout: faq
Order: 740
Section: Reference
Summary: Short answers to the questions people ask most.
---

# Frequently asked questions

Short answers. Each one links to the page with the details.

## Where are my documents stored? {#storage}

In the repository folder you chose, as ordinary files with descriptive names.
Vocabularies, plugins, notes and plugin data are in a `.conf` folder inside it.
[Repository settings](reference-repository-settings.md)

## Is my original file changed when I add it? {#original}

No. MiAZ copies it into the repository and leaves the original alone.
[Add documents](howto-add-documents.md)

## Can I have more than one repository? {#repositories}

Yes. Add them in **Repository management** (<kbd>Ctrl</kbd>+<kbd>R</kbd>) and
switch in **Settings**. [Create and switch repositories](howto-repositories.md)

## Why is a document in the Review list? {#why-review}

Its name does not have seven fields, or one of its values is not enabled in the
repository. [Fix documents waiting for review](howto-review-documents.md)

## Why does a document have the date 99991231? {#unknown-date}

MiAZ could not read a date from it and did not guess.
[Unknown dates](explanation-filename-convention.md#unknown-date)

## Where did my documents go? {#hidden}

Probably a filter. Look at the tags above the list, or press
<kbd>Esc</kbd> in the document list to clear all filters. The date filter starts on recent periods;
pick **All documents** to see everything.
[Search and filter documents](howto-search-filter.md)

## Can I undo a change? {#undo}

With the [History plugin](plugin-miazhistory.md) enabled, yes: it keeps every
change to the repository and adds undo and redo buttons.

## How do I back up? {#backup}

**Settings** (<kbd>Ctrl</kbd>+<kbd>,</kbd>) > **Backup & Restore**.
[Back up and restore](howto-backup-restore.md)

## Can I use MiAZ from a terminal? {#terminal}

Yes: `miaz search`, `miaz add`, `miaz rename` and more.
[Command line](reference-command-line.md)

## Does MiAZ need internet access? {#internet}

No. Only two things go online: the [AI Assistant](plugin-miazaiassistant.md)
with a cloud provider, and this help when no copy is installed with MiAZ.
