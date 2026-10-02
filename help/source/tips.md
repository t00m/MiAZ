---
Feature: Documents, Renaming, Notes, Repositories
HelpId: tips
Kind: tips
Order: 410
Section: Help
Summary: Small things MiAZ does for you that are easy to miss.
---

# Tips

## The Concept field links documents {#concept-links}

Give documents that belong together the same Concept. Case and underscores do
not matter: `home_insurance`, `Home Insurance` and `HOME_INSURANCE` count as
the same.

## An exchange reads as a conversation {#conversations}

The **Conversations** view (<kbd>Ctrl</kbd>+<kbd>4</kbd>) groups documents by
Concept and puts what you sent on one side and what you received on the other.
An invoice and its payment read as one exchange.

## MiAZ reads the date from the document, not from its name {#date-from-metadata}

A file name is full of numbers that look like dates: invoice numbers, policy
numbers, IDs. The date stored inside the file cannot be confused that way, so
MiAZ reads it first.

## One note for several documents {#note-many}

Select several documents and press <kbd>Ctrl</kbd>+<kbd>N</kbd>. You write the
note once and it is attached to all of them.

## Plugins are chosen per repository {#plugins-per-repository}

A work archive and a family archive can have different plugins enabled, each
with its own settings.

## Repositories on a network {#remote}

If a repository lives on a network share or a mounted cloud folder, turn on
**Remote repository** in **Repository settings**. MiAZ then stops reading every
file to draw thumbnails, and checks for changes every 30 seconds instead of
waiting for the system to tell it. Turn it off and everything comes back at
once.
