# MiAZ UI test checklist

What the automated suite cannot reach: anything needing a display, a real
repository and a human deciding whether it looks right. Run it before tagging a
release.

## How to use it

Work top to bottom. Each item is an action and what should happen. Tick what
passes, and for anything that fails write the item number and what you saw.

**Run the automated ones first.** Items marked **[A]** are covered by
`scripts/checks/run_ui_tests.sh`, which starts the real application against a
throwaway repository and asserts on the same things you would check by hand.
Run it, and if it passes, skip those items:

```bash
scripts/checks/run_ui_tests.sh          # ~3 minutes
scripts/checks/run_ui_tests.sh --headless   # no desktop session needed
```

It never touches your own configuration: HOME points at a temporary directory
for the duration.

Three ways to run the rest, depending on how much time you have:

- **Smoke (15 minutes):** the items marked **[S]**. Enough to catch a broken
  build before sharing it.
- **Changed (30 minutes):** the items marked **[N]**, everything this release
  touched. These carry the highest risk of a regression.
- **Full:** all of it. Do this before a release you announce.

Markers: **[S]** smoke, **[N]** changed this release, **[A]** covered by the
automated UI suite, **[K]** needs a paid API key (skip unless you have one).

## Before you start

- [ ] Build and install from the tag you intend to release, not from the
      working tree: `scripts/packaging/build_all.sh --ref vX.Y.Z`
- [ ] Have two repositories registered, one with at least 50 documents and one
      nearly empty, so switching is visible.
- [ ] Have at least one document whose values are not in the configuration, so
      the Review path has something to show.
- [ ] Have a PDF, an image and a plain text file to hand for the add and
      preview paths.
- [ ] Note the version under test and the desktop (GNOME version, Wayland or
      X11, light or dark theme) in the results table at the end.

---

## 1. Start and first run

- [ ] **1.1 [S]** Launch from the applications menu. The window opens, the
      workspace lists documents, no error dialog.
- [ ] **1.2** Launch from a terminal with `miaz`. Same result, and the terminal
      shows coloured log lines.
- [ ] **1.3 [N]** Redirect the log: `miaz 2> /tmp/miaz.log`, then open the file.
      Readable text with no escape code sequences in it.
- [ ] **1.4** Quit with `Ctrl+Q`, relaunch. The window reopens at the same size
      and position, maximised if it was maximised.
- [ ] **1.5** Rename `~/.MiAZ` aside and launch. The first-run assistant offers
      to create a repository, creates it, and the app lands on an empty
      workspace. Countries is the only field it asks about; the summary reports
      every shipped group, purpose, sender and recipient as enabled, and
      Settings confirms it. Restore your `~/.MiAZ` afterwards.
- [ ] **1.6** With the app already running, launch it again. The existing window
      is raised rather than a second one opening.

## 2. Workspace

- [ ] **2.1 [S] [A]** The document list shows the columns you expect, with dates
      formatted and country, group, sender, purpose and recipient shown as
      labels rather than codes.
- [ ] **2.2** Click each column header. Sorting toggles ascending and
      descending, and the date column sorts chronologically, not as text.
- [ ] **2.3** Resize the window narrow and wide. Columns reflow, nothing is
      clipped, no horizontal scrollbar appears at normal widths.
- [ ] **2.4 [S] [A]** Select one row, then several with `Ctrl` and with `Shift`. The
      selection count and the header bar buttons update accordingly.
- [ ] **2.5** Press `Return` on a selected document. It opens in the system
      viewer.
- [ ] **2.6** Right-click a selection. The context menu appears with the actions
      that apply to that number of documents.
- [ ] **2.7 [N]** With documents that fail validation present, the Review button
      appears and shows them. Clearing the filter brings the normal view back.
- [ ] **2.8 [A]** Type in the search box. The list narrows as you type, and matches
      are case-insensitive.
