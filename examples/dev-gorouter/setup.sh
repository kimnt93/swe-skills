#!/usr/bin/env bash
# Rebuild this example from nothing, in <parent dir> (default: ~/Documents/me), exactly as a user would:
#   bash examples/dev-gorouter/setup.sh [parent dir]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
parent="${1:-$HOME/Documents/me}"
mkdir -p "$parent" && cd "$parent"
[ -f dev-gorouter/project.yaml ] || swe-cli project create dev-gorouter --mode dev   # AGENTS.md, PROJECT.md, config.yaml, workflows/, ...
url=https://github.com/kimnt93/gorouter
[ "$(gh config get git_protocol 2>/dev/null)" = ssh ] && url=git@github.com:kimnt93/gorouter.git   # agents push over ssh
swe-cli project dev-gorouter add "$url" --name gorouter                     # clones the upstream into ./dev-gorouter/gorouter
cp "$here/PROJECT.md" dev-gorouter/PROJECT.md                              # the filled-in notes
cd dev-gorouter && swe-cli models check && swe-cli flow validate dev-gorouter
echo "ready: cd $parent/dev-gorouter"
