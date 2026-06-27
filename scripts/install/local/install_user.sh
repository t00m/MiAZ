#!/bin/bash

# User-space install prefix used by `make user` (meson --prefix=~/.local).
ICON_THEME_DIR="$HOME/.local/share/icons/hicolor"

# Regenerate the per-user hicolor icon cache so it matches what is actually
# on disk. ninja uninstall removes the icon file but leaves icon-theme.cache
# untouched, so a stale entry keeps pointing GTK at a missing SVG and triggers
# "Failed to load icon ... No such file or directory" warnings. Refreshing
# after both uninstall and install keeps the cache in sync.
refresh_icon_cache() {
  if command -v gtk-update-icon-cache >/dev/null 2>&1 && [ -d "$ICON_THEME_DIR" ]; then
    gtk-update-icon-cache -f -t "$ICON_THEME_DIR" >/dev/null 2>&1 || true
  fi
}

# Function to build and install the app
install_app() {
  echo "Building and installing the app in the user space..."

  if ! make user; then
    echo "Error: Build failed. The app was not installed."
    return 1
  fi

  echo "App installed successfully."
}

uninstall_app() {
    echo "Uninstalling previous version"

    if ! make user_uninstall; then
      echo "Error: Uninstall failed. The app was not uninstalled."
      return 1
  fi

  echo "App uninstalled successfully."
}

uninstall_app
refresh_icon_cache
install_app
refresh_icon_cache
