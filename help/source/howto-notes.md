---
DocType: How-to guide
Feature: Notes
HelpId: notes
Level: basic
Order: 410
Related: plugin-miazocr.md
Section: Notes
Summary: Write notes on documents, find them again, and back them up.
---

# Write notes on documents

A note is text you keep next to a document: what was agreed on the phone,
why a bill was disputed, a reminder. Notes are written in Markdown.

## Add a note {#add}

1. Select one or more documents.
2. Press <kbd>Ctrl</kbd>+<kbd>N</kbd>, or right-click and open **Documents >
   Annotation > Notes > Create a new note**.
3. Write the note. Under **Details** you can set the category, priority and
   status.
4. Press **Save**.

With several documents selected, the same note is filed against each of them:
useful for a batch that arrived together, such as the papers from one
appointment.

## Find notes {#find}

- In the document list, the **Notes** column shows how many notes a document
  has.
- In the sidebar, **Only with notes** keeps the documents that have some.
- When the one selected document has notes, a pin button appears in the
  header bar. Press it to see them.
- <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>N</kbd>, or **See all notes…** in the
  same menu, opens the **Notes** page with every note of the repository.

## Edit or delete a note {#edit}

Open the notes of a document (the pin button, or the **Notes** page), select
one and press **Edit**, then **Save** or **Discard**. **Delete** removes it after asking; it cannot be undone.

## Back up and restore notes {#backup}

Right-click and open **Documents > Annotation > Notes**:

- **Backup notes** saves every note of the repository into a ZIP file.
- **Restore notes** brings them back from such a file.

Notes are also included in a backup of the repository configuration, see
[Back up and restore](howto-backup-restore.md).

## Notes from scanned documents {#ocr}

The [OCR plugin](plugin-miazocr.md) reads the text of a scanned PDF and saves
it as a note, so the scan becomes searchable.
