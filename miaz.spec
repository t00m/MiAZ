Name:           miaz
Version:        0.1.25
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

%description
MiAZ is a GTK4/Libadwaita desktop application that organises personal
documents by enforcing a strict 7-field filename convention:
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}

The directory is the database — no external database required.

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
%doc README.md CHANGELOG.md
%{_bindir}/miaz
%{_datadir}/MiAZ/
%{_datadir}/applications/io.github.t00m.MiAZ.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.github.t00m.MiAZ.svg
%{_datadir}/glib-2.0/schemas/io.github.t00m.MiAZ.gschema.xml
%{_datadir}/metainfo/io.github.t00m.MiAZ.metainfo.xml

%changelog
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
