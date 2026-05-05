flatpak install -y flathub org.flatpak.Builder
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak run --command=flathub-build org.flatpak.Builder --install flatpak/io.github.t00m.MiAZ.json
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest flatpak/io.github.t00m.MiAZ.json
flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
flatpak run io.github.t00m.MiAZ
