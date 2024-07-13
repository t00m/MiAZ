# https://github.com/linuxdeploy/linuxdeploy-plugin-gtk/tree/master
rm -rf build/ MiAZ.egg-info AppDir/MiAZ AppDir/MiAZ-* AppDir/bin AppDir/share AppDir/README.adoc
wget -c "https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh"
wget -c "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
chmod +x linuxdeploy-x86_64.AppImage linuxdeploy-plugin-gtk.sh
rm -rf builddir
meson builddir --prefix=~/.local
meson setup builddir --prefix=/home/t00m/Documents/devel/github/MiAZ/AppDir --reconfigure
ninja -C builddir install
mkdir -p AppDir/usr/bin
cp -fv AppDir/bin/miaz AppDir/usr/bin/miaz
VERSION=0.0.21 DEPLOY_GTK_VERSION=4 ./linuxdeploy-x86_64.AppImage --appdir AppDir --plugin gtk --output appimage --icon-file MiAZ/data/io.github.t00m.MiAZ.svg --desktop-file MiAZ/data/io.github.t00m.MiAZ.desktop
