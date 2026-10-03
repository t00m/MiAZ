---
DocType: Reference
Feature: Search, Documents
HelpId: views
Order: 320
Related: howto-search-filter.md
Section: Find documents
Summary: The five ways to see documents, the preview and the column chooser.
---

# Views

The buttons at the left of the toolbar switch the view. All views show the
same filtered documents and share one selection.

| View | Shortcut | Shows |
|---|---|---|
| Details | <kbd>Ctrl</kbd>+<kbd>1</kbd> | a table with one column per field |
| Grid | <kbd>Ctrl</kbd>+<kbd>2</kbd> | a thumbnail per document |
| Timeline | <kbd>Ctrl</kbd>+<kbd>3</kbd> | documents in date order, with the years marked |
| Conversations | <kbd>Ctrl</kbd>+<kbd>4</kbd> | documents grouped by Concept, sent on one side, received on the other |
| Filenames | <kbd>Ctrl</kbd>+<kbd>5</kbd> | the plain file names |

Plugins can add more views, for example **Income and expenses** and
**Contacts**.

## Details {#details}

- Click a column header to sort by it.
- **Choose the columns to show** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>)
  hides or shows columns.
- **Notes** column: how many notes a document has.
- **Copy** column: appears after a duplicate check finds documents with the
  same content.

## Grid {#grid}

The page size controls at the right of the toolbar set how many thumbnails a
page holds.

## Timeline {#timeline}

When the documents shown involve exactly two parties, the timeline splits into
two columns, one per side, so a correspondence reads as an exchange.

## Conversations {#conversations}

Documents with the same Concept form one conversation. What you sent is on one
side and what you received on the other, so an invoice and its payment read as
one exchange. Case and underscores in the Concept do not matter.

## Preview {#preview}

<kbd>F8</kbd> opens or closes a preview of the selected document.

## Remote repositories {#remote}

Grid, Timeline and Conversations are unavailable while a repository is marked
remote, because they read every file. See [Repositories on a
network](howto-remote-repository.md).
