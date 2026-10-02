---
DocType: Explanation
Feature: Plugins, Documents
HelpId: plugin-oikos-amounts
Order: 642
Plugin: MiAZOikos
Related: plugin-miazoikos.md, reference-miazoikos.md
Section: Plugins for documents
Since: "0.5"
Summary: Why MiAZOikos reads and shows amounts the way it does, and never mixes currencies.
---

# How MiAZOikos handles money

## One rule for separators {#separators}

People type amounts the way the number reached them: `1234,50` from a Spanish
invoice, `1234.50` from a bank export. MiAZOikos accepts both, so it needs one
rule that does not depend on the language of the desktop: a single separator
is always the decimal one.

The price of that rule is that `1.500` means one and a half, even where it is
the usual way to write fifteen hundred. Guessing from the number of digits
after the separator would be right more often and wrong without warning, and
a wrong amount that looks right is the worst outcome for a record of money.

## Why amounts have no thousands separator {#no-grouping}

If MiAZOikos showed `1.500,00 EUR`, someone copying that into an amount field
as `1.500` would record a thousandth of it. Shown as `1500,00 EUR`, what is on
the screen can be typed back as it is, in every language.

## Why currencies are never added together {#currencies}

Adding dollars to euros needs an exchange rate, and the right rate depends on
the day of each payment. A total made with a guessed rate is worse than two
honest totals, so every currency has its own card, its own chart section and
its own scale.

## Why nothing is preselected for mixed documents {#mixed}

When the selected documents already differ in type or currency, the editor
leaves both unchosen. Preselecting one would turn a salary into a bill, or
relabel dollars as euros, on a single click of **Apply**.

## Sign and colour {#sign}

In the Amount column an expense is negative and an income has no sign. The
sign alone tells them apart; red and green are a second cue, so the column
still reads correctly for anyone who cannot tell those colours apart.

## Exact amounts {#exact}

Amounts are stored as decimal text, never as floating point numbers, so
`0.10 + 0.20` stays `0.30` however many times a total is recomputed.
