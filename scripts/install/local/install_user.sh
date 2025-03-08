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

install_app
