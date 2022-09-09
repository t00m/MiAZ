#!/usr/bin/env python
# -*- coding: utf-8 -*-

from MiAZ.backend.env import ENV
from MiAZ.backend.util import get_version
from MiAZ.backend.util import desktop_session
from MiAZ.backend.config import load_config
from MiAZ.backend.controller import get_documents
from MiAZ.backend.controller import valid_filename


def main(dirpath: str) -> None:
    print("%s v%s" % (ENV['APP']['shortname'], get_version()))
    if desktop_session() is None:
        print("No Desktop Environment available")
    config = load_config()
    if config is None:
        print("Configuration file not found!")
    docs = get_documents(dirpath)
    for doc in docs:
        valid, reasons = valid_filename(doc)
        if not valid:
            print ("%s needs revision. Reasons" % doc)
            for reason in reasons:
                print ("\t => %s" % reason)

if __name__ == '__main__':
    import sys
    main(sys.argv[1])
