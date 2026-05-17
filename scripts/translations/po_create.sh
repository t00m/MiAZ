# DEPRECATED: use scripts/i18n/update_translations.sh instead.
# This script predates the Meson-based i18n pipeline and references paths
# (MiAZ/data/po/) that no longer exist. Retained for historical reference
# and may be removed in a future release.
xgettext -d miaz -o MiAZ/data/po/miaz.pot $(find . -name "*.py")