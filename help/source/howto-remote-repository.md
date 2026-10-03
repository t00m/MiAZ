---
DocType: How-to guide
Feature: Repositories
HelpId: remote
Level: advanced
Order: 540
Section: Repositories
Summary: Keep MiAZ fast with a repository on a network share or a mounted cloud folder.
---

# Repositories on a network

When a repository lives on a network share, an sshfs or rclone mount, or any
place where opening a file means fetching it, mark it remote.

## Mark a repository as remote {#mark}

1. Open **Repository settings** (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd>).
2. In **Repository**, turn on **Remote repository**.

MiAZ never sets this for you. **Detected** shows what the system reports, but
an rclone mount reports itself as local and an encrypted folder on your own
disk can report itself as a network one, so neither answer is reliable enough
to act on.

## What changes {#changes}

| While remote | Why |
|---|---|
| Grid, Timeline and Conversations are unavailable | each reads one file per row |
| The duplicate check does not run | it reads every file that shares a size with another |
| Changes are checked every 30 seconds | a mount does not report files added from another computer |
| The checking stops while the window is not on screen | nothing to show it to |

Details, Filenames and the preview of the selected document keep working.

## Turn it off {#off}

Switch **Remote repository** off. Everything comes back at once, with no
restart.
