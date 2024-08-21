# MiAZ, a Personal Document Organizer

## About MiAZ

Sometimes, it is quite a challenge to keep the documentation of the family, schools, administration, billing, etc... well organized in terms of classification, disk space, time to do it and effort.


MiAZ app aims to solve this problem: with minimal effort, it is possible to have all paperwork organized.


A little effort means: scan letters, donwload attachments from emails, place it in the right MiAZ repository directory, and edit the filename according to a set of fixed rules, like choosing:

- Country,
- Date,
- Group
- Purpose
- Sender
- Receiver

MiAZ helps you comply with these rules effortlessly.

**Disclaimer**: please, take into account that this project is based solely in my own experience and for my own necesities.

## Changelog

### [0.1.0-rc1] - 2024-08-21

First Release Candidate for version 0.1

### Added
- N/A

### Changed
- Reduce log level verbosity (from DEBUG to TRACE)

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- Add missing icons for date and concept actionrows in Rename dialog
- Do not raise error when disabling an already disabled plugin

### Security
- N/A

## Features

* **One or more document repositories**.
* **No database**. The directory holding the documents is the database. Properties are extracted from the own filenames. Configuration files reside in the same repository.
* **Workspace**: a single place where you can view/edit your documents
* **Filtering and search**: built-in drop-downs to help finding documents easily.
* It is **fast**. Depending on the volume of documents and the hardware capacity of your device, thousands of documents can be displayed in seconds.
* Support for **projects**: those documents related between them can be (un)assigned to projects (eg.: all those documents related to the same tax stament year).
* **Single renaming**: a useful feature to rename a single document easily.
* **Mass renaming**: when importing several documents, sometimes is useful to assign the same property to all of them (e.g.: same country). This functionality allows MiAZ to do mass renaming for countries, groups, purposes, senders, and receivers, saving you a lot of time.
* **Predefined properties**: To expedite the document archiving process, you can select from a default set of values. For instance, for groups, among othe values, you have MED, INS, BIL (MEDICAL, INSURANCE, BILLING respectively). Same for purposes. These values can be edited.
* **Plug-in system**: in order to avoid large modifications in the code base, MiAZ uses a plug-in system to extend the functionality and the UI. MiAZ comes with a set of standard plugins to help you importing documents from several sources (a single file, a directory, from the scanner, etc...), and also for exporting them (to excel, CSV, to another directory, in a zip file, as filenames in a plain text file, etc...)


## File name convention

All documents managed by MiAZ are renamed following this name convention consisting on 7 fields:

`{timestamp}-{country}-{group}-{sentby}-{purpose}-{concept}-{sentto}.{extension}`

* **Timestamp**: with format: %Y%m%d (eg.: 20221119)
* **Country**: ISO-3166 Alpha-2 code (eg.: ES for Spain)
* **Group**: root category to which any document belongs to with a similar purpose. Eg.: HOU (Housing), EDU (Education), FIN (Finances), ADM (Public Admon.) and so on.
* **Purpose**: Type of document. Eg.: INF (Informative), REQ (Request), INV (Invoice), etc...
* **SentBy**: The (legal or natural) person sending the document
* **Concept**: Document details. Free text field. Eg.: invoice number, flight number, etc...
* **SentTo**: the (legal or natural) person receiving the document

Notes:

* Each field is separated by a hyphen (`-`). Only 6 hyphens are allowed. Extra hyphens found in a field are automatically converted to underscores (`_`)
* The timestamp format helps to sort documents easily in a file browser or even in a terminal
* Filename fields correspond to the key. If the configuration is lost for any reason, you'll have to figure out what the key stands for. So, try to use meaninful keys whenever you can.

## Get started

### Requirements

MiAZ has been developed under Linux in Python with GTK4 and GObject libraries.
The base for development is always the last Debian stable version, so it should be compatible with newer distros like Ubuntu or Fedora.

At this moment, I haven't released any initial version, neither there is a .deb, .rpm, flatpack or snap package for an easy installation.

It must be installed from source.

**meson** and **ninja** must be already installed in your system.

### Installation

sudo make install

### Uninstallation

sudo make uninstall

### Troubleshooting

Sometimes, because of a bad development decision of mine, software installation can be broken.

Usually, to fix any problem with MiAZ, the environment must be cleaned by:

- deleting all contents in /usr/share/MiAZ

If you installed the software by using PIP (which is also possible), you have to make sure you delete any version deployed.

### Need help?

Raise an issue, please.


## Screenshots

![Workspace](data/mkt/miaz-workspace.png)

![Manage countries](data/mkt/miaz-country-selector.png)

![Manage groups](data/mkt/miaz-projects-selector.png)

![Manage purposes](data/mkt/miaz-purposes-selector.png)

![Manage senders and recipients](data/mkt/miaz-people-selector.png)

![Workspace menu](data/mkt/miaz-workspace-menu.png)

![Add documents from several sources](data/mkt/miaz-workspace-menu-add-new.png)

![Mass renaming](data/mkt/miaz-workspace-menu-mass-renaming.png)

![Projects management](data/mkt/miaz-workspace-menu-projectmgt.png)

![Plugins Export to directory](data/mkt/miaz-plugin-export2dir.png)

![Single rename](data/mkt/miaz-editor.png)

![Plugins](data/mkt/miaz-plugin-system.png)

![About](data/mkt/miaz-about.png)


## About me

Hi, this is Tomás Vírseda. I was born in Spain, and lived half life there, working now in Luxembourg, and living in Germany.
I work as a SAP Basis Administrator, use GNU/Linux in a daily basis, and I love to develop just for fun, mostly with Python.
Do not hesitate to contact me for whatever reason.

## Caution

* **This software application is currently in development and is not yet ready for production use**. The application may contain bugs, errors, or other issues that could cause your computer or device to malfunction or experience other unexpected behaviors. By using this application, you acknowledge and agree that you do so at your own risk, and that the developer and any other parties involved in the development, distribution, or support of this application are not responsible for any damages or losses that may result from its use.*
* **This software application performs typical file operations (such as copy, rename, delete) at Operating System level**. Make sure you have a backup of those files.
* Be aware that files added to the repository directory, are **automatically renamed** to comply with MiAZ rules.
* Please note that **this application is based on the GPL v3 license**, and is provided free of charge. There is **no guarantee of any kind**, either express or implied, regarding its functionality, reliability, or suitability for any particular purpose. The developer reserves the right to modify, update, or discontinue this application at any time, and may not provide support or assistance in resolving any issues or problems that arise from its use. However, **you are free to grab, extend, improve and fork the code as you want**.

**By using this application, you acknowledge and agree to the terms of the GPL v3 license and this disclaimer, and waive any and all claims, actions, or damages that you may have against the developer or any other parties involved in the development, distribution, or support of this application. If you do not agree to these terms, you must not use this application.**
