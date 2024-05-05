#! /bin/bash

# abort on all errors
set -e

if [ "$DEBUG" != "" ]; then
    set -x
    verbose="--verbose"
fi

script=$(readlink -f "$0")

show_usage() {
    echo "Usage: $script --appdir <path to AppDir>"
    echo
    echo "Bundles resources for applications that use ncurses into an AppDir"
}

copy_tree() {
    local src=("${@:1:$#-1}")
    local dst="${*:$#}"

    for elem in "${src[@]}"; do
        cp "$elem" --archive --parents --target-directory="$dst" $verbose
    done
}

APPDIR=

while [ "$1" != "" ]; do
    case "$1" in
        --plugin-api-version)
            echo "0"
            exit 0
            ;;
        --appdir)
            APPDIR="$2"
            shift
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Invalid argument: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
done

if [ "$APPDIR" == "" ]; then
    show_usage
    exit 1
fi

mkdir -p "$APPDIR"

echo "Installing AppRun hook"
HOOKSDIR="$APPDIR/apprun-hooks"
HOOKFILE="$HOOKSDIR/linuxdeploy-plugin-ncurses.sh"
mkdir -p "$HOOKSDIR"
cat > "$HOOKFILE" <<\EOF
#! /bin/bash

export TERMINFO="$APPDIR/usr/share/terminfo"
EOF

echo "Installing terminfo data base"
copy_tree "/usr/share/terminfo" "$APPDIR/"
