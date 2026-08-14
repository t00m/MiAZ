Name:           miaz
Version:        0.1.60
Release:        1%{?dist}
Summary:        Personal Document Organizer

License:        GPL-3.0-or-later
URL:            https://github.com/t00m/MiAZ
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  meson >= 1.5.1
BuildRequires:  ninja-build
BuildRequires:  python3-devel
BuildRequires:  gettext
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

Requires:       python3 >= 3.9
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       libpeas
Requires:       libpeas-loader-python
Requires:       webkitgtk6.0
Requires:       libsecret
Requires:       iso-codes
Recommends:     python3-keyring
Recommends:     python3-pip

%description
MiAZ is a GTK4/Libadwaita desktop application that organises personal
documents by enforcing a strict 7-field filename convention:
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}

The directory is the database, no external database required.

%prep
%autosetup

%build
%meson -Dprofile=release
%meson_build

%install
%meson_install
%find_lang miaz

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.t00m.MiAZ.desktop

%post
glib-compile-schemas %{_datadir}/glib-2.0/schemas &> /dev/null || :
update-desktop-database &> /dev/null || :
touch --no-create %{_datadir}/icons/hicolor &> /dev/null || :

%postun
glib-compile-schemas %{_datadir}/glib-2.0/schemas &> /dev/null || :
update-desktop-database &> /dev/null || :
if [ $1 -eq 0 ] ; then
    touch --no-create %{_datadir}/icons/hicolor &> /dev/null || :
    gtk-update-icon-cache %{_datadir}/icons/hicolor &> /dev/null || :
fi

%posttrans
gtk-update-icon-cache %{_datadir}/icons/hicolor &> /dev/null || :

%files -f miaz.lang
%license data/docs/LICENSE
%doc data/docs/README CHANGELOG.md
%{_bindir}/miaz
%{_datadir}/MiAZ/
%{_datadir}/applications/io.github.t00m.MiAZ.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.github.t00m.MiAZ.svg
%{_datadir}/glib-2.0/schemas/io.github.t00m.MiAZ.gschema.xml
%{_datadir}/metainfo/io.github.t00m.MiAZ.metainfo.xml

%changelog
* Fri Aug 14 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.60-1
- New release. See CHANGELOG.md for details.

* Thu Aug 06 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.50-1
- New release. See CHANGELOG.md for details.

* Wed Aug 05 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.40-1
- AI provider API keys are stored in the system keyring instead of plain text
- Country, Group and Purpose labels are shown in the user's language; French and German catalogues added
- Plugins can add tabs to the rename dialog: set a project or a periodicity while renaming
- Rename dialog is keyboard-friendly: typeable date, Ctrl+Enter to apply, Esc to cancel, invalid names refused
- Faster workspace on large repositories: single file changes update one row, and scans no longer touch the disk per row
- New MiAZInsights plugin page: all-years overview, period selector, activity heatmap, rank movers and a world map
- One AI plugin: MiAZAIChat merged into MiAZAIAssistant, so providers are configured once
- Adding documents is always available: it moved from an optional plugin into the app
- Optional third-party libraries install into a private virtualenv, never into the system Python
- Failed plugins are reported in the app instead of only the log, and every plugin now has an icon
- Config files are written atomically, so a crash cannot leave a half-written repository
- Fixed date filters that hid documents at month boundaries and past midnight
- Flatpak packaging is deprecated: a sandboxed build cannot reach host tools such as ocrmypdf and scanimage
- Removed the unused change journal and the MiAZNewspaper plugin

* Wed Jul 08 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.30-1
- New release. See CHANGELOG.md for details.

* Mon Jul 06 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.29-1
- New release. See CHANGELOG.md for details.

* Sat Jun 27 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.28-1
- New plugin MiAZAIChat: chat about a document via Claude, OpenAI, Gemini, or Ollama
- Mass rename is now a core feature with a guided Concept transform dialog
- Per-repository change journal records every add, rename, and delete with import provenance
- New plugins: MiAZNewspaper, MiAZYearReport, MiAZOCR, MiAZFullscreen, MiAZColumnVisibility
- MiAZNotes renders the note body as Markdown in view mode
- Embedded localhost web server with a built-in Browser page
- Global crash handling with a log file and an error dialog
- Rename: filenames forced to uppercase; Suggest metadata from documents sharing the concept
- Sidebar filters: case-insensitive substring search with sorted entries

* Sat May 16 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.26-1
- New plugin MiAZAIAssistant: AI-powered field suggestions via Claude, OpenAI, Gemini, Ollama
- New plugin MiAZNotes: attach Markdown notes to documents with faceted filtering and backup/restore
- New plugin MiAZColumnVisibility: toggle workspace column visibility
- Rename dialog: inline Add buttons on restricted-vocabulary rows
- Rename dialog: Concept autocomplete via difflib-backed Gtk.Popover
- Workspace: Adw.InlineViewSwitcher for workspace view switching
- Backend: filename_guess_date() helper probing PDF metadata, EXIF, and file mtime

* Tue May 05 2026 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.25-1
- Features:
    - Plugin system: Migrated libpeas 1.x → 2.x (Loader=python, Peas 2.0, GNOME 49 runtime)
    - Plugins: Auto-enable 6 essential system plugins when creating a new repository
    - Workspace: Sidebar migrated to Adw.Sidebar
    - Workspace: Added "Future" date filter showing documents from tomorrow to 9999-12-31
    - Repository: Auto-check empty config sections (Country, Group, Plugin, etc.) after repo activation

- Fixes
    - Backend: Fixed shell injection, file I/O leaks, JSON parsing, and infinite recursion
    - Plugin System loading: Fixed re-activation loop causing "filter already registered" errors
    - Plugins: Fixed threading, i18n, deactivation, and signal handler leaks across 7 plugins
    - Workspace: Fixed project filter race conditions and "No documents found" bug
    - Workspace: Fixed project filter race conditions, added "Future" date filter option
    - GObject: Migrated runtime signal_new() to __gsignals__, fixed cross-instance mutable dicts
    - GTK: Replaced deprecated get_style_context() with add_css_class()
    - i18n: Fixed untranslatable f-strings across all modules

- Performance
    - Repository get() caches JSON I/O instead of reading on every access
    - field_used() uses inverted index (O(1) vs O(N) per call)
    - Workspace filter: date bounds parsed once, dropdowns resolved once per pass
    - ColumnView update() uses single splice() instead of two notifications


* Sat May 03 2025 Tomás Vírseda <tomasvirseda@gmail.com> - 0.1.18-1
- Update to 0.1.18, switch build system to meson
