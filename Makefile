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
