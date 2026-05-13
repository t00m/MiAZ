# MiAZ — Personal Document Organizer

![MiAZ brand](data/docs/brand/io.github.t00m.MiAZ-brand.png)

## About

Keeping family records, school files, invoices, and administrative paperwork organised is a constant challenge — especially when documents arrive from many different countries and institutions.

MiAZ solves this with a simple, consistent file-naming convention of seven fields. Scan a letter, download an email attachment, drop it into your MiAZ repository, and the app guides you through naming it correctly with minimal effort.

## Features

- **Multiple repositories** — keep work, home, and archive documents separate
- **No database** — the directory is the database; files are always portable
- **Workspace** — fast, filterable list that handles thousands of documents
- **Sidebar filters** — per-field dropdowns for date, country, group, sender, purpose, and recipient
- **Single and mass renaming** — fix one document or rename many at once
- **Project management** — group related documents into named projects
- **Plugin system** — extend functionality with plugins

## File-naming convention

Every document managed by MiAZ follows this seven-field scheme:

```
{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}
```

| Field | Format | Example |
|---|---|---|
| Date | `%Y%m%d` | `20240315` |
| Country | ISO 3166-1 Alpha-2 | `ES` |
| Group | 3-char code | `HOU`, `FIN`, `EDU` |
| SentBy | Free text (no hyphens) | `BANKNAME` |
| Purpose | 3-char code | `INV`, `REQ`, `INF` |
| Concept | Free text | `Q1invoice` |
| SentTo | Free text (no hyphens) | `JOHNDOE` |

Fields are separated by hyphens. The date-first order means files sort chronologically in any file browser.

## Screenshots

![Workspace](data/docs/screenshots/MiAZ-Worskpace.png)

![Filters](data/docs/screenshots/MiAZ-Workspace-filters.png)

![Document menu](data/docs/screenshots/MiAZ-Workspace-menu.png)

![Repository settings](data/docs/screenshots/MiAZ-repository-settings.png)

![Plugins](data/docs/screenshots/MiAZ-repository-plugins.png)

## Installation

### RPM (Fedora, RHEL, openSUSE)

Download the `.rpm` package from the [latest release](https://github.com/t00m/MiAZ/releases) and install:

```bash
sudo dnf install ./miaz-*.rpm
```

### DEB (Debian, Ubuntu, derivatives)

Download the `.deb` package from the [latest release](https://github.com/t00m/MiAZ/releases) and install:

```bash
sudo dpkg -i ./miaz_*.deb
sudo apt-get install -f   # resolve any missing dependencies
```

> **Flatpak is deprecated.** Because the application runs inside a sandbox, it does not have access to certain system resources and applications (e.g. scanner software), which negatively impacts the user experience.

### From source

Requirements: Python ≥ 3.9, GTK ≥ 4.10, Libadwaita ≥ 1.6, PyGObject ≥ 3.50, meson, ninja.

```bash
git clone https://github.com/t00m/MiAZ
cd MiAZ
./scripts/install/local/install_user.sh
```

To uninstall:

```bash
./scripts/uninstall/uninstall_user.sh
```

## Requirements

| Dependency | Minimum version |
|---|---|
| Python | 3.9 |
| GTK | 4.10 |
| Libadwaita | 1.6 |
| PyGObject | 3.50 |

## Contributing

Bug reports and feature requests: [GitHub Issues](https://github.com/t00m/MiAZ/issues)

## About the author

My name is Tomás Vírseda. Originally from Spain, I now work in Luxembourg and live in Germany. I work as an SAP Basis Administrator and enjoy programming in Python in my spare time.

Feel free to reach out: tomasvirseda@gmail.com

## License

GPL v3 — see [data/docs/LICENSE](data/docs/LICENSE).

## Disclaimer

* **This software application is currently in development and is not yet ready for production use**. The application may contain bugs, errors, or other issues that could cause your computer or device to malfunction or experience other unexpected behaviors. By using this application, you acknowledge and agree that you do so at your own risk, and that the developer and any other parties involved in the development, distribution, or support of this application are not responsible for any damages or losses that may result from its use.*
* **This software application performs typical file operations (such as copy, rename, delete) at Operating System level**. Make sure you have a backup of those files.
* Be aware that files added to the repository directory, are **automatically renamed** to comply with MiAZ rules.
* Please note that **this application is based on the GPL v3 license**, and is provided free of charge. There is **no guarantee of any kind**, either express or implied, regarding its functionality, reliability, or suitability for any particular purpose. The developer reserves the right to modify, update, or discontinue this application at any time, and may not provide support or assistance in resolving any issues or problems that arise from its use. However, **you are free to grab, extend, improve and fork the code as you want**.
