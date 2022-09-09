#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.src.env import ENV
from MiAZ.src.util import get_version
from MiAZ.src.util import desktop_session
from MiAZ.src.config import load_config
from MiAZ.src.backend import get_documents
from MiAZ.src.backend import valid_filename


def main() -> None:
    print("%s v%s" % (ENV['APP']['shortname'], get_version()))
    if desktop_session() is None:
        print("No Desktop Environment available")
    config = load_config()
    if config is None:
        print("Configuration file not found!")
    docs = get_documents('.')
    for doc in docs:
        valid, reasons = valid_filename(doc)
        if not valid:
            print ("%s needs revision. Reasons" % doc)
            for reason in reasons:
                print ("\t => %s" % reason)

if __name__ == '__main__':
    main()
