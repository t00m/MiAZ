rm -rf MiAZ.egg-info build
./scripts/genbuild.py
pip3 install . --user
# pip3 install . --user --use-feature=in-tree-build
