---
DocType: How-to guide
Feature: Development
HelpId: dev-help
Level: advanced
Order: 940
Section: Developers
Summary: Write and build these help pages, and link a part of the application to one.
---

# Write help pages

This help is built from `help/source/` by KB4IT with its `apphelp` theme, and
published to GitHub Pages from the `main` branch.

## Keep it current {#rule}

Every change to the code is checked against the help, in the same commit:

- the user pages, when the change alters what a user sees or does;
- these developer pages, when it alters how MiAZ is built, run, tested or
  extended.

## One type per page {#doctype}

The help follows [Diátaxis](https://diataxis.fr/): every page is exactly one
type of document, and the theme refuses to publish a page that is not.

| `DocType` | The page | Example here |
|---|---|---|
| `Tutorial` | takes a newcomer through a lesson, step by step | Get started with MiAZ |
| `How-to guide` | solves one task for someone who knows what they want | Add documents |
| `Reference` | describes, in tables and lists, without instructions | Keyboard shortcuts |
| `Explanation` | says how or why something works | How documents are named |

When a page needs two of these, write two pages and link them with
`Related`. The MiAZOikos help is the example: a how-to guide, a reference and
an explanation.

`Layout` changes how a page is drawn, not what it is: `faq` (each `##` is a
collapsible question, usually a Reference), `tips` (each `##` is a card,
usually a How-to guide) or `troubleshooting` (each `##` is a problem with
`### Cause` and `### Fix`, usually a How-to guide).

## A page {#page}

One Markdown file per page, in `help/source/`, no subfolders:

```markdown
---
DocType: How-to guide
Feature: Documents
HelpId: add-documents
Level: basic
Order: 210
Section: Documents
Summary: One line, 160 characters at most.
---

# Add documents

## Add a folder {#folder}
```

- `DocType`, `Section`, `Order`, `Summary` and `Feature` are required.
- `DocType` is spelled exactly as in the table above. A page without a valid
  one is left out of the site and fails the build.
- `Feature` and `Level` values must be in the vocabulary in
  `help/config/repo.json`.
- `Related` lists file names of pages to show first under "Related pages".
- Quote a value that contains `: `, such as `Summary: "A: b"`.
- Give a heading an explicit id (`{#folder}`) when anything links to it.
- Link to another page as `[text](page.md#anchor)`.
- Images go in `help/source/resources/images/`.

## Opening a page from MiAZ {#help-ids}

`HelpId: add-documents` names a page; `HelpId: add-folder=#folder` names a
section. MiAZ opens one with:

```python
app.get_service('actions').open_help('add-folder')
```

Every id the application or a plugin uses must be listed in
`help/config/contract.txt`. The build fails when one of them no longer exists,
so renaming a page or a heading cannot silently break the application.

## Build it {#build}

```bash
pip install 'git+https://github.com/t00m/KB4IT@0fd6bb810331376b27f1efbc0f89755c69699b93'
kb4it build help/config/repo.json --force
xdg-open help/target/index.html
```

A build with no warnings is the target. `help/target/` and `help/var/` are
build output and are not committed.

The installed MiAZ does not read `help/target/`: `meson install` builds the
help again into the build directory and installs that copy, so after editing
a page, reinstall to see it in the application. Run from the source tree,
MiAZ reads `help/target/` directly. A KB4IT too old for these pages makes
meson warn and keep the last copy built by hand; `-Dhelp=enabled` turns that
into an error.
