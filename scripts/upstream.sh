#!/usr/bin/env bash
# What changed in pstack, for the paths we forked, since the pin in UPSTREAM. Read it, take what you want, bump the pin.
#   scripts/upstream.sh          log and diffstat
#   scripts/upstream.sh --diff   the full diff
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
up="${UP:-$HOME/src/pstack-upstream}"
[ -d "$up/.git" ] || git clone -q --filter=blob:none --sparse https://github.com/cursor/plugins.git "$up"
git -C "$up" sparse-checkout set pstack
git -C "$up" fetch -q origin main
pin="$(awk '$1 == "pin" {print $2}' "$root/UPSTREAM")"
mapfile -t paths < <(awk '$1 !~ /^#/ && $1 != "pin" && NF >= 2 {print $2}' "$root/UPSTREAM" | sort -u)
echo "pstack changes since $pin, in ${#paths[@]} forked paths:"
git -C "$up" log --oneline "$pin"..origin/main -- "${paths[@]}"
if [ "${1:-}" = "--diff" ]; then
  git -C "$up" diff "$pin" origin/main -- "${paths[@]}"
else
  git -C "$up" diff --stat "$pin" origin/main -- "${paths[@]}"
fi
