install:
	sudo rm -rf builddir_system
	sudo meson builddir_system --prefix=/usr
	sudo meson setup builddir_system --prefix=/usr --wipe
	sudo ninja -C builddir_system install

install_msys2:
	rm -rf builddir_system
	meson builddir_system --prefix=/usr
	meson setup builddir_system --prefix=/usr --wipe
	ninja -C builddir_system install

uninstall:
	cd builddir_system && sudo ninja uninstall

uninstall_msys2:
	cd builddir_system && ninja uninstall

user:
	rm -rf builddir_user
#~ 	meson setup builddir_user --prefix=~/.local
	meson setup builddir_user --prefix=~/.local --reconfigure --buildtype=debugoptimized --wipe
	ninja -C builddir_user install

user_uninstall:
	cd builddir_user && ninja uninstall

