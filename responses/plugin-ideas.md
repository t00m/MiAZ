# MiAZ — Plugin Ideas for User Engagement

> Generated: 2026-08-31  
> Context: Features that lower adoption friction and drive daily retention

---

## Priority 1 — Core engagement (must-have)

### MiAZStatsDashboard
**What it does:** Renders the existing `MiAZStats` backend data as native GTK bar charts (Gtk.DrawingArea + cairo) on a new workspace stack page. Tabs: "By Year", "By Group", "By Purpose", "By Sender".  
**Why it matters:** The single most convincing demonstration that organizing documents pays off. Without it, MiAZ looks like a renamed file folder.  
**Builds on:** `backend/stats.py` (fully implemented, never wired); `MiAZWebBrowser`/`load_file()` pattern from TimelineJS; `app.add_widget('stack', ...)` in `mainwindow.py`.  
**Key new files:** `data/resources/plugins/MiAZStatsDashboard/statsdashboard.py`  
**Effort:** M

---

### MiAZRenameTemplates
**What it does:** Adds a "Templates" menu button to the rename dialog. One click pre-fills all five dropdowns (country, group, sender, purpose, recipient) from a saved preset. A "Save as template…" action captures current selections.  
**Why it matters:** Users who file recurring documents (monthly bank statements, annual tax forms) re-select the same 4–5 fields on every rename. Templates reduce a 30-second workflow to 5 seconds.  
**Builds on:** `widgets/rename.py` (`set_suggestion()`, `_set_suggestion()`); `MiAZConfig` pattern for `.conf/templates-used.json`; `MiAZConfigView`/`MiAZSelector` for template management UI.  
**Key new files:** `data/resources/plugins/MiAZRenameTemplates/renametemplates.py`, `MiAZConfigTemplates` subclass in `backend/config.py`  
**Effort:** M

---

## Priority 2 — Daily retention (high value)

### MiAZStarred
**What it does:** Right-click context menu to star/unstar any document. A "Starred" toggle in the sidebar instantly filters the column view to only starred items.  
**Why it matters:** Frequently referenced documents (national ID scan, current lease, latest pay slip) currently require re-entering search criteria. One-click access drives daily return visits.  
**Builds on:** `workspace.register_filter_view()` extension point; `plugin.get/set_config_key()` for persistent starred set; `sidebar-plugin-section` for the sidebar toggle; `util` signals (`filename-renamed`, `filename-deleted`) to keep the set consistent.  
**Key new files:** `data/resources/plugins/MiAZStarred/starred.py` (~150 lines, self-contained)  
**Effort:** S

---

### MiAZSavedSearches
**What it does:** A "Save current filters" button in the sidebar captures the active dropdown + search state as a named preset. Presets appear as one-click rows below the dropdowns.  
**Why it matters:** Power users repeatedly reconstruct the same sidebar filter state (e.g., "all invoices from Bank X this year"). Saved searches make switching contexts instant.  
**Builds on:** `sidebar.py` (`set_filter_state()`); `plugin.get/set_config_key()` for storage. Zero backend changes needed.  
**Key new files:** `data/resources/plugins/MiAZSavedSearches/savedsearches.py`  
**Effort:** S

---

### MiAZPreviewPane
**What it does:** Collapsible right-side pane (Gtk.Revealer) that renders the selected document in a MiAZWebBrowser instance (WebKit renders PDFs and images natively). Falls back to an Adw.StatusPage with file metadata for unsupported types. Toggle button in headerbar.  
**Why it matters:** Requiring users to launch an external app (evince, eog) to verify a document breaks the rename/verify cycle entirely.  
**Builds on:** `widgets/webbrowser.py` (`load_file(filepath)`); `workspace-view-selection-changed` signal; `mainwindow.py` pane layout pattern; `plugin.set_config_key('preview_open', bool)` for persistence.  
**Key new files:** `data/resources/plugins/MiAZPreviewPane/previewpane.py`  
**Effort:** M

---

### MiAZAutoImportWatch
**What it does:** User designates a "watch folder" (e.g. `~/Downloads`). Uses `Gio.FileMonitor` to detect new files, then automatically opens the rename dialog pre-filled with date and name suggestions.  
**Why it matters:** Documents accumulate in Downloads unorganized because the import step requires manual action. A drop-folder removes that barrier entirely.  
**Builds on:** `Gio.FileMonitor` (GTK4 native); `services/actions.py` import flow; `guess_date_if_empty()` in `rename.py`; `plugin.set_config_key('watch_dir', path)` for persistence.  
**Key new files:** `data/resources/plugins/MiAZAutoImportWatch/autoimportwatch.py`  
**Effort:** M

---

## Priority 3 — Power-user features (medium value)