- [ ] **2.9 [A]** Clear the search. The full list returns.
- [ ] **2.10 [A]** Add a file to the repository directory from outside the app (a
      file manager or `cp`). The workspace picks it up without a restart.
- [ ] **2.11 [A]** Delete a file from outside the app. The row disappears and the
      document count drops by exactly one.

## 3. Sidebar filters

- [ ] **3.1 [S] [A]** Each of the five field dropdowns filters the list, and "Any"
      restores it.
- [ ] **3.2** Type in a dropdown's search box. Entries filter, and picking one
      applies it.
- [ ] **3.3 [N] [A]** Open the date dropdown. It lists exactly eleven entries: This
      month, Since past month, Since last 3 months, Since last 6 months, Since
      last year, Since two years ago, Since three years ago, Since five years
      ago, Since ten years ago, Future, All documents.
- [ ] **3.4 [N] [A]** Pick "Since last 6 months". Only documents from the last six
      months remain, and the boundary is the 1st of the month six back.
- [ ] **3.5 [N]** Pick "Since last year". The range is the last twelve months,
      not the calendar year to date.
- [ ] **3.6 [A]** Pick "Future". Only documents dated after today remain.
- [ ] **3.7 [A]** Combine a date filter with two field filters. They narrow
      together, and the document count matches what is listed.
- [ ] **3.8** Toggle the sidebar with the header bar button. It hides and shows,
      and the setting survives a restart.

## 4. Rename dialog

- [ ] **4.1 [S] [A]** Select one document, press `Ctrl+BackSpace`. The dialog opens
      with all seven fields filled from the filename.
- [ ] **4.2 [N] [A]** Open it on a document whose values are not in the
      configuration. Those dropdowns show "Any", the affected rows are marked,
      and the **Rename button is insensitive**.
- [ ] **4.3 [N] [A]** Fill in date, country, sent by, concept and sent to. The
      Rename button becomes sensitive as soon as the last one is set.
- [ ] **4.4 [N] [A]** Clear the concept. The button goes insensitive again.
- [ ] **4.5 [A]** Leave Group and Purpose as "Any". The button stays sensitive:
      those two are advisory.
- [ ] **4.6 [A]** Type a date directly in the date field. Valid `YYYYMMDD` is
      accepted. Type `20261301`: the field keeps exactly what you typed, the
      row is marked wrong, the label next to it reads "not a date" rather than
      showing an unrelated valid date, and Rename stays insensitive.
- [ ] **4.7** Open the calendar popover and pick a day. The field updates.
- [ ] **4.7b** Click the detect button next to the date field on a document whose
      concept holds a date, such as `FACTURA_15_03_2024`. The field is set to
      `20240315`, whatever it held before. On a concept with no date it is set
      to `99991231`.
- [ ] **4.7c** Edit the concept to add a date, then click detect again. It reads
      the concept as it is now, not as the file was named on disk.
- [ ] **4.7d** Click detect on a PDF whose concept holds no date but whose PDF
      properties show a creation date (check with `pdfinfo` or a viewer). The
      field is set to that date, not to today. This works with no `pypdf` and no
      `Pillow` installed, which is the normal case.
- [ ] **4.7e** Click detect on a document that has both: a creation date in its
      properties and a digit run in its concept that looks like a date, such as
      the invoice number `RG240719880042`. The metadata date wins. The concept
      is only read when the file itself carries no date.
- [ ] **4.8** Type two characters in the concept field. The autocomplete popover
      offers matching concepts, and picking one fills the field.
- [ ] **4.9 [A]** Use the inline Add button on a restricted row. The add
      dialog appears, the new value is saved and selected. Open the manage
      window next to it twice without closing the rename dialog: it is
      populated both times.
- [ ] **4.10 [A]** Watch the filename preview as you edit. It updates on every
      change and matches what will be written.
- [ ] **4.11 [S]** Click Rename. The confirmation dialog appears.
- [ ] **4.12 [N]** Look at the confirmation text. It is **not** highlighted when
      the dialog opens. Select part of it with the mouse: selection works.
