sudo rm -rf builddir_system && \
sudo meson builddir_system --prefix=/usr && \
sudo meson setup builddir_system --prefix=/usr --wipe && \
sudo meson dist -C builddir_system && \
echo "Update sha256 field in io.github.t00m.MiAZ.json with this value:" && \
sudo cat builddir_system/meson-dist/MiAZ-0.0.50.tar.xz.sha256sum

