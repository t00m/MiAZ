---
DocType: How-to guide
Feature: Plugins, Documents
HelpId: plugin-oikos
Level: basic
Order: 640
Plugin: MiAZOikos
Related: reference-miazoikos.md, explanation-miazoikos-amounts.md
Section: Plugins for documents
Since: "0.5"
Summary: Record documents as income or expense, then filter them and see their totals.
---

# Record income and expenses

The MiAZOikos plugin records what a document is worth: money coming in or
going out, how much, and in what currency. For every choice and format, see
[Income and expenses reference](reference-miazoikos.md).

## Turn the plugin on {#enable}

1. Open **Repository settings** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd>).
2. Go to **Plugins** and enable **MiAZOikos**.

Plugins are enabled per repository.

## Choose your currencies {#currencies}

1. Open **Repository settings > Metadata > Currencies**, or right-click a
   document and open **Documents > Annotation > Manage currencies**.
2. Enable the currencies you use.
3. In **Repository settings > Settings**, pick the **Default currency** new
   records start with.

## Record one document {#one}

1. Select the document and press <kbd>F2</kbd>.
2. Open the **Income or expense** tab.
3. Choose **Income** or **Expense**, the currency and the amount.
4. Press **Rename**. The amount is saved even if the name did not change.

To remove a record, choose **Neither**. **Cancel** changes nothing.

## Record many documents {#many}

1. Select the documents.
2. Right-click the selection and open **Documents > Annotation > Set income
   or expense…**.
3. Choose the type and the currency.
4. Keep **Same amount for all documents** for one shared amount, or untick it
   to type one amount per document.
5. Press **Apply**.

Type amounts without a thousands separator: `1500,50` or `1500.50`.

## Find the documents still to record {#missing}

1. In the sidebar, set the income or expense filter to **Without an amount**.
2. Select what is listed and record it as above.

## See the totals {#totals}

1. Narrow the documents with the sidebar filters, for example a year and
   **Expense**.
2. Switch to the **Income and expenses** view, or right-click and open
   **Documents > Annotation > Show income and expenses**.
3. To count only some of the documents shown, select them first.

The totals follow the filters while the view is open.

## Sort by amount {#sort}

In **Details**, click the **Amount** column header. To hide or show the column,
use **Choose the columns to show** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>).
