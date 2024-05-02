rm -rf MiAZ.egg-info build bdist.linux-x86_64 lib && ./scripts/genbuild.py && /usr/bin/env python3 -m pip install . --user --break-system-packages && rm -rf MiAZ.egg-info build bdist.linux-x86_64 lib
