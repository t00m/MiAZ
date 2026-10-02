---
DocType: How-to guide
Feature: Documents, Renaming
HelpId: review-fix
Level: basic
Order: 240
Related: explanation-filename-convention.md, plugin-miazdoctor.md
Section: Add and name documents
Summary: Find the documents MiAZ cannot file yet and fix their names or the vocabulary.
---

# Fix documents waiting for review

A document waits for review when its name does not have seven fields, or when
one of its values is not enabled in the repository. See
[Documents waiting for review](explanation-filename-convention.md#review) for
why.

## Show them {#show}

1. Press **Review** in the toolbar above the documents. It appears only when
   there is something to review.
2. The list now holds only those documents.

## Fix a name {#rename}

1. Select a document and press <kbd>F2</kbd>.
2. Fill in the missing fields, or pick a known value where the name has an
   unknown one.
3. Press **Rename**. The document leaves the list once its name is complete.

To fix many at once, select them and use mass renaming
(<kbd>Ctrl</kbd>+<kbd>M</kbd>), see [Rename many documents at
once](howto-mass-rename.md).

## Or enable the value {#enable-value}

When the value in the name is right but the repository does not know it yet:

1. Open **Repository settings** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd>)
   and go to **Metadata**.
2. Choose the field, add the value to the available list if it is not there,
   and **Enable** it.

Every document using that value leaves the review list at once.

## Find them all at once {#doctor}

With the [Doctor plugin](plugin-miazdoctor.md), **Run repository health check**
lists every unknown value and every badly named document, with a button that
shows them in the list.
