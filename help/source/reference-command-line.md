---
DocType: Reference
Feature: Search, Documents, Repositories
HelpId: command-line
Order: 730
Section: Reference
Summary: The miaz command, for searching and changing a repository from a terminal.
---

# Command line

`miaz` with no command opens the window. With a command it works in the
terminal, without a display. Every command takes `--repo NAME_OR_PATH` to
choose the repository; without it, the default one is used, and the default is
never changed.

| Command | Does |
|---|---|
| `miaz search [TEXT]` | find documents |
| `miaz repos` | list repositories |
| `miaz add PATH…` | add files or folders to the repository |
| `miaz delete DOCUMENT…` | delete documents |
| `miaz rename DOCUMENT` | change fields of a document name |
| `miaz fields FIELD` | list or change the values of a field |
| `miaz notes [TEXT]` | read the notes on documents |
| `miaz ocr DOCUMENT…` | read the text of documents with OCR and save it as a note (needs the [OCR plugin](plugin-miazocr.md) enabled) |

`miaz --version` prints the version; `miaz COMMAND --help` lists every option.

## search {#search}

| Option | Meaning |
|---|---|
| `TEXT` | free text, in any field |
| `--concept CONCEPT` | part of the Concept |
| `--country`, `--group`, `--sentby`, `--purpose`, `--sentto TEXT` | part of the code or of its description; `none` for documents without one |
| `--since PERIOD` | `this-month`, `past-month`, `last-3-months`, `last-6-months`, `last-12-months`, `2-years`, `3-years`, `5-years`, `10-years`, `future` |
| `--from YYYYMMDD`, `--to YYYYMMDD` | dated on or after, on or before |
| `--pending` | only documents waiting for review |
| `--all` | include documents with values the repository does not know |
| `--limit N` | at most N results |
| `--long` | a table with descriptions |
| `--json` | JSON records |

The search means the same as the sidebar filters in the window.

## add {#add}

| Option | Meaning |
|---|---|
| `PATH…` | files or folders |
| `--recursive`, `-r` | include the subfolders of a folder |

## delete {#delete}

| Option | Meaning |
|---|---|
| `DOCUMENT…` | names as `miaz search` prints them |
| `--yes`, `-y` | do not ask; needed when there is no terminal to ask on |

## rename {#rename}

| Option | Meaning |
|---|---|
| `DOCUMENT` | the name as `miaz search` prints it |
| `--date YYYYMMDD`, `--concept TEXT` | new date or concept |
| `--country`, `--group`, `--sentby`, `--purpose`, `--sentto CODE` | a code the repository has; see `miaz fields` |

## fields {#fields}

| Option | Meaning |
|---|---|
| `FIELD` | `country`, `group`, `sentby`, `purpose` or `sentto` |
| `--list` | keys and descriptions (also what naming a field alone does) |
| `--add KEY DESCRIPTION` | add a key, or describe one |
| `--remove KEY` | remove a key, unless documents still use it |
| `--json` | JSON records |

## notes {#notes}

| Option | Meaning |
|---|---|
| `TEXT` | free text in the note, its header or the document name |
| `--document`, `--category`, `--status`, `--priority TEXT` | only notes matching |
| `--full` | print each note in full |
| `--limit N`, `--long`, `--json` | as in `search` |

## ocr {#ocr}

| Option | Meaning |
|---|---|
| `DOCUMENT…` | names as they are in the repository |
| `--language LANGUAGE` | language the OCR engine should assume |
| `--force` | ignore any existing text layer and read every page |
