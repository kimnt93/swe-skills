#!/usr/bin/env bash
# swe-cli init / project add: a directory becomes a project, repos are listed in project.yaml and cloned.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
cli="$here/bin/main"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL $*"; exit 1; }
export SWE_HOME="$tmp/home" HOME="$tmp/home"
mkdir -p "$HOME"
git config --global user.email t@t; git config --global user.name t; git config --global init.defaultBranch main
for r in api-server web-app; do
    git init -q "$tmp/remote-$r"; git -C "$tmp/remote-$r" commit -q --allow-empty -m init
done
unset SWE_PROJECTS SWE_WORKSPACE

mkdir "$tmp/acme" && cd "$tmp/acme"
# non-interactive: --repo
"$cli" init --name acme --repo "$tmp/remote-api-server" >"$tmp/init.txt" 2>&1 || { cat "$tmp/init.txt"; fail "init"; }
for f in AGENTS.md project.yaml roles.yaml models.yaml workflows/feature.yaml workflows/card.yaml; do
    [ -e "$f" ] || fail "init did not write $f"
done
grep -q "flow run acme feature" AGENTS.md || fail "AGENTS.md is not rendered for the project"
grep -q "swe-cli project add" AGENTS.md || fail "AGENTS.md does not tell the manager how to add repos"
[ -d remote-api-server/.git ] || fail "repo not cloned"
grep -q "remote-api-server" project.yaml || fail "repo not listed in project.yaml"
"$cli" project add "$tmp/remote-web-app" --name web >"$tmp/add.txt" 2>&1 || { cat "$tmp/add.txt"; fail "project add"; }
[ -d remote-web-app/.git ] && grep -q "web:" project.yaml || fail "second repo"
"$cli" project add "$tmp/remote-web-app" --name web | grep -q "already" || fail "adding the same repo twice must be a no-op"
"$cli" project list | grep -q "^acme" || fail "project list"
"$cli" init >/dev/null 2>&1 && fail "init over an existing project must refuse"
# works from a subdirectory and from anywhere via the registry
mkdir -p sub/deep && (cd sub/deep && "$cli" project list | grep -q "^acme") || fail "discovery from a subdirectory"
(cd / && "$cli" project list | grep -q "^acme") || fail "registry lookup from elsewhere"
"$cli" flow list 2>&1 | grep -q "feature" || fail "flow list in the project"
"$cli" flow validate acme >"$tmp/val.txt" 2>&1 || { cat "$tmp/val.txt"; fail "workflows of the project validate"; }
# a project workflow overrides the bundled one
sed -i 's/^description:.*/description: "local override"/' workflows/docs.yaml
"$cli" flow list 2>&1 | grep -q "local override" || fail "project workflow does not override"
echo "PASS init: project.yaml, AGENTS.md, workflows; repos cloned from URLs; found from subdirectories and via the registry"
