#!/bin/bash
# Build a self-contained MiAZ AppImage.
#
# Runs INSIDE a throwaway Ubuntu 26.04 container: it installs packages and
# writes to /usr, so do not run it on your workstation. build_appimage.sh
# starts the container and calls this script.
#
# What goes in: the Ubuntu 26.04 builds of Python, PyGObject, GTK 4, libadwaita,
# libpeas 2, WebKitGTK 6.0, libsecret, poppler-utils and tesseract, together with
# their glibc and dynamic linker. sharun (through pkgforge's quick-sharun) runs
# every bundled binary with the bundled linker, so no library comes from the
# host: it needs the kernel, FUSE, a display and the host's CA certificates, and
# runs on distributions much older than the one it was built on. Ubuntu 22.04,
# the system AppImageHub tests on, is the one test_appimage.sh checks.
#
# The image is SquashFS with the standard type 2 runtime, because AppImageHub
# only accepts that. quick-sharun's own packer makes DwarFS images.
#
# Usage: build_in_container.sh SOURCE_DIR OUTPUT_DIR
set -euo pipefail

SRC="${1:?usage: build_in_container.sh SOURCE_DIR OUTPUT_DIR}"
OUT="${2:?usage: build_in_container.sh SOURCE_DIR OUTPUT_DIR}"
ARCH="$(uname -m)"
[[ "$ARCH" == x86_64 ]] || { echo "Only x86_64 is supported (got $ARCH)" >&2; exit 1; }

# Every download from outside the Ubuntu archive is pinned by checksum;
# quick-sharun pins what it downloads itself (sharun). The Ubuntu packages are
# whatever 26.04 ships on the day of the build, security updates included.
QUICK_SHARUN_URL=https://raw.githubusercontent.com/pkgforge-dev/Anylinux-AppImages/e9182b3c59f6b5bf0708bf59a91e1f51b19db053/useful-tools/quick-sharun.sh
QUICK_SHARUN_SHA=80258777c02e427239dec3dda5a712e86c888ce7e8022c1b6339c44345554187
APPIMAGETOOL_URL=https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage
APPIMAGETOOL_SHA=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
RUNTIME_URL=https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64
RUNTIME_SHA=2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d

APP_ID=io.github.t00m.MiAZ
UPINFO="gh-releases-zsync|t00m|MiAZ|latest|MiAZ-*-${ARCH}.AppImage.zsync"

log() { echo "[appimage] $*"; }
die() { echo "[appimage] ERROR: $*" >&2; exit 1; }

fetch() {  # fetch URL DEST SHA256
    wget -q "$1" -O "$2"
    echo "$3  $2" | sha256sum -c --quiet - || die "checksum mismatch for $1"
}

export DEBIAN_FRONTEND=noninteractive
log "Installing build tools and the runtime stack ..."
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    ca-certificates wget file binutils patchelf xvfb xauth dbus-x11 locales \
    meson ninja-build gettext desktop-file-utils libglib2.0-bin libglib2.0-dev-bin \
    python3 python3-venv python3-gi python3-gi-cairo python3-markdown \
    gir1.2-gtk-4.0 gir1.2-adw-1 libpeas-2-0 gir1.2-peas-2 \
    gir1.2-webkit-6.0 gir1.2-secret-1 \
    iso-codes poppler-utils tesseract-ocr tesseract-ocr-eng p11-kit-modules \
    librsvg2-common adwaita-icon-theme fonts-dejavu-core \
    >/dev/null

log "Installing MiAZ to /usr ..."
BUILD="$(mktemp -d)"
mkdir -p "$BUILD"/src
tar -C "$SRC" --exclude=.git --exclude=builddir_appimage --exclude=AppDir \
    --exclude='*.AppImage' --exclude=__pycache__ -cf - . | tar -C "$BUILD"/src -xf -
cd "$BUILD"/src
meson setup _build --prefix=/usr -Dprofile=release >/dev/null
ninja -C _build >/dev/null
ninja -C _build install >/dev/null
VERSION="$(meson introspect --projectinfo _build \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["version"])')"
[[ -n "$VERSION" ]] || die "could not read the version from meson"
log "Version: $VERSION"

# The launcher puts /usr/share/MiAZ first on sys.path. In the AppImage the
# package sits next to bin/, so resolve it from the launcher's own location.
sed -i \
  "s|sys\.path\.insert(1, '/usr/share/MiAZ')|sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'share', 'MiAZ'))|" \
  /usr/bin/miaz
grep -q "os.path.realpath(__file__)" /usr/bin/miaz || die "launcher sys.path patch did not apply"

# quick-sharun looks for the interpreter's stdlib in the arch lib dir (the Arch
# Linux layout); Debian and Ubuntu keep it in /usr/lib/pythonX.Y. Stage a copy
# where it looks. Distribution packages stay in Debian's own place,
# lib/python3/dist-packages, which the bundled interpreter searches relative to
# its prefix, never the host's.
PYVER="$(python3 -c 'import sys; print("python%d.%d" % sys.version_info[:2])')"
PYSTAGE="/usr/lib/$ARCH-linux-gnu/$PYVER"
DISTPKG=/usr/lib/python3/dist-packages
rm -rf "$PYSTAGE"
cp -a "/usr/lib/$PYVER" "$PYSTAGE"
find "$PYSTAGE" -type d -name __pycache__ -prune -exec rm -rf {} +

# MiAZ's venv service ("python -m venv", for plugin dependencies) needs
# ensurepip. Debian's looks for the pip wheel in /usr/share/python-wheels, which
# the AppImage cannot rely on, so carry the wheel inside ensurepip and look
# there.
mkdir -p "$PYSTAGE/ensurepip/_bundled"
cp /usr/share/python-wheels/pip-*.whl "$PYSTAGE/ensurepip/_bundled/"
sed -i "s|^_pkg_dir = sysconfig.get_config_var('WHEEL_PKG_DIR')$|_pkg_dir = os.path.join(os.path.dirname(__file__), '_bundled')|" \
    "$PYSTAGE/ensurepip/__init__.py"
