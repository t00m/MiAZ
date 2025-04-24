# Extract the version
PROJECT_VERSION=$(grep -oP "version\s*:\s*'\K[0-9]+\.[0-9]+\.[0-9]+(\+build\.[0-9]+)?" meson.build)
echo "Building flatpak bundle for MiAZ $PROJECT_VERSION"
flatpak build-export repo builddir_flatpak
flatpak build-bundle repo $PROJECT_VERSION.flatpak io.github.t00m.MiAZ --arch=x86_64
