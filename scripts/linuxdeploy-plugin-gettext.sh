#! /bin/bash

# exit whenever a command called in this script fails
set -e

appdir=""

show_usage() {
    echo "Usage: bash $0 --appdir <AppDir>"
}

while [ "$1" != "" ]; do
    case "$1" in
        --plugin-api-version)
            echo "0"
            exit 0
            ;;
        --appdir)
            appdir="$2"
            shift
            shift
            ;;
        *)
            echo "Invalid argument: $1"
            echo
            show_usage
            exit 2
    esac
done

if [[ "$appdir" == "" ]]; then
    show_usage
    exit 2
fi

echo "Installing AppRun hook"
set -x
mkdir -p "$appdir"/apprun-hooks
cat > "$appdir"/apprun-hooks/linuxdeploy-plugin-gettext.sh <<\EOF
#! /bin/bash

export TEXTDOMAINDIR="$APPDIR"/usr/share/locale:"$TEXTDOMAINDIR"
EOF
