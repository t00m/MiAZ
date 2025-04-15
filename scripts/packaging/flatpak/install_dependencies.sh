#!/bin/bash

set -e

# Function to print info
info() {
  echo -e "\e[1;34m[INFO]\e[0m $1"
}

# Function to print error
error() {
  echo -e "\e[1;31m[ERROR]\e[0m $1"
}

# Ensure script is run as root or with sudo
if [[ $EUID -ne 0 ]]; then
  error "Please run this script as root or with sudo."
  exit 1
fi

info "Installing Flatpak (if not already installed)..."
dnf install -y flatpak

info "Adding Flathub repository (if not already added)..."
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

info "Installing org.gnome.Sdk version 47..."
flatpak install -y flathub org.gnome.Sdk//47

info "Installing org.gnome.Platform version 47..."
flatpak install -y flathub org.gnome.Platform//47

info "Installation completed successfully!"
