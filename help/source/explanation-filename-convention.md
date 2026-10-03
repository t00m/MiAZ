---
DocType: Explanation
Feature: Documents, Renaming
HelpId: filename-convention, review=#review
Level: basic
Order: 120
Section: Get started
Summary: The seven fields every document name carries, and what happens when one is unknown.
---

# How documents are named

MiAZ does not keep a database. Everything it knows about a document is in its
file name, so the name follows a fixed shape of seven fields separated by `-`.

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}
```

For example:

```
20240315-ES-HOU-BANKNAME-INV-Q1invoice-JOHNDOE.pdf
```

## The seven fields {#fields}

| Field | Meaning | Example |
|---|---|---|
| Date | The date of the document, as `YYYYMMDD` | `20240315` |
| Country | Where it comes from | `ES` |
| Group | The area of your life it belongs to | `HOU` |
| Sent by | Who sent it | `BANKNAME` |
| Purpose | What kind of document it is | `INV` |
| Concept | Free text that describes it | `Q1invoice` |
| Sent to | Who received it | `JOHNDOE` |

Every field except Date and Concept takes a value from a list you control in
**Repository settings**. You can add your own values, and you only see the ones
you enabled.

## The Concept links documents {#concept}

The Concept is the one free field, and it does more than describe. Documents
with the same Concept belong together: every payment of the same loan, a
request and its answer. The **Conversations** view groups them, and the
[Related plugin](plugin-miazrelated.md) finds them from any one of them.

Case and underscores do not matter when Concepts are compared:
`home_insurance`, `Home Insurance` and `HOME_INSURANCE` are the same, so
reusing a Concept does not depend on typing it exactly as last time.

## Where the date comes from {#date}

When MiAZ fills in a date it reads the date stored inside the file first (a
PDF's creation date, a photo's EXIF date, an office document's created date),
and only then a date in the original file name. File names are full of numbers
that look like dates, such as invoice and policy numbers, and a date field
inside the file cannot be confused that way. It is still a claim by whatever
program wrote the file, so the rename dialog shows it before anything is
applied.

## Documents waiting for review {#review}

When a name does not have seven fields, or one of its values is not enabled in
the repository, MiAZ cannot file the document. It goes to the **Review** list,
and a **Review** button appears in the header bar.

Open the list and rename each document there. Once its name is complete and
every value is known, it leaves the list.

## Unknown dates {#unknown-date}

When MiAZ cannot read a date from a document, it uses `99991231` instead of
guessing. These documents sort at the end of the list, so they are easy to find
and fix.
