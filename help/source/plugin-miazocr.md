---
DocType: How-to guide
Feature: Plugins, Notes
HelpId: plugin-ocr
Order: 631
Plugin: MiAZOCR
Related: howto-notes.md
Section: Plugins for documents
Summary: Read the text of scanned PDFs and keep it as a note, so scans become searchable.
---

# Extract text with OCR

MiAZOCR reads the text of PDF documents and saves it as a note on each one.
It needs `ocrmypdf`; if it is missing, the plugin refuses to start and says how
to install it (for example `sudo dnf install ocrmypdf poppler-utils` or `sudo
apt install ocrmypdf poppler-utils`).

## Extract the text {#run}

1. Select one or more PDF documents.
2. Right-click and open **Documents > Annotation > Extract text (OCR)…**.
3. Pick the **Document language**, and tick **Force OCR** to read every page
   even when the PDF already has a text layer.

The text arrives as a note on each document, see [Write notes on
documents](howto-notes.md).

## Default language {#language}

**Repository settings > Settings** holds the language the OCR engine assumes.

## From a terminal {#cli}

`miaz ocr DOCUMENT…` does the same without the window, see [Command
line](reference-command-line.md#ocr).
