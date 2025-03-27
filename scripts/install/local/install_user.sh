#!/bin/bash

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
install_app
