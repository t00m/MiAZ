#!/bin/bash

# Function to build and install the app
install_app() {
  echo "Building and installing the app in the user space..."

  make user

  echo "App installed successfully."
}

install_app
