#!/usr/bin/env bash
# selftest: prove the fleet command without touching the live setup.
# Fake claude / omp / gh CLIs, a scratch git repo with an origin, a scratch omp config and Hermes home.
#
#   fleet/tests/selftest.sh            everything except a real Hermes bootstrap
#   fleet/tests/selftest.sh --hermes   also bootstrap a scratch Hermes home (slow, needs hermes)
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
fleet="$here/bin/fleet"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export OMP_CONFIG="$tmp/omp/config.yml"
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }
plugin="$("$fleet" name)"

# 1. every level resolves from models.yaml
"$fleet" models show >"$tmp/show.txt" || fail "show"
for level in board lane worker reviewer subagent "omp role"; do
  grep -q "^$level " "$tmp/show.txt" || fail "show has no $level rows"
done
mapfile -t cmd < <("$fleet" models cmd claude mid)
[ "${cmd[*]}" = "claude -p --model sonnet --effort high --permission-mode bypassPermissions" ] || fail "cmd claude mid: ${cmd[*]}"
mapfile -t cmd < <("$fleet" models cmd omp low)
[ "${cmd[3]}" = "google-antigravity/gemini-3.8-flash" ] || fail "cmd omp low: ${cmd[*]}"
[ "$("$fleet" models reviewer claude)" = "omp top" ] || fail "reviewer of claude"
[ "$("$fleet" models reviewer omp)" = "claude mid" ] || fail "reviewer of omp"
[ "$("$fleet" models subagent worker)" = "sonnet" ] || fail "subagent worker"
[ "$("$fleet" models subagent adversary)" = "opus" ] || fail "subagent adversary"
pass "models: board, lanes, workers, reviewers, subagents, omp roles"

# 2. one edit in models.yaml reaches every agent that uses it
sed 's/top: {model: opus,/top: {model: claude-opus-6,/' "$here/models.yaml" >"$tmp/models.yaml"
[ "$(FLEET_MODELS="$tmp/models.yaml" "$fleet" models cmd claude top | sed -n 4p)" = "claude-opus-6" ] || fail "worker swap"
[ "$(FLEET_MODELS="$tmp/models.yaml" "$fleet" models subagent adversary)" = "claude-opus-6" ] || fail "subagent swap"
pass "swap: a new model in workers reaches the next card and the plugin's adversary subagent"

# 3. projects: a scratch registry with one project; apply and bootstrap --dry-run write nothing
git init -q "$tmp/demo-repo"
export FLEET_PROJECTS="$tmp/projects.yaml"
printf '# scratch registry\nprojects:\n  demo:\n    repo: %s\n    github: acme/demo\n    description: Demo API\n' "$tmp/demo-repo" >"$FLEET_PROJECTS"
"$fleet" project list | grep -q "^demo .*pm-demo .*acme/demo" || fail "project list"
"$fleet" models show | grep -q "manager demo .*pm-demo .*claude-sonnet-5-5" || fail "show manager"
"$fleet" models apply --dry-run >"$tmp/apply.txt"
grep -q "would run: hermes -p pm-demo config set model.default claude-sonnet-5-5" "$tmp/apply.txt" || fail "apply manager"
grep -q "would run: hermes config set model.default gemini-3.8-flash" "$tmp/apply.txt" || fail "apply root"
grep -q "would run: hermes -p omp config set model.default" "$tmp/apply.txt" || fail "apply omp lane"
[ ! -e "$OMP_CONFIG" ] || fail "apply --dry-run wrote omp config"
"$fleet" bootstrap --dry-run >"$tmp/boot.txt"
grep -q "hermes profile create pm-demo --no-alias --description Manager of project demo only (Demo API)" "$tmp/boot.txt" || fail "manager profile"
grep -q "hermes -p pm-demo tools disable file code_execution web browser delegation" "$tmp/boot.txt" || fail "manager tools"
grep -q "hermes tools enable kanban terminal memory" "$tmp/boot.txt" || fail "root tools"
grep -q "hermes config set kanban.auto_decompose false" "$tmp/boot.txt" || fail "manual decomposition"
grep -q "hermes kanban boards create demo --default-workdir $tmp/demo-repo" "$tmp/boot.txt" || fail "board"
grep -q "hermes -p pm-demo project create demo $tmp/demo-repo --slug demo --board demo" "$tmp/boot.txt" || fail "manager's project"
grep -q "skills.external_dirs .*fleet/skills.*$plugin/skills" "$tmp/boot.txt" || fail "skills dirs"
"$fleet" project add bad_name --repo "$tmp/demo-repo" --github acme/x --dry-run >"$tmp/bad.txt" && fail "bad project name accepted"
grep -q "name must match" "$tmp/bad.txt" || fail "bad name message"
"$fleet" project add other --repo "$tmp/nope" --github acme/x --dry-run >"$tmp/bad.txt" && fail "missing repo accepted"
grep -q "is not a git clone" "$tmp/bad.txt" || fail "missing repo message"
pass "projects: list, show, apply and bootstrap --dry-run per project; bad names and repos refused"

