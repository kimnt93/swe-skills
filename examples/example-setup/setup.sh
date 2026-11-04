#!/usr/bin/env bash
# Rebuild this example from nothing, in <parent dir> (default: ~/Documents/me), exactly as a user would:
#   bash examples/example-setup/setup.sh [parent dir]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
parent="${1:-$HOME/Documents/me}"
mkdir -p "$parent" && cd "$parent"
[ -f example-setup/project.yaml ] || swe-cli project create example-setup     # AGENTS.md, PROJECT.md, models.yaml, roles.yaml, workflows/, ...
swe-cli project example-setup add https://github.com/kimnt93/jlogger            # clones the upstream into ./example-setup/jlogger
cp "$here/PROJECT.md" "$here/models.yaml" example-setup/                        # the filled-in notes; claude builds, omp reviews
cd example-setup && swe-cli models check && swe-cli flow validate example-setup
echo "ready: cd $parent/example-setup && swe-cli flow run example-setup feature --goal '...'"
