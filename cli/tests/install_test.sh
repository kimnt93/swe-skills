#!/usr/bin/env bash
# install_test: prove the install.sh script works cleanly for help, dry-run, and uninstall
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$root"

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

# 1. Help message
out="$(./install.sh --help)"
grep -q "installer" <<<"$out" || fail "install.sh --help"
pass "installer: --help shows usage"

# 2. Dry-run
dry="$(./install.sh --dry-run)"
grep -q "Would link" <<<"$dry" || fail "install.sh --dry-run"
pass "installer: --dry-run previews installation steps"

# 3. Dry-run uninstall
uninst="$(./install.sh --uninstall --dry-run)"
grep -q "Would remove" <<<"$uninst" || fail "install.sh --uninstall --dry-run"
pass "installer: --uninstall --dry-run previews uninstallation"

echo "all passed"