grep -q "^_pkg_dir = os.path.join(os.path.dirname(__file__), '_bundled')$" "$PYSTAGE/ensurepip/__init__.py" \
    || die "ensurepip wheel-directory patch did not apply"

log "Deploying with quick-sharun ..."
WORK="$BUILD/deploy"
mkdir -p "$WORK"
cd "$WORK"
fetch "$QUICK_SHARUN_URL" quick-sharun "$QUICK_SHARUN_SHA"
chmod +x quick-sharun

export ARCH VERSION
export APPDIR="$WORK/AppDir"
export DESKTOP="/usr/share/applications/$APP_ID.desktop"
export ICON="/usr/share/icons/hicolor/scalable/apps/$APP_ID.svg"
export MAIN_BIN=miaz
export DEPLOY_PYTHON=1
export DEPLOY_GTK=1
export DEPLOY_GDK=1
export DEPLOY_LIBPEAS=1
export DEPLOY_P11KIT=1
# quick-sharun starts the binaries to see what they load at run time
export XVFB_CMD="xvfb-run -a --"

# Libraries PyGObject reaches only through typelibs are invisible to ldd, so
# they are named here. Ubuntu keeps glycin's image loaders in libexec, where
# quick-sharun (Arch layout) does not look; without them every image that goes
# through GdkPixbuf, and every SVG, fails to load.
./quick-sharun \
    /usr/bin/miaz \
    /usr/bin/pdftotext /usr/bin/pdftoppm /usr/bin/tesseract \
    /usr/lib/"$ARCH"-linux-gnu/libadwaita-1.so* \
    /usr/lib/"$ARCH"-linux-gnu/libgtk-4.so* \
    /usr/lib/"$ARCH"-linux-gnu/libpeas-2.so* \
    /usr/lib/"$ARCH"-linux-gnu/libwebkitgtk-6.0.so* \
    /usr/lib/"$ARCH"-linux-gnu/libjavascriptcoregtk-6.0.so* \
    /usr/lib/"$ARCH"-linux-gnu/libsecret-1.so* \
    /usr/lib/"$ARCH"-linux-gnu/girepository-1.0/* \
    /usr/libexec/glycin-loaders/*/* \
    "$DISTPKG"/gi/*.so \
    "$DISTPKG"/cairo/*.so

# quick-sharun copied the compiled modules of gi and cairo (and bundled what
# they link to); add their pure-Python halves and the other packages MiAZ
# imports. Only these: dist-packages also holds build tools (meson, setuptools).
for pkg in gi cairo markdown PyGObject-*.dist-info pycairo-*.dist-info markdown-*.dist-info; do
    for path in "$DISTPKG"/$pkg; do
        cp -a --update=none "$path" "$APPDIR/lib/python3/dist-packages/"
    done
done
find "$APPDIR/lib/python3" -type d -name __pycache__ -prune -exec rm -rf {} +

# quick-sharun guesses StartupWMClass=miaz for the desktop entry. That is not
# what the window reports on X11, so leave the key out rather than ship a
# wrong one (the packaged desktop file has none either).
sed -i '/^StartupWMClass=/d' "$APPDIR/$APP_ID.desktop"

# Point the bundled OpenSSL at the host's CA certificates (see the hook).
cp "$SRC/scripts/packaging/AppImage/ca-certs.hook" "$APPDIR/bin/10-ca-certs.hook"

# Opt-in, off by default: see webkit-sandbox.hook for what it does and why.
if [[ "${MIAZ_WEBKIT_SANDBOX_FALLBACK:-0}" == 1 ]]; then
    cp "$SRC/scripts/packaging/AppImage/webkit-sandbox.hook" "$APPDIR/bin/20-webkit-sandbox.hook"
fi

# AppImageHub (and appimagetool) read AppStream data from usr/share/metainfo.
mkdir -p "$APPDIR/usr/share/metainfo"
cp "/usr/share/metainfo/$APP_ID.metainfo.xml" "$APPDIR/usr/share/metainfo/"

log "Packing the AppImage (SquashFS, type 2 runtime) ..."
TOOLS="$BUILD/tools"
mkdir -p "$TOOLS" "$OUT"
fetch "$APPIMAGETOOL_URL" "$TOOLS/appimagetool" "$APPIMAGETOOL_SHA"
fetch "$RUNTIME_URL" "$TOOLS/runtime" "$RUNTIME_SHA"
chmod +x "$TOOLS/appimagetool"

NAME="MiAZ-${VERSION}-${ARCH}.AppImage"
rm -f "$OUT/$NAME" "$OUT/$NAME.zsync"
# No FUSE inside a container: appimagetool runs from its extracted self.
# It writes the .zsync next to the image, for the update information.
cd "$OUT"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$TOOLS/appimagetool" \
    --no-appstream \
    --comp zstd --mksquashfs-opt -Xcompression-level --mksquashfs-opt 19 \
    --runtime-file "$TOOLS/runtime" \
    -u "$UPINFO" \
    "$APPDIR" "$NAME"

[[ -f "$OUT/$NAME" ]] || die "appimagetool did not produce $NAME"
chmod +x "$OUT/$NAME"
if [[ -n "${OUTPUT_OWNER:-}" ]]; then
    chown "$OUTPUT_OWNER" "$OUT/$NAME" "$OUT/$NAME.zsync" 2>/dev/null || true
fi
rm -rf "$BUILD"
log "Done: $OUT/$NAME ($(du -h "$OUT/$NAME" | cut -f1))"
