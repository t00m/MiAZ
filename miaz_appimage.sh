# https://github.com/linuxdeploy/linuxdeploy-plugin-gtk/tree/master
#rm -rf AppDir
wget -c "https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh"
wget -c "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
chmod +x linuxdeploy-x86_64.AppImage linuxdeploy-plugin-gtk.sh
/usr/bin/env python3 -m pip install . -t AppDir --upgrade
cp -fv AppDir/bin/miaz AppDir/usr/bin/miaz
VERSION=0.0.4 DEPLOY_GTK_VERSION=4 ./linuxdeploy-x86_64.AppImage --appdir AppDir --plugin gtk --output appimage --icon-file MiAZ/data/icons/com.github.t00m.MiAZ.svg --desktop-file MiAZ/data/resources/com.github.t00m.MiAZ.desktop
