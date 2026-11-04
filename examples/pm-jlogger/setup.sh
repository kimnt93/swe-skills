#!/usr/bin/env bash
# Rebuild this example from nothing, in <parent dir> (default: ~/Documents/me), exactly as a user would:
#   bash examples/pm-jlogger/setup.sh [parent dir]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
parent="${1:-$HOME/Documents/me}"
mkdir -p "$parent" && cd "$parent"
[ -f pm-jlogger/project.yaml ] || swe-cli project create pm-jlogger --mode pm   # AGENTS.md, PROJECT.md, config.yaml, workflows/, ...
url=https://github.com/kimnt93/jlogger
[ "$(gh config get git_protocol 2>/dev/null)" = ssh ] && url=git@github.com:kimnt93/jlogger.git   # agents push over ssh
swe-cli project pm-jlogger add "$url" --name jlogger                     # clones the upstream into ./pm-jlogger/jlogger
cp "$here/PROJECT.md" pm-jlogger/PROJECT.md                              # the filled-in notes
cd pm-jlogger && swe-cli models check && swe-cli flow validate pm-jlogger
echo "ready: cd $parent/pm-jlogger"
