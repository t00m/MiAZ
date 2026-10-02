---
DocType: How-to guide
Feature: Plugins, Repositories
HelpId: plugin-doctor
Order: 681
Plugin: MiAZDoctor
Related: howto-review-documents.md
Section: Plugins for the repository
Summary: Check the whole repository for problems in one pass, and repair its vocabulary.
---

# Check the health of a repository

## Run the check {#run}

1. Enable the plugin in **Repository settings > Plugins**.
2. Right-click and open **Repository > Health > Run repository health
   check**.

To run it every time the repository opens, turn on **Check the repository
when it opens** in **Repository settings > Settings**. It runs in the
background. When something is wrong the report opens by itself; for anything
less a message offers to **Open** it, and a clean repository just says so.

## Read the report {#report}

Findings are grouped by how much they matter:

| Group | Findings |
|---|---|
| **Problems**: these stop documents being filed or found | documents that cannot be read; documents not named in seven fields; values used by documents and missing from the vocabulary |
| **Worth cleaning**: nothing is broken, but the repository is drifting | documents of zero length; groups of documents with identical content; values described by nothing but themselves |
| **Notes**: tidying, whenever it suits | values no document uses; the duplicate check not run on a remote repository |

## Act on a finding {#act}

- **Show** narrows the document list to the documents of that finding. A tag
  above the list marks it; remove the tag to see everything again.
- For a value without a description, type one and press **Save**.
- For a value nobody uses, **Remove** takes it out of the vocabulary.

Duplicates are compared by content, not by name: two copies under different
names are found too. Keep one of each group and delete the rest.
