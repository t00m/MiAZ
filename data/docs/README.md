# MiAZ, a Personal Document Organizer

![About MiAZ](data/docs/brand/io.github.t00m.MiAZ-brand.png)

## About MiAZ

Managing documentation for family records, school files, institutional paperwork, and billing can often feel like an overwhelming task.
From organizing and classifying to finding the necessary time, and putting in the effort, it’s a constant balancing act.
As someone who has lived a life split across borders, I’ve experienced firsthand how complex it can be to keep everything in order.

MiAZ app aims to solve this problem with minimal effort.

Minimal effort means: scan postal letters, donwload attachments from emails, and process them with MiAZ by setting:

- Country,
- Date,
- Group
- Purpose
- Concept
- Sender
- Receiver

MiAZ helps you to organize your documents effortlessly with predefined values.

## Features

* **One or more document repositories**.
* **No database**. The directory holding the documents is the database.
* **Workspace**: a single place for viewieng/editing/managing your documents
* **Filtering and search**: built-in drop-downs to help finding documents easily.
* **Fast**: Thousands of documents can be displayed in seconds.
* **Project management**: Related documents can be (un)assigned to projects
* **Single renaming**: a useful feature to rename a single document easily.
* **Mass renaming**: Save time renaming several documents at once using the same property
* **Plugin system**: Support for user plugins


## File name convention

All documents managed by MiAZ are renamed following this name convention consisting on 7 fields:

`{date}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}`

* **Date**: with format: %Y%m%d (eg.: 20221119)
* **Country**: ISO-3166 Alpha-2 code (eg.: ES for Spain)
* **Group**: root category to which any document belongs to with a similar purpose. Eg.: HOU (Housing), EDU (Education), FIN (Finances), ADM (Public Admon.) and so on.
* **Purpose**: Type of document. Eg.: INF (Informative), REQ (Request), INV (Invoice), etc...
* **SentBy**: The (legal or natural) person sending the document
* **Concept**: Document details. Free text field. Eg.: invoice number, flight number, etc...
* **SentTo**: the (legal or natural) person receiving the document

Notes:

* Each field is separated by a hyphen (`-`).
* The date format helps to sort documents easily in a file browser or even in a terminal.
* Filename fields correspond to keys.

## Get started

### Requirements

MiAZ has been developed under Linux in Python/GObject/GTK/Libadwaita libraries:
- Python > 3.9
- GObject > 3.50.0
- GTK >= 4.10
- Libadwaita >= 1.6


### Installation

* Developers:
** Download sources: `git clone https://github.com/t00m/MiAZ`
** Installation: `./scripts/install/local/install_user.sh`
** Uninstallation: `./scripts/uninstall/uninstall_user.sh`

Please note that **meson** and **ninja** must be already installed in your system

* Users:
** Installation/Uninstallation from Flatpak repositories: not available yet.


### Need help?

Please, raise an [issue](https://github.com/t00m/MiAZ/issues) in MiAZ Github repository:


## Screenshots

![Workspace](data/docs/screenshots/MiAZ-Worskpace.png)

![Repository settings](data/docs/screenshots/MiAZ-repository-settings.png)

![Main menu](data/docs/screenshots/MiAZ-Workspace-menu.png)

![Plugins](data/docs/screenshots/MiAZ-settings-plugins.png)

![Filters](data/docs/screenshots/MiAZ-Workspace-filters.png)




## About me

My name is Tomás Vírseda. Originally from Spain, where I spent half of my life, I now work in Luxembourg, but I live in Germany.

I work as an SAP Basis Administrator. I use GNU/Linux daily and enjoy programming in my spare time, primarily with Python, as a way to explore new ideas and solve problems.

Feel free to reach out —I’m always open to connecting and collaborating!

mailto:tomas.virseda@gmail.com


## Caution

* **This software application is currently in development and is not yet ready for production use**. The application may contain bugs, errors, or other issues that could cause your computer or device to malfunction or experience other unexpected behaviors. By using this application, you acknowledge and agree that you do so at your own risk, and that the developer and any other parties involved in the development, distribution, or support of this application are not responsible for any damages or losses that may result from its use.*
* **This software application performs typical file operations (such as copy, rename, delete) at Operating System level**. Make sure you have a backup of those files.
* Be aware that files added to the repository directory, are **automatically renamed** to comply with MiAZ rules.
* Please note that **this application is based on the GPL v3 license**, and is provided free of charge. There is **no guarantee of any kind**, either express or implied, regarding its functionality, reliability, or suitability for any particular purpose. The developer reserves the right to modify, update, or discontinue this application at any time, and may not provide support or assistance in resolving any issues or problems that arise from its use. However, **you are free to grab, extend, improve and fork the code as you want**.

**By using this application, you acknowledge and agree to the terms of the GPL v3 license and this disclaimer, and waive any and all claims, actions, or damages that you may have against the developer or any other parties involved in the development, distribution, or support of this application. If you do not agree to these terms, you must not use this application.**