# 3b. the example setups (Claude-only, oh-my-pi-only) are consistent
for example in claude-only omp-only; do
  file="$here/examples/models.$example.yaml"
  FLEET_MODELS="$file" "$fleet" models show >"$tmp/ex.txt" || fail "$example: show"
  lanes="$(FLEET_MODELS="$file" python3 -c "import yaml,sys; print(' '.join(yaml.safe_load(open(sys.argv[1]))['lanes']))" "$file")"
  [ "$(wc -w <<<"$lanes")" = 1 ] || fail "$example: expected one lane, got: $lanes"
  read -r rlane rtier <<<"$(FLEET_MODELS="$file" "$fleet" models reviewer "$lanes")"
  [ "$rlane" = "$lanes" ] && [ "$rtier" = top ] || fail "$example: reviewer is $rlane $rtier"
  for tier in top mid low; do
    FLEET_MODELS="$file" "$fleet" models cmd "$lanes" "$tier" >/dev/null || fail "$example: cmd $lanes $tier"
  done
  FLEET_MODELS="$file" "$fleet" bootstrap --dry-run >"$tmp/ex-boot.txt" || fail "$example: bootstrap dry-run"
  grep -q "hermes -p $lanes tools disable web browser" "$tmp/ex-boot.txt" || fail "$example: lane profile"
  ! grep -q "hermes -p $( [ "$lanes" = claude ] && echo omp || echo claude) " "$tmp/ex-boot.txt" || fail "$example: the other lane leaked in"
done
pass "examples: claude-only and omp-only each have one lane, a same-lane top reviewer, and bootstrap cleanly"

