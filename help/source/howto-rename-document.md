---
Feature: Renaming
HelpId: rename-document
Kind: howto
Level: basic
Order: 310
Section: Renaming
Summary: Rename a single document with the rename dialog, and let MiAZ detect fields for you.
---

# Rename a document

1. Select the document and press <kbd>F2</kbd>.
2. Fill in or correct the seven fields.
3. Press **Preview** to see the new name.
4. Press **Rename**.

## Let MiAZ detect fields {#detect}

The **Detect** menu in the rename dialog reads the document and fills in what it
can find:

- **Date**: from the file's own metadata first, then from the original file name.
- **Country**, **Sent by**, **Sent to**: by finding one of your enabled values in
  the document text.
- **Every field**: all of the above in one pass.

Group, Purpose and Concept are never guessed. A wrong guess there is harder to
notice than an empty field.

Nothing changes until you press **Rename**, so check the result first.
