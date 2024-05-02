rm -rf builddir
meson builddir --prefix=~/.local
meson setup builddir --prefix=~/.local --reconfigure
ninja -C builddir install