# 4. fleet lane run + review against fake CLIs
mkdir -p "$tmp/bin"
cat >"$tmp/bin/claude" <<'EOF'
#!/usr/bin/env bash
echo ok >ok && git add ok && git commit -qm "feat: add ok" && echo "fake claude: $*" | head -c 300
EOF
cat >"$tmp/bin/omp" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = models ]; then echo '[]'; exit 0; fi
mkdir -p .fleet && echo "no verified findings" >.fleet/review.md
EOF
chmod +x "$tmp/bin/claude" "$tmp/bin/omp"
export PATH="$tmp/bin:$PATH"
git init -q --bare "$tmp/origin.git"
git clone -q "$tmp/origin.git" "$tmp/repo" 2>/dev/null
cd "$tmp/repo"
git config user.email t@t && git config user.name t
printf 'verify:\n\ttest -f ok\n\ttest -z "$$(git status --porcelain)"\n' >Makefile
git add Makefile && git commit -qm "chore: init" && git branch -M main && git push -q origin main
git switch -qc wt/t1
echo "goal: add ok" >"$tmp/card.md"
HERMES_KANBAN_WORKSPACE="$tmp/repo" "$fleet" lane run claude mid "$tmp/card.md" || fail "lane run exit"
python3 - "$tmp/repo/.fleet/evidence.json" <<'EOF' || fail "evidence.json"
import json, sys
e = json.load(open(sys.argv[1]))
assert e["verify_exit"] == 0 and e["agent_exit"] == 0, e
assert e["commits"] and e["changed_files"] == ["ok"] and e["uncommitted"] == [], e
assert "--model sonnet" in e["command"], e
EOF
grep -q "Start with the $plugin skill" "$tmp/repo/.fleet/run-agent.log" || fail "brief names the plugin router"
pass "lane run: agent commits, make verify passes, .fleet/ is not uncommitted, brief names /$plugin"
HERMES_KANBAN_WORKSPACE="$tmp/repo" "$fleet" lane review claude "$tmp/card.md" || fail "review exit"
python3 - "$tmp/repo/.fleet/review.json" <<'EOF' || fail "review.json"
import json, sys
r = json.load(open(sys.argv[1]))
assert r["lane"] == "omp" and r["tier"] == "top" and "openai-codex/gpt-6-sol" in r["command"], r
assert r["reviewer_edited_files"] is False and "no verified findings" in r["report"], r
EOF
pass "lane review: the other family (omp top), report captured, no edits"
rm ok && git commit -qam "revert ok"
HERMES_KANBAN_WORKSPACE="$tmp/repo" "$fleet" lane run omp low "$tmp/card.md" && fail "verify should fail"
python3 -c "import json; assert json.load(open('$tmp/repo/.fleet/evidence.json'))['verify_exit'] != 0" || fail "failing verify"
pass "lane run: a failing make verify gives a non-zero exit and is recorded"
cd "$here"

# 5. fleet merge: the autopilot guard
cat >"$tmp/bin/gh" <<'EOF'
#!/usr/bin/env bash
case "$1 $2" in
  "pr view") cat "$GH_VIEW" ;;
  "pr checks") cat "$GH_CHECKS" ;;
  "pr merge") echo "MERGED $*" >>"$GH_LOG" ;;
esac
EOF
chmod +x "$tmp/bin/gh"
export GH_VIEW="$tmp/view.json" GH_CHECKS="$tmp/checks.json" GH_LOG="$tmp/gh.log"
sed 's/auto_merge: \[\]/auto_merge: [low]/' "$here/models.yaml" >"$tmp/auto.yaml"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false}' >"$GH_VIEW"
echo '[{"name":"verify","bucket":"pass"}]' >"$GH_CHECKS"
expect_refused() {  # <label> <models file> <risk> <sha>
  local rc=0
  FLEET_MODELS="$2" "$fleet" merge 7 --risk "$3" --sha "$4" >"$tmp/merge.txt" || rc=$?
  [ "$rc" = 3 ] && grep -q REFUSED "$tmp/merge.txt" || { cat "$tmp/merge.txt"; fail "merge guard: $1"; }
}
expect_refused "autopilot off" "$here/models.yaml" low abc
expect_refused "money-path" "$tmp/auto.yaml" money-path abc
expect_refused "risk not allowed" "$tmp/auto.yaml" standard abc
expect_refused "sha mismatch" "$tmp/auto.yaml" low def
echo '[{"name":"verify","bucket":"fail"}]' >"$GH_CHECKS"
expect_refused "red required check" "$tmp/auto.yaml" low abc
echo '[]' >"$GH_CHECKS"
expect_refused "no required checks" "$tmp/auto.yaml" low abc
echo '[{"name":"verify","bucket":"pass"}]' >"$GH_CHECKS"
echo '{"headRefOid":"abc","state":"MERGED","isDraft":false}' >"$GH_VIEW"
expect_refused "closed PR" "$tmp/auto.yaml" low abc
[ ! -e "$GH_LOG" ] || fail "a refused case merged"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false}' >"$GH_VIEW"
FLEET_MODELS="$tmp/auto.yaml" "$fleet" merge 7 --risk low --sha abc >/dev/null || fail "allowed merge"
grep -q "MERGED pr merge 7 --squash --auto --delete-branch --match-head-commit abc" "$GH_LOG" || fail "merge command"
: >"$GH_LOG"
"$fleet" merge 7 --risk money-path --sha abc --approved >/dev/null || fail "approved money-path merge"
grep -q "MERGED pr merge 7 --squash" "$GH_LOG" || fail "approved merge command"
rc=0; "$fleet" merge 7 --risk money-path --sha def --approved >"$tmp/merge.txt" || rc=$?
[ "$rc" = 3 ] && grep -q "is not the verified SHA" "$tmp/merge.txt" || fail "approval does not skip the SHA check"
echo '[{"name":"verify","bucket":"fail"}]' >"$GH_CHECKS"
rc=0; "$fleet" merge 7 --risk low --sha abc --approved >"$tmp/merge.txt" || rc=$?
[ "$rc" = 3 ] && grep -q "not green" "$tmp/merge.txt" || fail "approval does not skip the checks"
sed 's/auto_merge: \[\]/auto_merge: [low, money-path]/' "$here/models.yaml" >"$tmp/bad.yaml"
FLEET_MODELS="$tmp/bad.yaml" "$fleet" models check >"$tmp/check.txt" 2>&1 || true
grep -q "never include money-path" "$tmp/check.txt" || fail "check rejects money-path autopilot"
pass "merge: refuses off / money-path / other risk / stale sha / red or missing checks / closed; merges low at the sha; --approved merges money-path but never skips the SHA or the checks"

