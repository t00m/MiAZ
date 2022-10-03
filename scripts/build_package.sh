rm -rf MiAZ.egg-info build bdist.linux-x86_64/ lib/
./scripts/genbuild.py
pip3 install . --user
# pip3 install . --user --use-feature=in-tree-build