- [ ] **4.13** Confirm. The file is renamed on disk and the row updates in place.
- [ ] **4.14** Rename to a name that already exists. The error explains the
      clash and the dialog stays open.
- [ ] **4.15** With every field valid, press `Enter` from the date or concept
      field. It renames, same as clicking Rename. (There is no `Ctrl+Enter`:
      the fields activate the dialog's default button.)
- [ ] **4.16 [A]** Press `Escape`, and separately click Cancel. Both close without
      renaming and without writing anything.
- [ ] **4.17** Click Preview. The document opens in the system viewer and the
      dialog stays open.
- [ ] **4.18** Click Suggest with the concept at two or more characters. Fields
      are filled from documents sharing that concept. With a shorter concept the
      button is insensitive.

## 5. Rename dialog tabs

- [ ] **5.1** With MiAZProjectMgt and MiAZPeriodicity enabled, the dialog header
      shows a view switcher with Fields, Projects and Periodicity.
- [ ] **5.2 [N]** Open the Projects tab on a repository with no projects. The
      empty message names the **Manage projects** button, and the button is
      there.
- [ ] **5.3 [N]** Click Manage projects. The manager opens over the rename
      window.
- [ ] **5.4 [N]** Create a project there and close the manager. The tab lists it
      immediately, unticked.
- [ ] **5.5 [N]** Tick a project, open the manager again, add another, close.
      Your tick is still there and the new project is unticked.
- [ ] **5.6** Tick a project and cancel the rename. Nothing is assigned.
- [ ] **5.7** Tick a project and complete the rename. The assignment is written
      against the new filename, and the sidebar project filter finds it.
- [ ] **5.8** Same two checks for the Periodicity tab.

## 6. Mass rename

- [ ] **6.1 [A]** Select two or more documents. The header bar shows the mass rename
      menu button instead of the single rename button.
- [ ] **6.2** The menu offers seven functions: Date, Country, Group, Purpose,
      Concept, Sent by, Sent to.
- [ ] **6.3** Set Country across the selection. The preview lists every file
      with its new name, and applying renames all of them.
- [ ] **6.4** Use Date with a calendar date. All selected files take it.
- [ ] **6.5** Use Date with "Detect date from each file" ticked. Each file gets
      its own detected date, the label says how many dates were read out of how
      many files, and files with no readable date get 99991231.
- [ ] **6.5b** Include a file whose concept holds a date the app cannot resolve
      on its own, such as `03_04_2024` (3 April or 4 March, no way to tell). It
      gets 99991231 rather than one of the two readings.
- [ ] **6.6** Use the Concept transform. The guided dialog previews the result
      before applying.
- [ ] **6.7** Include a document whose target name already exists. It is skipped,
      the others are renamed, and the toast says how many were skipped.
- [ ] **6.8** Cancel a mass rename at the preview. Nothing changes on disk.
- [ ] **6.9** The same seven functions appear in the right-click menu for a
      multiple selection.

## 7. Adding and deleting documents

- [ ] **7.1 [S]** Add menu, then Add document (`Ctrl+Insert`). Pick a file. It is
      copied in, normalised to the seven-field form, and appears for review.
- [ ] **7.2** Add several files at once. All arrive and the count is right.
- [ ] **7.3** Add a file whose name is already in the repository. The clash is
      reported and nothing is overwritten.
- [ ] **7.4** Select documents and press `Ctrl+Delete`. The confirmation lists
      exactly what will go, and Cancel leaves them alone.
- [ ] **7.5** Confirm a delete. The files are gone from disk, the rows are gone,
      and the count matches.
- [ ] **7.6 [N]** Delete a document from inside the rename dialog. The row
      disappears from the workspace straight away, without a rescan.
- [ ] **7.7 [S] [N]** Drag files from the file manager onto the document list. The
      area is highlighted while they hover, and dropping copies them in exactly
      as Add document does.
- [ ] **7.8 [N]** Drop on the Browser tab. Nothing is imported: the drop is only
      accepted on the Documents page.
- [ ] **7.9 [N]** Drop a folder. A question appears naming it, saying how many files
      would be imported, and the number changes when Include subfolders is
      ticked. Answering No imports nothing; answering Yes imports exactly the
      number that was shown.
- [ ] **7.10 [N]** Add menu, then Add documents from a directory
      (`Shift+Insert`). It asks about subfolders exactly as a dropped folder
      does, the documents arrive, and the workspace stays usable while it runs.
- [ ] **7.11 [N]** Point it at an unreadable directory
      (`mkdir /tmp/locked && chmod 000 /tmp/locked`). It reports the failure
      instead of ending in silence, and the workspace still refreshes
      afterwards.
- [ ] **7.12 [N]** Import more than twenty files at once. The window stays
      responsive, the list refreshes once at the end rather than per file, and
      the toast counts them all.
- [ ] **7.13 [N]** Select documents and press `Ctrl+Shift+C`, or use Copy
      document names in the right-click menu. Paste: one name per line, in the
      order shown, and a toast says how many.

## 8. Repository switching

- [ ] **8.1 [N] [A]** Settings, Repositories, switch to the other repository. The
      workspace reloads with its documents, and the window subtitle names it.
- [ ] **8.2 [N] [A]** Check the sidebar dropdowns after switching. They show the new
      repository's vocabulary, not the previous one's.
- [ ] **8.3 [N] [A]** Edit a value in repository A, switch to B, switch back. Your
      edit is there, and B never showed A's values.
- [ ] **8.4 [N] [A]** The plugins follow the switch. Enable a plugin in A only,
      switch to B: its button or page is gone. Switch back: it is there again.
- [ ] **8.5 [N] [A]** Confirm the dialog with **Set as the default repository**
      ticked. The workspace switches and this repository becomes the default.
- [ ] **8.6 [N] [A]** Confirm it with the checkbox unticked. The workspace
      switches, and Settings still shows the previous one as the default.
- [ ] **8.7 [N] [A]** Cancel the dialog. Nothing switches and the dropdown goes
      back to the repository in use.
- [ ] **8.8 [N]** Nothing restarts. The window stays open through all of the
      above, the Settings dialog stays open behind the confirmation, and a
      toast names the repository switched to.
- [ ] **8.9** Restart the app. It opens the repository last set as the default,
      which is not necessarily the last one you looked at (8.6).
- [ ] **8.10** Point a repository at a directory that no longer exists. The
      error is explained and the app stays usable.

## 9. Settings

- [ ] **9.1 [S]** `Ctrl+S` opens Application settings, and the pages listed are
      reachable.
- [ ] **9.2** Change the theme preference. It applies immediately.
- [ ] **9.3** Repository settings opens a window with a tab per vocabulary:
      Countries, Groups, Purposes, Senders, Recipients.
- [ ] **9.4** Add a value in one of those tabs. It appears in the list, in the
      matching sidebar dropdown and in the rename dialog without a restart.
- [ ] **9.5 [N]** Rename an existing value's description. The workspace shows the
      new label on affected rows, and the rest of the view does not flicker or
      rebuild.
- [ ] **9.6** Delete a value still used by documents. It is refused and the
      documents using it are listed.
- [ ] **9.7** Delete an unused value. It goes, and the dropdowns lose it.
- [ ] **9.8** Export the configuration, then import it into the other
      repository. The values arrive.
- [ ] **9.9** External libraries: the group lists the libraries, their versions
      and which plugin needs them. Installing one shows progress and finishes.
- [ ] **9.10** Backup and restore: take a backup, change something, restore it,
      and confirm the change is undone. While it runs the window behind is
      greyed out and a progress dialog reports the files; it cannot be closed
      until the work ends, then it says what happened and Close gives the UI
      back. A restore restarts MiAZ on Close, not before.

## 10. Plugins

- [ ] **10.1 [S] [A]** Settings, Plugins. All 17 are listed, each with an icon and a
      description, and the enabled ones are ticked.
- [ ] **10.2 [N] [A]** Disable a plugin that adds a page (MiAZNotes, MiAZInsights).
      Its page disappears from the view switcher.
- [ ] **10.3 [N] [A]** Enable it again. The page comes back and works. Repeat the
      cycle a second time: still fine.
- [ ] **10.4 [N] [A]** Disable and re-enable MiAZFullscreen. The header bar button
      disappears and comes back.
- [ ] **10.5 [N] [A]** Disable and re-enable MiAZProjectMgt and MiAZPeriodicity.
      Their sidebar dropdowns and rename tabs disappear and come back, once
      each, not twice.
- [ ] **10.6** Import a plugin from a ZIP. It appears in the list and can be
      enabled.
- [ ] **10.7** A plugin that fails to load is reported in the plugin manager,
      not only in the log. Setup: add a broken import to a bundled plugin,
      `sed -i '1i import nosuchmodule' ~/.local/share/MiAZ/resources/plugins/MiAZWSFont/wsfont.py`,
      enable it, then undo the edit.

### Plugin by plugin

- [ ] **10.8** MiAZImportFromZip: import a ZIP. Same checks as 7.10.
- [ ] **10.9 [N]** MiAZImportFromZip: with a broken ZIP, the failure is
      reported and the workspace does not freeze for the rest of the session.
      Setup: `printf 'not a zip' > /tmp/broken.zip`.
- [ ] **10.10** MiAZAutoScan: the Add menu entry is present. With no scanner
      connected it still appears and explains the problem when used. No
      scanner needed: unplug it, or run MiAZ with `PATH=/nonexistent:$PATH`
      so `scanimage` cannot be found.
- [ ] **10.11** MiAZOCR: run OCR on a scanned PDF. Progress is shown and the
      text layer is added.
- [ ] **10.12 [N]** MiAZOCR: with `ocrmypdf` missing, the failure is reported
      and later workspace updates still happen. Setup: start MiAZ from a shell
      with `PATH=/usr/bin:/bin` and `ocrmypdf` temporarily renamed, or run it
      in a container without the package.
- [ ] **10.13 [K]** MiAZAIAssistant: configure a provider key, then Suggest in
      the rename dialog. Fields are filled.
- [ ] **10.14 [N]** MiAZAIAssistant: with an invalid key, the button recovers
      instead of staying greyed out reading "Thinking". Setup: no real key
      needed, type any nonsense as the API key and Suggest.
- [ ] **10.15 [K]** MiAZAIAssistant: the chat answers about a document, and a
      failed request does not hang the dialog.
- [ ] **10.16** MiAZNotes: write a note, save it, reopen it. Markdown renders in
      view mode, and the All notes page lists it.
- [ ] **10.17** MiAZInsights: the page renders, the year selector works, the
      heatmap and the world map draw, and the period presets agree with the
      sidebar ones.
- [ ] **10.18** MiAZProjectMgt: assign (`Ctrl+P`), unassign (`Ctrl+Shift+P`) and
      manage (`Ctrl+Alt+P`). The sidebar project filter follows.
- [ ] **10.19** MiAZPeriodicity: set a periodicity and filter by it.
- [ ] **10.20** MiAZColumnVisibility: hide and show columns. The choice survives
      a restart.
- [ ] **10.21** MiAZWSFont: change the workspace font. It applies immediately.
- [ ] **10.22** MiAZExport2CSV, 2Dir, 2Text, 2Zip: export a selection with each.
      The output is written where promised and contains what was selected.
- [ ] **10.23** MiAZImportFromScan: reachable from the Add menu and behaves like
      MiAZAutoScan without a scanner.

## 11. Dialogs and messages

- [ ] **11.1 [N]** Any dialog with a body: the text is not selected when it
      opens, and can still be selected by hand.
- [ ] **11.2** An error dialog wraps long messages instead of stretching the
      window off screen.
- [ ] **11.3** Toasts appear for the actions that report one, and disappear on
      their own.
- [ ] **11.4** `Escape` closes every dialog that has a cancel action.
- [ ] **11.5** A dialog opened over another dialog appears above it, not behind.

## 12. Keyboard

- [ ] **12.1** `Ctrl+?` opens the shortcuts window and lists Application and
      Documents sections.
- [ ] **12.2 [S]** Every shortcut in that window does what it says: `Ctrl+S`,
      `Ctrl+B`, `Ctrl+Q`, `F1`, `Ctrl+BackSpace`, `Ctrl+Delete`, `Return`.
- [ ] **12.3** `Ctrl+Insert` adds a document.
- [ ] **12.4** Tab moves through the rename dialog fields in filename order.
- [ ] **12.5** The whole add-classify-rename loop is possible without the mouse.

## 13. Appearance and language

Nothing in this section is automated, and none of it should be. A machine can
assert that a widget exists; whether the text is legible on a dark background,
whether a Spanish label overflows its button, and whether icons look right at
200% are all judgements only you can make.


- [ ] **13.1** Switch the desktop to dark. Every view is legible, with no
      light-on-light or dark-on-dark text, including the Insights page and the
      Markdown note view.
- [ ] **13.2** Switch back to light. Same check.
- [ ] **13.3** Run with `LANG=es_ES.UTF-8`. The interface is in Spanish,
      including menus, dialogs, column headers and the date filter entries.
- [ ] **13.4** In Spanish, check that no label is cut off or overflows its
      widget.
- [ ] **13.5** Country, group and purpose labels appear in the interface
      language, while the filenames keep their codes.
- [ ] **13.6** At 200% scaling, icons and text are sharp.

## 14. Long-running work

- [ ] **14.1 [N]** Start a directory import of many files. The window stays
      responsive, and the workspace refreshes once at the end rather than per
      file.
- [ ] **14.2 [N]** Start two long operations that overlap, an import and an OCR
      run. Both finish, and the view refreshes normally afterwards.
- [ ] **14.3 [N]** Make one fail (unplug the scanner, remove a file mid-import).
      The failure is reported and later updates still happen. This is the one
      that used to freeze the workspace for the rest of the session.
- [ ] **14.4** Open a large repository. The first paint is quick and the app is
      usable while the scan finishes.

## 15. Command line

Not the GUI, but it ships in the same package and is new in this release.

- [ ] **15.1 [N]** `miaz repos` lists the repositories with the current one
      marked.
- [ ] **15.2 [N]** `miaz search invoice` prints filenames, one per line, with no
      log noise on stdout.
- [ ] **15.3 [N]** `miaz search --long` prints an aligned table with expanded
      labels.
- [ ] **15.4 [N]** `miaz search --json | jq -r '.[].concept'` works.
- [ ] **15.5 [N]** `miaz search --repo <other>` searches the other repository,
      and afterwards the GUI still opens the repository it opened before.
- [ ] **15.6 [N]** `miaz search --repo Nope` names the repositories that exist.
- [ ] **15.7 [N]** `miaz` with no arguments still opens the window.

## 16. Packaging

- [ ] **16.1** Install the .deb in a clean Debian or Ubuntu VM. It installs, the
      desktop entry appears, and the app starts from the menu.
- [ ] **16.2** Install the .rpm in a clean Fedora VM. Same three checks.
- [ ] **16.3** Run the AppImage on a machine without MiAZ installed.
- [ ] **16.4** The About dialog shows the version you are releasing.
- [ ] **16.5** Uninstall removes the binary, the desktop entry and the schema,
      and leaves `~/.MiAZ` and the repositories alone.

---

## Results

| Item | Result | Notes |
|---|---|---|
| Version under test | | |
| Desktop | | GNOME version, Wayland or X11 |
| Date | | |
| Smoke pass | | |
| Changed pass | | |
| Full pass | | |
| Failures | | item numbers |