# 6. optional: bootstrap a scratch Hermes home with a project, twice, then add a second project
if [ "${1:-}" = "--hermes" ]; then
  export HERMES_HOME="$tmp/hermes"
  mkdir -p "$HERMES_HOME"
  "$fleet" bootstrap >"$tmp/boot1.txt" 2>&1 || { cat "$tmp/boot1.txt"; fail "bootstrap"; }
  "$fleet" bootstrap >"$tmp/boot2.txt" 2>&1 || { cat "$tmp/boot2.txt"; fail "bootstrap re-run"; }
  grep -q "board demo exists" "$tmp/boot2.txt" && grep -q "project demo exists for pm-demo" "$tmp/boot2.txt" || fail "bootstrap not idempotent"
  [ "$(hermes -p pm-demo config get model.default | tail -1)" = "claude-sonnet-5-5" ] || fail "manager model"
  [ "$(hermes -p omp config get model.default | tail -1)" = "gemini-3.8-flash" ] || fail "omp lane model"
  [ "$(hermes config get kanban.auto_decompose | tail -1)" = "False" ] || [ "$(hermes config get kanban.auto_decompose | tail -1)" = "false" ] || fail "auto_decompose"
  hermes -p pm-demo config get skills.external_dirs | grep -q "dist/$plugin/skills" || fail "manager skills dir"
  hermes kanban boards list | grep -qw demo || fail "board demo"
  hermes project list | grep -qw demo || fail "root project demo"
  git init -q "$tmp/web-repo"
  "$fleet" project add web --repo "$tmp/web-repo" --github acme/web --description "Web app" >"$tmp/add.txt" 2>&1 || { cat "$tmp/add.txt"; fail "project add"; }
  grep -q "^  web:" "$FLEET_PROJECTS" && grep -q "^# scratch registry" "$FLEET_PROJECTS" || fail "registry written (header kept)"
  hermes profile list | grep -q "pm-web" || fail "pm-web profile"
  hermes -p pm-web project list | grep -qw web || fail "pm-web project"
  grep -q "gemini-3.8-flash" "$OMP_CONFIG" || fail "omp modelRoles"
  pass "bootstrap on a scratch Hermes home with a project, twice; project add creates the second manager"
fi
echo "all passed"
