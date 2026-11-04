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
for f in AGENTS.md PROJECT.md skills/learn/SKILL.md project.yaml roles.yaml models.yaml workflows/feature.yaml workflows/card.yaml; do
    [ -e "$f" ] || fail "init did not write $f"
done
grep -q "^agents:" models.yaml && grep -q "developer-strong:" models.yaml && ! grep -qi "hermes\|kanban\|^board:\|^workers:\|tier" models.yaml || fail "models.yaml is the agents template (cli, model, reasoning per agent, no tiers, no Hermes)"
grep -q "flow run acme feature" AGENTS.md || fail "AGENTS.md is not rendered for the project"
grep -q "swe-cli project add" AGENTS.md || fail "AGENTS.md does not tell the manager how to add repos"
[ -d remote-api-server/.git ] || fail "repo not cloned"
grep -q "remote-api-server" project.yaml || fail "repo not listed in project.yaml"
"$cli" project add "$tmp/remote-web-app" --name web >"$tmp/add.txt" 2>&1 || { cat "$tmp/add.txt"; fail "project add"; }
[ -d remote-web-app/.git ] && grep -q "web:" project.yaml || fail "second repo"
"$cli" project add "$tmp/remote-web-app" --name web | grep -q "already" || fail "adding the same repo twice must be a no-op"
"$cli" project list | grep -q "^acme" || fail "project list"
"$cli" init >/dev/null 2>&1 && fail "init over an existing project must refuse"
"$cli" project notes | grep -q "PROJECT.md: .* words (limit 2000)" || fail "project notes"
python3 -c "print('word ' * 2100)" >>PROJECT.md
"$cli" project notes >/dev/null 2>&1 && fail "an over-long PROJECT.md must fail project notes"
# an existing directory with files in it becomes a project too, files kept
mkdir "$tmp/old" && echo keep >"$tmp/old/README.md" && (cd "$tmp/old" && "$cli" init --name old >/dev/null 2>&1 && grep -q keep README.md && [ -f PROJECT.md ] && [ -f changelog/project.md ]) || fail "init on an existing directory"
# works from a subdirectory and from anywhere via the registry
mkdir -p sub/deep && (cd sub/deep && "$cli" project list | grep -q "^acme") || fail "discovery from a subdirectory"
(cd / && "$cli" project list | grep -q "^acme") || fail "registry lookup from elsewhere"
"$cli" flow list 2>&1 | grep -q "feature" || fail "flow list in the project"
"$cli" flow validate acme >"$tmp/val.txt" 2>&1 || { cat "$tmp/val.txt"; fail "workflows of the project validate"; }
# a project workflow overrides the bundled one
sed -i 's/^description:.*/description: "local override"/' workflows/docs.yaml
"$cli" flow list 2>&1 | grep -q "local override" || fail "project workflow does not override"
echo "PASS init: project.yaml, AGENTS.md, workflows; repos cloned from URLs; found from subdirectories and via the registry"

# ---- project update: untouched files are refreshed, edited files are kept with a .new, missing ones come back
"$cli" project update >"$tmp/up.txt" 2>&1 || { cat "$tmp/up.txt"; fail "project update"; }
grep -q "0 updated, 0 added" "$tmp/up.txt" || { cat "$tmp/up.txt"; fail "a fresh project must be current"; }
rm workflows/bugfix.yaml
echo "# my rule" >>AGENTS.md
python3 - <<'PY'
import hashlib, json, pathlib
shipped = json.load(open(".swe/shipped.json"))
old = pathlib.Path("roles.yaml").read_text() + "# older shipped version\n"
pathlib.Path("roles.yaml").write_text(old)
shipped["roles.yaml"] = hashlib.sha256(old.encode()).hexdigest()
json.dump(shipped, open(".swe/shipped.json", "w"))
PY
"$cli" project update >"$tmp/up.txt" 2>&1 || { cat "$tmp/up.txt"; fail "project update 2"; }
[ -f workflows/bugfix.yaml ] || fail "deleted workflow not restored"
grep -q "my rule" AGENTS.md && [ -f AGENTS.md.new ] || fail "edited AGENTS.md must be kept with a .new"
! grep -q "older shipped version" roles.yaml || fail "unedited roles.yaml not refreshed"
grep -q "1 updated, 1 added" "$tmp/up.txt" && grep -q "2 kept" "$tmp/up.txt" || { cat "$tmp/up.txt"; fail "update summary"; }
"$cli" project update --force >/dev/null 2>&1; [ -f AGENTS.md.bak ] && ! grep -q "my rule" AGENTS.md || fail "--force replaces after a backup"
echo "PASS project update: refreshes what you did not edit, keeps what you edited (.new), restores what is missing, --force with .bak"

# ---- swe-cli update: pulls main, rebuilds, reinstalls, relinks (a stand-in repo with a Makefile)
git init -q --bare "$tmp/upstream.git"
git clone -q "$tmp/upstream.git" "$tmp/plugin" 2>/dev/null
printf 'install:\n\t@echo installed >>installs.log\ncli:\n\t@echo linked >>installs.log\nclaude:\n\t@echo only-claude >>installs.log\n' >"$tmp/plugin/Makefile"
echo ".gitignore" >/dev/null; printf 'installs.log\n' >"$tmp/plugin/.gitignore"
git -C "$tmp/plugin" add -A; git -C "$tmp/plugin" commit -qm one; git -C "$tmp/plugin" push -q origin HEAD:main 2>/dev/null
git -C "$tmp/plugin" branch -M main; git -C "$tmp/plugin" branch -u origin/main -q
git clone -q "$tmp/upstream.git" "$tmp/other" 2>/dev/null; echo two >"$tmp/other/NEWS"; git -C "$tmp/other" add -A; git -C "$tmp/other" commit -qm two; git -C "$tmp/other" push -q origin HEAD:main
SWE_REPO="$tmp/plugin" "$cli" update >"$tmp/upd.txt" 2>&1 || { cat "$tmp/upd.txt"; fail "swe-cli update"; }
[ -f "$tmp/plugin/NEWS" ] || fail "update did not pull main"
grep -q installed "$tmp/plugin/installs.log" && grep -q linked "$tmp/plugin/installs.log" || fail "update did not reinstall and relink"
SWE_REPO="$tmp/plugin" "$cli" update claude >/dev/null 2>&1; grep -q only-claude "$tmp/plugin/installs.log" || fail "update <harness> installs only that one"
echo dirty >"$tmp/plugin/Makefile.local"; git -C "$tmp/plugin" add Makefile.local
SWE_REPO="$tmp/plugin" "$cli" update >/dev/null 2>&1 && fail "update must refuse a dirty checkout"
echo "PASS update: pulls main (fast-forward only), rebuilds and reinstalls into the detected (or named) harnesses, relinks, refuses a dirty or non-main checkout"
