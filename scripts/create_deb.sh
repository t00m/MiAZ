# to be executed from source code root directory
sudo apt install python3-setuptools python3-wheel pypy-setuptools debhelper python3-stdeb python3-all-dev dh-python
rm -rf deb_dist
rm -f *.tar.gz
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version=2 bdist_deb
#sudo dpkg -i deb_dist/*.deb
