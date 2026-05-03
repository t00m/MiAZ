VERSION := $(shell meson introspect --projectinfo meson.build 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null || grep "^version" meson.build | head -1 | sed "s/.*version.*:.*'\(.*\)'.*/\1/")
NAME    := miaz

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
	meson setup builddir_user --prefix=~/.local --reconfigure --buildtype=debugoptimized --wipe
	ninja -C builddir_user install

user_uninstall:
	cd builddir_user && ninja uninstall

# ── Source tarball (required by rpm and deb targets) ──────────────────────────
dist:
	git archive --format=tar.gz --prefix=$(NAME)-$(VERSION)/ HEAD \
	    -o $(NAME)-$(VERSION).tar.gz
	@echo "Created $(NAME)-$(VERSION).tar.gz"

# ── RPM ───────────────────────────────────────────────────────────────────────
rpm: dist
	mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
	cp $(NAME)-$(VERSION).tar.gz ~/rpmbuild/SOURCES/
	cp $(NAME).spec ~/rpmbuild/SPECS/
	rpmbuild -ba ~/rpmbuild/SPECS/$(NAME).spec
	@echo "RPM built in ~/rpmbuild/RPMS/"

# ── DEB ───────────────────────────────────────────────────────────────────────
deb: dist
	@# dpkg-buildpackage reads debian/ in the current source tree
	dpkg-buildpackage -us -uc -b
	@echo "DEB built in parent directory (../)"

# ── AppImage ──────────────────────────────────────────────────────────────────
appimage: appimage-install
	@# linuxdeploy-plugin-gtk is already in AppDir/apprun-hooks
	ARCH=x86_64 ./linuxdeploy-x86_64.AppImage \
	    --appdir AppDir \
	    --plugin gtk \
	    --desktop-file data/io.github.t00m.MiAZ.desktop \
	    --icon-file data/io.github.t00m.MiAZ-icon.svg \
	    --output appimage
	@echo "AppImage built: MiAZ-$(VERSION)-x86_64.AppImage"

appimage-install:
	@# Install the app into AppDir/usr using Meson DESTDIR
	rm -rf builddir_appimage
	meson setup builddir_appimage --prefix=/usr -Dprofile=release --wipe
	ninja -C builddir_appimage
	DESTDIR=$(CURDIR)/AppDir ninja -C builddir_appimage install
	@echo "Installed into AppDir/"

