---
DocType: Reference
Feature: Plugins, Documents
HelpId: plugin-oikos-reference
Order: 620
Plugin: MiAZOikos
Related: plugin-miazoikos.md, explanation-miazoikos-amounts.md
Section: Plugins
Since: "0.5"
Summary: The filter choices, the Amount column, the totals view, amount formats and storage of MiAZOikos.
---

# Income and expenses reference

## Record {#record}

| Field | Values |
|---|---|
| Type | Income, Expense; Neither (rename dialog tab only) removes the record |
| Currency | Any ISO 4217 code enabled in Metadata > Currencies |
| Amount | Zero or more, up to four decimals; never negative |

## Amount formats {#formats}

| Typed | Read as |
|---|---|
| `1500`, `1500.50`, `1500,50` | 1500, 1500.50, 1500.50 |
| `1.500`, `1,500` | 1.50 (a single separator is the decimal one) |
| `1.500,50`, `1,500.50` | 1500.50 (with two separators, the last one is decimal) |
| `1.234.567` | 1234567 (one separator repeated groups thousands) |
| `-5`, `abc`, `1.23456` | refused |

Amounts are shown without a thousands separator, with the decimal point of
the desktop's regional format: `1500,00 EUR` or `1500.00 EUR`.

## Sidebar filter {#filter}

| Choice | Shows |
|---|---|
| Any amount | every document (the filter is off; Clear filters selects it) |
| Income | documents recorded as an income |
| Expense | documents recorded as an expense |
| With an amount | documents with an income or an expense |
| Without an amount | documents with nothing recorded |

The filter combines with the other sidebar filters.

## Amount column {#column}

| Document | Cell |
|---|---|
| Expense | negative, red: `−650,40 EUR` |
| Income | no sign, green: `1500,00 EUR` |
| Nothing recorded | empty |

Sort order: documents with an amount first, grouped by currency, from the
largest expense to the largest income.

## Income and expenses view {#view}

| Selection | Documents counted | Line above the chart |
|---|---|---|
| None | every document the filters leave on screen | "3 of 5 documents shown counted" |
| Some | the selected documents | "2 of 2 selected documents counted" |

- One card per currency: income, expense, net.
- Chart grouping: total, year, month, group, sender, purpose.
- Hovering a bar: income, expense, net, number of documents.
- Documents with nothing recorded are listed as not counted.
- **Set income or expense…** in the view edits the documents it counts.

## Menu entries {#menu}

Right-click > **Documents > Annotation**:

| Entry | Does |
|---|---|
| Set income or expense… | record the selected documents |
| Clear income or expense | remove their records |
| Show income and expenses | open the view |
| Manage currencies | open Metadata > Currencies |

## Storage {#storage}

`<repository>/.conf/plugins/MiAZOikos/data/MiAZOikos.json`. Records follow a
document when it is renamed, are removed when it is deleted, and are included
in **Backup & Restore**.
