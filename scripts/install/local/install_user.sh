#!/bin/bash

# Function to check for dependencies
check_dependencies() {
  local dependencies=("meson" "ninja" "gcc" "make")
  local missing_deps=()

  for dep in "${dependencies[@]}"; do
    if ! command -v "$dep" &> /dev/null; then
      missing_deps+=("$dep")
    fi
  done

  if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "Error: The following dependencies are missing: ${missing_deps[*]}"
    install_dependencies "${missing_deps[@]}"
    exit 1
  fi
}

# Function to install missing dependencies
install_dependencies() {
  local missing_deps=("$@")
  local distro=$(grep -oP '^ID=\K\w+' /etc/os-release)

  echo "Attempting to install missing dependencies..."

  case $distro in
    ubuntu|debian)
      sudo apt update
      sudo apt install -y "${missing_deps[@]}"
      ;;
    fedora)
      sudo dnf install -y "${missing_deps[@]}"
      ;;
    arch)
      sudo pacman -Syu --noconfirm "${missing_deps[@]}"
      ;;
    *)
      echo "Unsupported Linux distribution: $distro"
      echo "Please install the following dependencies manually:"
      echo "${missing_deps[*]}"
      exit 1
      ;;
  esac

  # Verify installation
  for dep in "${missing_deps[@]}"; do
    if ! command -v "$dep" &> /dev/null; then
      echo "Error: Failed to install $dep. Please install it manually."
      exit 1
    fi
  done

  echo "All dependencies installed successfully."
}

# Function to build and install the app
install_app() {
  echo "Building and installing the app in the user space..."

  make user

  echo "App installed successfully."
}

# Main script execution
check_dependencies
install_app
