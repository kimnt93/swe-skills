#!/usr/bin/env bash
# Example pipeline: a project whose agents run on Claude Code (plan, build) and oh-my-pi (review).
#   bash examples/claude-omp-pipeline/run.sh <parent dir> <git url of the repo to work on> [project name]
# Needs: swe-cli (make cli), claude and omp logged in, tmux, gh. Re-run safe: an existing project is reused.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
parent="${1:?usage: run.sh <parent dir> <git url> [project name]}"
url="${2:?usage: run.sh <parent dir> <git url> [project name]}"
name="${3:-demo}"
mkdir -p "$parent" && cd "$parent"
[ -f "$name/project.yaml" ] || swe-cli project create "$name"      # 1. a project directory, no repos yet
swe-cli project "$name" add "$url"                                 # 2. clone the repo into it
cp "$here/models.yaml" "$name/models.yaml"                         # 3. agents: claude builds, omp reviews
cd "$name"
swe-cli models check                                               # 4. models exist, logins work
swe-cli flow validate "$name"                                      # 5. the workflows are sound
swe-cli flow graph docs "$name"                                    # 6. the DAG that will run
swe-cli flow run "$name" docs --goal "Add a short 'Quick start' section to the repo's README"   # 7. plan, write, review
swe-cli flow status "$name"
