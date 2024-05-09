install:
	sudo rm -rf builddir_system
	sudo meson builddir_system --prefix=/usr
	sudo meson setup builddir_system --prefix=/usr --wipe
	sudo ninja -C builddir_system install

uninstall:
	cd builddir_system && sudo ninja uninstall

user:
	rm -rf builddir_user
	meson builddir_user --prefix=~/.local
	meson setup builddir_user --prefix=~/.local --reconfigure --buildtype=debug --wipe
	ninja -C builddir_user install

user_uninstall:
	cd builddir_user && ninja uninstall

deb:
	rm -rf deb_dist; rm -f *.tar.gz; python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version=2 --maintainer 'Tomás Vírseda <tomas.virseda@gmail.com>' --compat 10 --section utils --suggests simple-scan --copyright-file data/docs/LICENSE bdist_deb

rpm:
	sudo apt install rpm rpmlint rpm-i18n elfutils; rm -rf dist; rm -f *.tar.gz; /usr/bin/env python3 setup.py bdist_rpm
AppImage:
#~ 	rm -rf builddir_user
	meson builddir_user --prefix=/home/t00m/Documents/devel/github/MiAZ/AppDir/usr
	meson setup builddir_user --prefix=/home/t00m/Documents/devel/github/MiAZ/AppDir/usr --reconfigure --buildtype=debug --wipe
	ninja -C builddir_user install
