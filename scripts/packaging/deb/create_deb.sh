# to be executed from source code root directory
sudo apt install python3-setuptools python3-wheel debhelper python3-stdeb python3-all-dev dh-python autoconf-archive gnu-standards dh-make flit python3-build python3-installer 
rm -rf deb_dist
rm -f *.tar.gz
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version=2 --maintainer 'Tomás Vírseda <tomas.virseda@gmail.com>' --compat 10 --section utils --suggests simple-scan --copyright-file data/docs/LICENSE bdist_deb
#sudo dpkg -i deb_dist/*.deb
