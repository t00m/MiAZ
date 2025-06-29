#!/usr/bin/env bash
# Execute: source ./scripts/env/alias.sh

alias build='./scripts/devel/increase_meson_version.sh build && ./scripts/install/local/install_user.sh'
alias run='miaz'
alias br='build && run'
