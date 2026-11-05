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
"$cli" project init --name acme >"$tmp/init.txt" 2>&1 || { cat "$tmp/init.txt"; fail "init"; }
for f in AGENTS.md PROJECT.md skills/learn/SKILL.md project.yaml config.yaml workflows/feature.yaml workflows/card.yaml; do
    [ -e "$f" ] || fail "init did not write $f"
done
grep -q "^agents:" config.yaml && grep -q "developer-senior:" config.yaml && grep -q "reviewer-junior:" config.yaml && grep -q "^roles:" config.yaml && grep -q "^mode: pm" config.yaml && [ ! -e roles.yaml ] && [ ! -e models.yaml ] && [ ! -e workflows/task.yaml ] && ! grep -q "^reviewers:\|^subagents:\|^omp_roles:\|^clis:" config.yaml && ! grep -qi "hermes\|kanban\|^board:\|^workers:\|tier" config.yaml || fail "config.yaml is the agents template (cli, model, reasoning per agent, no tiers, no Hermes)"
grep -q "flow run acme feature" AGENTS.md || fail "AGENTS.md is not rendered for the project"
grep -q "project acme add" AGENTS.md || fail "AGENTS.md does not tell the manager how to add repos"
grep -q "remote-api-server" project.yaml && fail "init must not add repos"
"$cli" init --repo x >/dev/null 2>&1 && fail "init must not take --repo"
"$cli" project acme add "$tmp/remote-api-server" >"$tmp/add0.txt" 2>&1 || { cat "$tmp/add0.txt"; fail "project <name> add"; }
[ -d remote-api-server/.git ] && grep -q "remote-api-server" project.yaml || fail "named add did not clone and list the repo"
(cd / && "$cli" project acme add "$tmp/remote-web-app" --name web2 --dir web2 >/dev/null 2>&1) && [ -d web2/.git ] || [ -d "$tmp/acme/web2/.git" ] || fail "named add from elsewhere"
"$cli" project nope add x >/dev/null 2>&1 && fail "unknown project must fail"
mkdir "$tmp/made" && (cd "$tmp/made" && "$cli" project create shop >/dev/null 2>&1 && [ -f shop/project.yaml ] && [ -f shop/AGENTS.md ]) || fail "project create"
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
old = pathlib.Path("workflows/card.yaml").read_text() + "# older shipped version\n"
pathlib.Path("workflows/card.yaml").write_text(old)
shipped["workflows/card.yaml"] = hashlib.sha256(old.encode()).hexdigest()
json.dump(shipped, open(".swe/shipped.json", "w"))
PY
"$cli" project update >"$tmp/up.txt" 2>&1 || { cat "$tmp/up.txt"; fail "project update 2"; }
[ -f workflows/bugfix.yaml ] || fail "deleted workflow not restored"
grep -q "my rule" AGENTS.md && [ -f AGENTS.md.new ] || fail "edited AGENTS.md must be kept with a .new"
! grep -q "older shipped version" workflows/card.yaml || fail "unedited workflows/card.yaml not refreshed"
grep -q "1 updated, 1 added" "$tmp/up.txt" && grep -q "2 kept" "$tmp/up.txt" || { cat "$tmp/up.txt"; fail "update summary"; }
"$cli" project update --force >/dev/null 2>&1; [ -f AGENTS.md.bak ] && ! grep -q "my rule" AGENTS.md || fail "--force replaces after a backup"
# ---- developer mode: no review and no merge, only the task workflow
mkdir "$tmp/devp" && cd "$tmp/devp" && "$cli" project init --name devp --mode dev >/dev/null 2>&1 || fail "init --mode dev"
grep -q "^mode: dev" config.yaml && [ -f workflows/task.yaml ] && [ ! -e workflows/feature.yaml ] && [ ! -e workflows/card.yaml ] || fail "dev mode ships only the task (and verify) workflows"
grep -q "No review agent, no merge" AGENTS.md && grep -q "flow run devp task" AGENTS.md || fail "dev AGENTS.md"
"$cli" flow validate devp >"$tmp/devval.txt" 2>&1 || { cat "$tmp/devval.txt"; fail "dev workflows validate"; }
"$cli" project update >/dev/null 2>&1 && [ ! -e workflows/feature.yaml ] || fail "project update keeps dev mode"
"$cli" project init --name x --mode nope >/dev/null 2>&1 && fail "bad mode accepted"
cd "$tmp/acme"
echo "PASS dev mode: init --mode dev ships config.yaml (mode dev), the task workflow and a developer AGENTS.md; update keeps the mode"
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
if SWE_REPO="$tmp/plugin" "$cli" update >/dev/null 2>&1; then fail "update must refuse a dirty checkout"; fi
echo "PASS update: pulls main (fast-forward only), rebuilds and reinstalls into the detected (or named) harnesses, relinks, refuses a dirty or non-main checkout"