### MiAZDocumentExpiry
**What it does:** Stores `{filename_id: expiry_date}` in `.conf/expiry.json`. On app start, compares today's date against stored expiries and shows an Adw.Toast for documents expiring within 30/60/90 days (configurable). A sidebar filter surfaces "Expiring soon" documents.  
**Why it matters:** Time-sensitive documents (passports, contracts, insurance) expire silently. Proactive reminders prevent missed renewals.  
**Builds on:** `MiAZConfig` pattern for `.conf/expiry.json`; `workspace.register_filter_view()` for the "Expiring soon" filter; `Adw.Toast` via `app.get_widget('toast-overlay')`.  
**Key new files:** `data/resources/plugins/MiAZDocumentExpiry/documentexpiry.py`  
**Effort:** M

---

### MiAZDuplicateDetector
**What it does:** On-demand toolbar action computes SHA-256 hashes of all repository files in a background thread. Groups duplicates in a dedicated Adw.Dialog list where the user can delete or keep files. Hash cache stored in `.conf/hashes.json`.  
**Why it matters:** Repeated imports accumulate duplicates that are invisible in the column view.  
**Builds on:** `threading.Thread` + `GLib.idle_add()` pattern; `Adw.Dialog`; `util` filename/delete operations; `filename-added`/`filename-deleted` signals to invalidate cache.  
**Key new files:** `data/resources/plugins/MiAZDuplicateDetector/duplicatedetector.py`  
**Effort:** M

---

### MiAZQuickNotes
**What it does:** Right-click "Add note…" opens an Adw.Dialog with a Gtk.TextView. Notes stored in `.conf/notes.json` as `{filename_id: "text"}`. A small indicator icon appears in a new column view column when a note exists. Notes survive rename via `filename-renamed` signal.  
**Why it matters:** Users need a way to attach brief context to documents ("disputed charge", "sent to accountant") without encoding it in the 7-field filename.  
**Builds on:** `plugin.get/set_config_key()` for storage; `util.connect('filename-renamed', ...)` to keep notes consistent; `Adw.Dialog` pattern from `services/dialogs.py`.  
**Key new files:** `data/resources/plugins/MiAZQuickNotes/quicknotes.py`  
**Effort:** S

---

### MiAZBulkFieldApply
**What it does:** Toolbar button (active with multi-selection) opens an Adw.Dialog with 7 optional dropdowns, each gated by a "change this field" checkbox. Only checked fields are rewritten; others are preserved. Calls `util.filename_rename()` for each selected item.  
**Why it matters:** `MiAZMassRename` rewrites all 7 fields at once. There is no way to fix a single field (e.g., a mis-spelled sender name) across many documents without touching the rest.  
**Builds on:** `workspace-view-selection-changed` to enable/disable the button; `util.filename_rename()`; `MiAZConfig` dropdowns for field values; existing mass-rename UI patterns.  
**Key new files:** `data/resources/plugins/MiAZBulkFieldApply/bulkfieldapply.py`  
**Effort:** M

---

### MiAZSmartRenameSuggestions
**What it does:** When the rename dialog opens, a new pure-backend module (`backend/suggest.py`) tokenizes the raw filename and substring-matches against the used-config vocabulary. On high-confidence match, a dismissible Adw.Banner offers "Apply suggestions" that pre-fills the matching dropdowns.  
**Why it matters:** The rename dialog is mechanical. A file named `Factura_BBVA_202403.pdf` clearly signals Group=FIN and Purpose=INV — the app should say so.  
**Builds on:** `guess_date_if_empty()` precedent in `rename.py`; `MiAZConfig.load_used()` for the vocabulary; `Adw.Banner` (already used in `selector.py`).  
**Key new files:** `MiAZ/backend/suggest.py`; modifications to `widgets/rename.py`  
**Effort:** S–M

---

## Summary table

| Plugin | Priority | Effort | Self-contained? |
|---|---|---|---|
| MiAZStatsDashboard | Must-have | M | Mostly (needs `app.py` service wiring) |
| MiAZRenameTemplates | Must-have | M | No (modifies `rename.py`) |
| MiAZStarred | High | S | Yes |
| MiAZSavedSearches | High | S | Yes |
| MiAZPreviewPane | High | M | Yes |
| MiAZAutoImportWatch | High | M | Yes |
| MiAZDocumentExpiry | Medium | M | Yes |
| MiAZDuplicateDetector | Medium | M | Yes |
| MiAZQuickNotes | Medium | S | Yes |
| MiAZBulkFieldApply | Medium | M | Yes |
| MiAZSmartRenameSuggestions | Medium | S–M | No (modifies `rename.py`, adds `backend/suggest.py`) |

**Effort key:** S = ~150–200 lines / 1–2 days, M = ~300–400 lines / 3–5 days
