---
DocType: How-to guide
Feature: Plugins, Documents
HelpId: plugin-autoscan
Order: 611
Plugin: MiAZAutoScan
Section: Plugins for documents
Summary: Scan pages with a SANE scanner and file them straight into the repository.
---

# Scan and import automatically

MiAZAutoScan drives your scanner directly and puts each scan in the
repository, named with defaults you choose. It needs `scanimage`, from the SANE
tools (`sane-backends`); without it the plugin says so and how to install it.

## Set it up {#setup}

1. Enable the plugin in **Repository settings > Plugins**.
2. In **Repository settings > Settings**, under **Scanner settings**, choose the
   **Scanner device**, **Source** (flatbed or document feeder), **Color
   mode**, **Resolution** and **Format**.
3. Under **Default filename fields**, pick the values new scans get. Empty
   fields stay empty, and Sent by defaults to `SCAN`.

## Scan {#scan}

1. Press **Add** in the header bar, or right-click, and choose **Scan and
   import (auto)**.
2. Pick the source when the scanner offers more than one. A feeder scans every
   page in it.

Each page is imported as a document dated today. Names with empty fields wait
in [Review](howto-review-documents.md) until you complete them.
