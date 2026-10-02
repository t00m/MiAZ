---
Feature: Development
HelpId: dev-help
Kind: howto
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

## A page {#page}

One Markdown file per page, in `help/source/`, no subfolders:

```markdown
---
Feature: Documents
HelpId: add-documents
Kind: howto
Level: basic
Order: 210
Section: Documents
Summary: One line, 160 characters at most.
---

# Add documents

## Add a folder {#folder}
```

- `Kind`, `Section`, `Order`, `Summary` and `Feature` are required.
- `Kind` is one of `tutorial`, `howto`, `reference`, `explanation`, `faq`,
  `tips`, `troubleshooting`.
- `Feature` and `Level` values must be in the vocabulary in
  `help/config/repo.json`.
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
pip install 'KB4IT==0.7.9'
kb4it build help/config/repo.json --force
xdg-open help/target/index.html
```

A build with no warnings is the target. `help/target/` and `help/var/` are
build output and are not committed.
