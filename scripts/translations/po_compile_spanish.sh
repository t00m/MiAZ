# DEPRECATED: use scripts/i18n/update_translations.sh instead.
# This script predates the Meson-based i18n pipeline and references paths
# (MiAZ/data/po/) that no longer exist. Retained for historical reference
# and may be removed in a future release.
msgfmt -o MiAZ/data/po/es_ES/LC_MESSAGES/miaz.mo MiAZ/data/po/es_ES/LC_MESSAGES/miaz.po
cp -iv MiAZ/data/po/es_ES/LC_MESSAGES/miaz.* MiAZ/data/po/es_ES.UTF-8/LC_MESSAGES/
