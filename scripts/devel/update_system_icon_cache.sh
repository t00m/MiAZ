# Whenever MiAZ app is installed system wide, and the uninstalled, the app icon remains in the /usr cache.
# The solution pass by update the system icon cache
sudo gtk-update-icon-cache -f /usr/share/icons/hicolor
