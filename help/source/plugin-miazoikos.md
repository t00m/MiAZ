---
Feature: Plugins, Documents
HelpId: plugin-oikos
Kind: howto
Level: basic
Order: 610
Plugin: MiAZOikos
Section: Plugins
Since: "0.5"
Summary: Record documents as income or expense and see their totals per currency.
---

# Income and expenses

The MiAZOikos plugin lets you say what a document is worth: whether it is money
coming in or going out, how much, and in what currency. A view next to
Details, Grid and Timeline then adds up the documents you select, or every
document shown when you select none.

## Turn it on {#enable}

Open **Repository settings** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd>),
go to **Plugins** and enable **MiAZOikos**. Plugins are enabled per repository.

## Record one document {#one}

1. Select the document and press <kbd>F2</kbd>.
2. Open the **Income or expense** tab.
3. Choose **Income** or **Expense**, the currency and the amount.
4. Press **Rename**. The amount is saved even if the name did not change.

Choose **Neither** to remove what was recorded. **Cancel** changes nothing.

## Record many documents {#many}

1. Select the documents.
2. Right-click the selection and open **Documents > Annotation > Set income
   or expense…**.
3. Choose the type and the currency.
4. Keep **Same amount for all documents** for one shared amount, or untick it
   to type one amount per document.
5. Press **Apply**.

!!! note
    If the selected documents already differ in type or currency, nothing is
    preselected. Choose both on purpose, so one click cannot turn a salary
    into a bill or dollars into euros.

## The Amount column {#column}

While the plugin is on, the **Details** table has an **Amount** column with
each document's amount and currency:

- an expense is negative and red: `−650,40 EUR`
- an income has no sign and is green: `1500,00 EUR`
- a document with nothing recorded shows nothing

Click the header to sort: documents with an amount come first, grouped by
currency, from the largest expense to the largest income. Hide or show the
column with **Choose the columns to show**
(<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>).

## Typing amounts {#amounts}

Write the amount without a thousands separator. Both `1500,50` and `1500.50`
work.

A single separator is always the decimal one, in every language: `1.500` is
one and a half, not fifteen hundred. With two separators, the last one is the
decimal one, so `1.500,50` and `1,500.50` both mean 1500.50.

MiAZ shows amounts the same way, without a thousands separator
(`1500,00 EUR`), so what you see can be typed back as it is.

## See the totals {#view}

Switch to the **Income and expenses** view, or right-click and open
**Documents > Annotation > Show income and expenses**. What it adds up
depends on the selection:

- **Nothing selected**: every document the filters leave on screen. Narrow
  the list with the sidebar (a sender, a year, a search) to get the totals of
  just those documents. The totals change as you change the filters.
- **Documents selected** in Details, Grid or Timeline: only those.

The line above the chart says which: "3 of 5 documents shown counted" or
"2 of 2 selected documents counted".

- One card per currency shows income, expense and net.
- The chart can be grouped by total, year, month, group, sender or purpose.
- Hover a bar to see its income, expense, net and number of documents.
- Documents with nothing recorded are not counted. The view says how many
  there are and offers to set them.
- **Set income or expense…** in the view edits the documents it is adding up:
  the selection, or everything shown.

Currencies are never converted or added together. Each one has its own card
and its own chart.

## Currencies {#currencies}

Enable the currencies you use in **Repository settings > Metadata >
Currencies**, or right-click and open **Documents > Annotation > Manage
currencies**. Choose
the currency new documents start with in **Repository settings > Settings >
Default currency**.

## Where the amounts are kept {#storage}

In the repository, in `.conf/plugins/MiAZOikos/data/MiAZOikos.json`. They
follow a document when you rename it, are removed when you delete it, and are
included in **Backup & Restore**.
