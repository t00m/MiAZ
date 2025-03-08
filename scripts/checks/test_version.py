# https://packaging.python.org/en/latest/specifications/version-specifiers/#version-specifiers

import re
import sys
import subprocess

def is_canonical(version):
    return re.match(r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$', version) is not None

cmd_version = 'meson introspect %s --projectinfo | jq .version' % sys.argv[1]
o, e = subprocess.Popen([cmd_version], shell=True, stdout=subprocess.PIPE).communicate()
VERSION = o.decode('utf-8').strip().replace('"', '')
print("Is version %s canonical? %s" % (VERSION, is_canonical(VERSION)))

