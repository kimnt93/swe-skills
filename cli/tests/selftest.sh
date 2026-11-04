#!/usr/bin/env bash
# selftest: prove the fleet command without touching the live setup.
# Fake claude / omp / gh CLIs, a scratch git repo with an origin and a scratch omp config.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
fleet="$here/bin/main"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export OMP_CONFIG="$tmp/omp/config.yml" CLAUDE_SETTINGS="$tmp/claude/settings.json" CODEX_CONFIG="$tmp/codex/config.toml"
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }
plugin="$("$fleet" name)"

# 1. every level resolves from models.yaml
"$fleet" models show >"$tmp/show.txt" || fail "show"
for level in manager agent reviewer subagent "omp role"; do
  grep -q "^$level " "$tmp/show.txt" || fail "show has no $level rows"
done
mapfile -t cmd < <("$fleet" models cmd developer)
[ "${cmd[*]}" = "claude -p --model sonnet --effort medium --permission-mode bypassPermissions" ] || fail "cmd developer: ${cmd[*]}"
mapfile -t cmd < <("$fleet" models cmd documenter)
[ "${cmd[*]}" = "claude -p --model haiku --permission-mode bypassPermissions" ] || fail "cmd documenter (no reasoning): ${cmd[*]}"
mapfile -t cmd < <("$fleet" models cmd reviewer)
[ "${cmd[0]} ${cmd[3]} ${cmd[5]}" = "omp openai-codex/gpt-6-sol high" ] || fail "cmd reviewer: ${cmd[*]}"
[ "$("$fleet" models reviewer claude)" = "reviewer" ] || fail "reviewer of claude"
[ "$("$fleet" models reviewer omp)" = "reviewer-claude" ] || fail "reviewer of omp"
[ "$("$fleet" models subagent worker)" = "sonnet" ] || fail "subagent worker"
[ "$("$fleet" models subagent adversary)" = "opus" ] || fail "subagent adversary"
! grep -q "^lane " "$tmp/show.txt" || fail "show still lists lane profiles"
pass "models: agents (cli, model, reasoning), reviewers, subagents, omp roles; a model without reasoning gets no flag"

# 2. one edit in models.yaml reaches every agent that uses it
sed 's/developer-strong: {cli: claude, model: opus,/developer-strong: {cli: claude, model: claude-opus-6,/' "$here/templates/models.yaml" >"$tmp/models.yaml"
[ "$(SWE_MODELS="$tmp/models.yaml" "$fleet" models cmd developer-strong | sed -n 4p)" = "claude-opus-6" ] || fail "agent swap"
[ "$(SWE_MODELS="$tmp/models.yaml" "$fleet" models subagent adversary)" = "claude-opus-6" ] || fail "subagent swap"
pass "swap: a new model in an agent reaches the next card and the plugin's adversary subagent"

# 2b. models set: one agent changes, comments and the other agents stay; all four harnesses build their commands
cp "$here/templates/models.yaml" "$tmp/set.yaml"
SWE_MODELS="$tmp/set.yaml" "$fleet" models set developer --cli codex --model gpt-6-sol --reasoning medium >/dev/null || fail "models set"
grep -q '^  developer: {cli: codex, model: gpt-6-sol, reasoning: medium}$' "$tmp/set.yaml" || fail "models set line: $(grep '^  developer:' "$tmp/set.yaml")"
grep -q '^# models.yaml: the ONE place' "$tmp/set.yaml" && grep -q '^  documenter: {cli: claude, model: haiku}' "$tmp/set.yaml" || fail "models set damaged the file"
SWE_MODELS="$tmp/set.yaml" "$fleet" models set scribe-opencode --cli opencode --model opencode/claude-sonnet-5 --reasoning high >/dev/null || fail "models set new agent"
SWE_MODELS="$tmp/set.yaml" "$fleet" models set developer --reasoning "" >/dev/null || fail "models set drops reasoning"
mapfile -t cmd < <(SWE_MODELS="$tmp/set.yaml" "$fleet" models cmd developer)
[ "${cmd[*]}" = "codex exec --model gpt-6-sol --dangerously-bypass-approvals-and-sandbox" ] || fail "codex without reasoning: ${cmd[*]}"
mapfile -t cmd < <(SWE_MODELS="$tmp/set.yaml" "$fleet" models cmd scribe-opencode)
[ "${cmd[*]}" = "opencode run --model opencode/claude-sonnet-5 --variant high --auto" ] || fail "opencode headless: ${cmd[*]}"
SWE_MODELS="$tmp/set.yaml" "$fleet" models set developer --cli nonsense --model x >/dev/null 2>&1 && fail "models set accepted a bad cli"
python3 - "$fleet" "$tmp/set.yaml" <<'PY' || fail "interactive argv of the four harnesses"
import importlib.machinery, importlib.util, sys, yaml
loader = importlib.machinery.SourceFileLoader("fleet", sys.argv[1])
spec = importlib.util.spec_from_loader("fleet", loader); fleet = importlib.util.module_from_spec(spec)
import os; os.environ["SWE_MODELS"] = sys.argv[2]; loader.exec_module(fleet)
cfg = fleet.load()
want = {
 "claude": ["claude", "--model", "sonnet", "--effort", "high", "--permission-mode", "bypassPermissions"],
 "codex": ["codex", "--model", "gpt-6-sol", "-c", "model_reasoning_effort=high", "--ask-for-approval", "never", "--sandbox", "danger-full-access"],
 "omp": ["omp", "--model", "openai-codex/gpt-6-sol", "--thinking", "high", "--approval-mode", "yolo"],
 "opencode": ["opencode", "--model", "opencode/claude-sonnet-5", "--auto"],
}
for cli, expected in want.items():
    spec = {"name": "t", "cli": cli, "model": expected[expected.index("--model") + 1], "reasoning": "high"}
    got = fleet.argv(cfg, spec, interactive=True)
    assert got == expected, (cli, got)
# switching an agent to another cli without a model takes that cli's default model
alt = fleet.agent_spec(cfg, "documenter", cli="omp")
assert alt["cli"] == "omp" and alt["model"] == cfg["clis"]["omp"]["model"] and alt["reasoning"] == "", alt
PY
pass "models set: edits one agent in place (comments kept, reasoning removable); claude, codex, omp and opencode build their interactive and headless commands"

# 3. projects: a directory with repos
git init -q "$tmp/demo-src"
git -C "$tmp/demo-src" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
export SWE_PROJECTS="$tmp/projects.yaml"
mkdir -p "$tmp/demo-dir"
git clone -q "$tmp/demo-src" "$tmp/demo-dir/api"
git clone -q "$tmp/demo-src" "$tmp/demo-dir/web"
printf '# scratch registry\nprojects:\n  demo:\n    dir: %s\n    description: Demo API\n    repos:\n      api: {github: acme/demo-api}\n      web: {github: acme/demo-web, hotspots: [package-lock.json]}\n' "$tmp/demo-dir" >"$SWE_PROJECTS"
"$fleet" project list | grep -q "^demo .*api,web .*$tmp/demo-dir" || fail "project list"
"$fleet" bootstrap --dry-run >"$tmp/boot-off.txt"
grep -q "repo api: cloned at $tmp/demo-dir/api" "$tmp/boot-off.txt" || fail "bootstrap does not check the clones"
"$fleet" models apply --dry-run >"$tmp/apply.txt"
[ ! -e "$OMP_CONFIG" ] || fail "apply --dry-run wrote omp config"
"$fleet" project add bad_name --dir "$tmp/x" --repo api=acme/x --dry-run >"$tmp/bad.txt" && fail "bad project name accepted"
grep -q "name must match" "$tmp/bad.txt" || fail "bad name message"
"$fleet" project add other --dir "$tmp/x" --repo Bad_Name=acme/x --dry-run >"$tmp/bad.txt" && fail "bad repo accepted"
grep -q "PROBLEM" "$tmp/bad.txt" || fail "bad repo message"
"$fleet" project add fresh --dir "$tmp/fresh-dir" --repo api="$tmp/demo-src" --repo docs="$tmp/demo-src" --manager developer --dry-run >"$tmp/add-dry.txt" || { cat "$tmp/add-dry.txt"; fail "project add dry-run"; }
grep -q "would create $tmp/fresh-dir" "$tmp/add-dry.txt" && grep -q "git clone $tmp/demo-src $tmp/fresh-dir/docs" "$tmp/add-dry.txt" || fail "project add does not plan the directory and the clones"
"$fleet" project add fresh --dir "$tmp/fresh-dir" --repo api="$tmp/demo-src" --repo docs="$tmp/demo-src" --manager developer >"$tmp/add.txt" 2>&1 || { cat "$tmp/add.txt"; fail "project add"; }
[ -d "$tmp/fresh-dir/api/.git" ] && [ -d "$tmp/fresh-dir/docs/.git" ] || fail "project add did not clone both repos"
pass "projects: a directory with several repos, add clones, bad input refused"

# 3b. the example setups (Claude-only, oh-my-pi-only) are consistent
for example in claude-only codex-only omp-only opencode-only; do
  file="$here/examples/models.$example.yaml"
  SWE_MODELS="$file" "$fleet" models show >"$tmp/ex.txt" || fail "$example: show"
  clis="$(SWE_MODELS="$file" python3 -c "import yaml,sys; print(' '.join(yaml.safe_load(open(sys.argv[1]))['clis']))" "$file")"
  [ "$(wc -w <<<"$clis")" = 1 ] || fail "$example: expected one cli, got: $clis"
  [ "$(SWE_MODELS="$file" "$fleet" models reviewer "$clis")" = reviewer ] || fail "$example: reviewer"
  for agent in $(python3 -c "import yaml,sys; print(' '.join(yaml.safe_load(open(sys.argv[1]))['agents']))" "$file"); do
    mapfile -t cmd < <(SWE_MODELS="$file" "$fleet" models cmd "$agent") || fail "$example: cmd $agent"
    [ "${cmd[0]}" != "${clis}" ] && [ "$clis" != opencode ] || true
    case "${cmd[*]}" in "$clis"*) ;; *) fail "$example: $agent runs ${cmd[*]}";; esac
  done
  SWE_MODELS="$file" "$fleet" bootstrap --dry-run >"$tmp/ex-boot.txt" || fail "$example: bootstrap dry-run"
done
pass "examples: claude, codex, omp and opencode setups each have one CLI, every agent builds its command, and bootstrap cleanly"

# 3c. the context policy reaches Claude Code, Codex and oh-my-pi, and changes nothing else
mkdir -p "$tmp/claude" "$tmp/codex" "$tmp/omp"
printf '{"model": "opus", "note": "keep — this dash", "hooks": {"SessionStart": []}}\n' >"$CLAUDE_SETTINGS"
cat >"$CODEX_CONFIG" <<'TOML'
# Default config
model = "gpt-6-sol"
model_reasoning_effort = "low"
model_context_window = 1000000   # to be replaced
approval_policy = "never"

[projects."/work/app"]
trust_level = "trusted"

[features.context_management]
experimental_mode = false
TOML
printf 'setupVersion: 2\nmodelRoles:\n  default: keep/me\n' >"$OMP_CONFIG"
"$fleet" context apply --dry-run >"$tmp/ctx.txt"
grep -q "would write: .*autoCompactWindow = 350000" "$tmp/ctx.txt" && grep -q "would write: .*model_context_window = 272000, model_auto_compact_token_limit = 245000" "$tmp/ctx.txt" \
  && grep -q "would write: .*compaction.thresholdTokens = 245000" "$tmp/ctx.txt" || { cat "$tmp/ctx.txt"; fail "context apply --dry-run"; }
! grep -q autoCompactWindow "$CLAUDE_SETTINGS" || fail "dry-run wrote claude settings"
"$fleet" context apply >/dev/null || fail "context apply"
python3 - <<'PY' || fail "context apply results"
import json, os, tomllib, yaml
claude = json.load(open(os.environ["CLAUDE_SETTINGS"]))
assert claude == {"model": "opus", "note": "keep — this dash", "hooks": {"SessionStart": []}, "autoCompactWindow": 350000}, claude
assert "\\u2014" not in open(os.environ["CLAUDE_SETTINGS"]).read(), "non-ASCII text was escaped"
codex = tomllib.load(open(os.environ["CODEX_CONFIG"], "rb"))
assert codex["model_context_window"] == 272000 and codex["model_auto_compact_token_limit"] == 245000, codex
assert codex["model"] == "gpt-6-sol" and codex["approval_policy"] == "never", codex
assert codex["projects"]["/work/app"]["trust_level"] == "trusted" and codex["features"]["context_management"]["experimental_mode"] is False, codex
omp = yaml.safe_load(open(os.environ["OMP_CONFIG"]))
assert omp["modelRoles"] == {"default": "keep/me"} and omp["compaction"]["thresholdTokens"] == 245000, omp
PY
ls "$tmp"/claude/settings.json.bak-* "$tmp"/codex/config.toml.bak-* >/dev/null 2>&1 || fail "backups"
"$fleet" context apply >"$tmp/ctx2.txt"
[ "$(grep -c unchanged "$tmp/ctx2.txt")" = 3 ] || { cat "$tmp/ctx2.txt"; fail "context apply is not idempotent"; }
"$fleet" context show >"$tmp/ctx3.txt"
grep -qE "^Claude Code .* 400,000 +350,000" "$tmp/ctx3.txt" && grep -qE "^Codex .* 272,000 +245,000" "$tmp/ctx3.txt" \
  && grep -qE "^oh-my-pi .* 272,000 +245,000" "$tmp/ctx3.txt" || { cat "$tmp/ctx3.txt"; fail "context show"; }
[ "$("$fleet" context env developer)" = "CLAUDE_CODE_AUTO_COMPACT_WINDOW=350000" ] || fail "context env claude"
[ -z "$("$fleet" context env reviewer)" ] || fail "context env omp must be empty"
oc="$(SWE_MODELS="$here/examples/models.opencode-only.yaml" "$fleet" context env developer)"
[ "$oc" = 'OPENCODE_CONFIG_CONTENT={"agent":{"build":{"model":"opencode/claude-sonnet-5","variant":"medium"}}}' ] || fail "opencode reasoning variant env: $oc"
sed 's/compact_at: 245000/compact_at: 300000/' "$here/templates/models.yaml" >"$tmp/ctx-bad.yaml"
SWE_MODELS="$tmp/ctx-bad.yaml" "$fleet" models check >"$tmp/ctx-check.txt" 2>&1 || true
grep -q "context.default: compact_at 300000 must be above 0 and below window 272000" "$tmp/ctx-check.txt" || fail "check rejects compact_at >= window"
for example in claude-only codex-only omp-only; do
  python3 - "$here/templates/models.yaml" "$here/examples/models.$example.yaml" <<'PY' || fail "$example: context differs from models.yaml"
import sys, yaml
base, example = (yaml.safe_load(open(p))["context"] for p in sys.argv[1:])
assert base == example, (base, example)
PY
done
pass "context: apply writes Claude Code, Codex and omp (other keys, tables and comments kept, backups made, idempotent); show; env; invalid policy rejected"

# 4. swe-cli lane run + review against fake CLIs
mkdir -p "$tmp/bin"
cat >"$tmp/bin/claude" <<'EOF'
#!/usr/bin/env bash
printf '%s' "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:-unset}" >"$PWD/.swe/compact-window.txt"
echo ok >ok && git add ok && git commit -qm "feat: add ok" && echo "fake claude: $*" | head -c 300
EOF
cat >"$tmp/bin/omp" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = models ]; then echo '[]'; exit 0; fi
mkdir -p .swe && echo "no verified findings" >.swe/review.md
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
SWE_WORKSPACE_DIR="$tmp/repo" "$fleet" lane run developer "$tmp/card.md" || fail "lane run exit"
python3 - "$tmp/repo/.swe/evidence.json" <<'EOF' || fail "evidence.json"
import json, sys
e = json.load(open(sys.argv[1]))
assert e["verify_exit"] == 0 and e["agent_exit"] == 0, e
assert e["commits"] and e["changed_files"] == ["ok"] and e["uncommitted"] == [], e
assert "--model sonnet" in e["command"], e
EOF
grep -q "Start with the $plugin skill" "$tmp/repo/.swe/run-agent.log" || fail "brief names the plugin router"
[ "$(cat "$tmp/repo/.swe/compact-window.txt")" = 350000 ] || fail "claude lane exports CLAUDE_CODE_AUTO_COMPACT_WINDOW"
pass "lane run: agent commits, make verify passes, .swe/ is not uncommitted, brief names /$plugin, Claude Code gets its compaction point (350000)"
SWE_WORKSPACE_DIR="$tmp/repo" "$fleet" lane review claude "$tmp/card.md" || fail "review exit"
python3 - "$tmp/repo/.swe/review.json" <<'EOF' || fail "review.json"
import json, sys
r = json.load(open(sys.argv[1]))
assert r["agent"] == "reviewer" and r["command"].startswith("omp ") and "openai-codex/gpt-6-sol" in r["command"], r
assert r["reviewer_edited_files"] is False and "no verified findings" in r["report"], r
EOF
pass "lane review: the other family (the reviewer agent, omp), report captured, no edits"
rm ok && git commit -qam "revert ok"
SWE_WORKSPACE_DIR="$tmp/repo" "$fleet" lane run reviewer "$tmp/card.md" && fail "verify should fail"
python3 -c "import json; assert json.load(open('$tmp/repo/.swe/evidence.json'))['verify_exit'] != 0" || fail "failing verify"
pass "lane run: a failing make verify gives a non-zero exit and is recorded"
cd "$here"

# 5. swe-cli merge: the autopilot guard
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
sed 's/auto_merge: \[\]/auto_merge: [low]/' "$here/templates/models.yaml" >"$tmp/auto.yaml"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false}' >"$GH_VIEW"
echo '[{"name":"verify","bucket":"pass"}]' >"$GH_CHECKS"
expect_refused() {  # <label> <models file> <risk> <sha>
  local rc=0
  SWE_MODELS="$2" "$fleet" merge 7 --risk "$3" --sha "$4" >"$tmp/merge.txt" || rc=$?
  [ "$rc" = 3 ] && grep -q REFUSED "$tmp/merge.txt" || { cat "$tmp/merge.txt"; fail "merge guard: $1"; }
}
expect_refused "autopilot off" "$here/templates/models.yaml" low abc
expect_refused "money-path" "$tmp/auto.yaml" money-path abc
expect_refused "risk not allowed" "$tmp/auto.yaml" standard abc
expect_refused "sha mismatch" "$tmp/auto.yaml" low def
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"mergeStateStatus":"BEHIND"}' >"$GH_VIEW"
expect_refused "branch behind main" "$tmp/auto.yaml" low abc
grep -q "swe-cli delegate sync-branch" "$tmp/merge.txt" || fail "behind-main message names sync-branch"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"mergeStateStatus":"DIRTY"}' >"$GH_VIEW"
expect_refused "branch in conflict with main" "$tmp/auto.yaml" low abc
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"mergeStateStatus":"CLEAN"}' >"$GH_VIEW"
echo '[{"name":"verify","bucket":"fail"}]' >"$GH_CHECKS"
expect_refused "red required check" "$tmp/auto.yaml" low abc
echo '[]' >"$GH_CHECKS"
expect_refused "no required checks" "$tmp/auto.yaml" low abc
echo '[{"name":"verify","bucket":"pass"}]' >"$GH_CHECKS"
echo '{"headRefOid":"abc","state":"MERGED","isDraft":false}' >"$GH_VIEW"
expect_refused "closed PR" "$tmp/auto.yaml" low abc
[ ! -e "$GH_LOG" ] || fail "a refused case merged"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"title":"feat: x","files":[{"path":"a.go"}],"labels":[]}' >"$GH_VIEW"
expect_refused "no changelog entry" "$tmp/auto.yaml" low abc
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"title":"feat: x","files":[{"path":"a.go"}],"labels":[{"name":"no-changelog"}]}' >"$GH_VIEW"
SWE_MODELS="$tmp/auto.yaml" "$fleet" merge 7 --risk low --sha abc >/dev/null || fail "no-changelog label merge"
rm -f "$GH_LOG"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"title":"docs: x","files":[],"labels":[]}' >"$GH_VIEW"
SWE_MODELS="$tmp/auto.yaml" "$fleet" merge 7 --risk low --sha abc >/dev/null || fail "docs PR needs no changelog"
rm -f "$GH_LOG"
echo '{"headRefOid":"abc","state":"OPEN","isDraft":false,"title":"fix(api): x","files":[{"path":"svc/CHANGELOG.md"}],"labels":[]}' >"$GH_VIEW"
SWE_MODELS="$tmp/auto.yaml" "$fleet" merge 7 --risk low --sha abc >/dev/null || fail "allowed merge"
grep -q "MERGED pr merge 7 --squash --auto --delete-branch --match-head-commit abc" "$GH_LOG" || fail "merge command"
: >"$GH_LOG"
"$fleet" merge 7 --risk money-path --sha abc --approved >/dev/null || fail "approved money-path merge"
grep -q "MERGED pr merge 7 --squash" "$GH_LOG" || fail "approved merge command"
rc=0; "$fleet" merge 7 --risk money-path --sha def --approved >"$tmp/merge.txt" || rc=$?
[ "$rc" = 3 ] && grep -q "is not the verified SHA" "$tmp/merge.txt" || fail "approval does not skip the SHA check"
echo '[{"name":"verify","bucket":"fail"}]' >"$GH_CHECKS"
rc=0; "$fleet" merge 7 --risk low --sha abc --approved >"$tmp/merge.txt" || rc=$?
[ "$rc" = 3 ] && grep -q "not green" "$tmp/merge.txt" || fail "approval does not skip the checks"
sed 's/auto_merge: \[\]/auto_merge: [low, money-path]/' "$here/templates/models.yaml" >"$tmp/bad.yaml"
SWE_MODELS="$tmp/bad.yaml" "$fleet" models check >"$tmp/check.txt" 2>&1 || true
grep -q "never include money-path" "$tmp/check.txt" || fail "check rejects money-path autopilot"
pass "merge: refuses off / money-path / other risk / stale sha / behind or conflicting branch / red or missing checks / closed; merges low at the sha; --approved merges money-path but never skips the SHA or the checks"

# 5b. swe-cli delegate: worktrees and tmux sessions against a fake interactive CLI
if command -v tmux >/dev/null; then
  export SWE_STATE="$tmp/state" SWE_WORKTREES="$tmp/wt" CLAUDE_JSON="$tmp/claude.json" SWE_READY_TIMEOUT=20
  git init -q --bare "$tmp/dd-origin.git"
  git clone -q "$tmp/dd-origin.git" "$tmp/dd" 2>/dev/null
  ( cd "$tmp/dd" && git config user.email t@t && git config user.name t && git checkout -q -b main \
    && echo a >a.txt && printf 'verify:\n\t@echo verified\n' >Makefile && mkdir schemas && touch schemas/.keep \
    && git add . && git commit -qm "chore: init" && git push -q origin main )
  printf 'projects:\n  dd:\n    dir: %s\n    description: Delegate demo\n    repos:\n      dd: {github: acme/dd, hotspots: [schemas/]}\n' "$tmp" >"$tmp/dd-projects.yaml"
  cat >"$tmp/bin/claude" <<'EOF'
#!/usr/bin/env bash
echo "fake claude $*"
printf '❯ \n'
while IFS= read -r line; do
  case "$line" in *".swe/brief"*) card=1;; esac
  if [ -n "${card:-}" ] && [ -z "${did:-}" ]; then
    did=1; echo "esc to interrupt"; sleep 1
    echo work >>a.txt && git add a.txt && git -c user.email=t@t -c user.name=t commit -qm "feat: fake work"
    echo "CARD DONE $(git rev-parse --short HEAD) https://example/pr/1"; printf '❯ \n'
  fi
done
EOF
  chmod +x "$tmp/bin/claude"
  trap 'for s in dd-c1 dd-c2 dd-c3 dd-c1-review dd2-x1 orca-dd-c7 dd-orchestrator; do tmux kill-session -t $s 2>/dev/null || true; done; rm -rf "$tmp"' EXIT
  d() { SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" delegate "$@"; }
  rc=0; d start dd c1 --files a.txt --goal "add a line" --branch feat/1-a --issue 1 >"$tmp/d1.txt" 2>&1 || rc=$?
  [ "$rc" = 0 ] || { cat "$tmp/d1.txt"; fail "delegate start"; }
  [ -d "$tmp/wt/dd/feat-1-a" ] && tmux has-session -t dd-c1 && [ -f "$tmp/state/dd/c1.json" ] || fail "delegate start: worktree, session or record missing"
  python3 -c "import json,os;d=json.load(open(os.environ['CLAUDE_JSON']));assert d['projects'][os.environ['SWE_WORKTREES']+'/dd/feat-1-a']['hasTrustDialogAccepted']" || fail "the worktree was not pre-trusted"
  [ "$(git -C "$tmp/wt/dd/feat-1-a" rev-parse --abbrev-ref HEAD)" = feat/1-a ] || fail "worktree branch"
  [ "$(git -C "$tmp/dd" branch --show-current)" = main ] && [ -z "$(git -C "$tmp/dd" status --porcelain)" ] || fail "the central clone was touched"
  for _ in $(seq 20); do d status dd c1 | grep -q '"outcome": "CARD DONE' && break; sleep 1; done
  d status dd c1 >"$tmp/d-status.json"
  python3 - "$tmp/d-status.json" <<'PY' || fail "delegate status"
import json, sys
s = json.load(open(sys.argv[1]))
assert s["outcome"].startswith("CARD DONE ") and s["state"] == "idle" and s["commits"] and s["changed_files"] == ["a.txt"], s
assert s["outside_scope"] == [] and s["behind_main"] == 0 and s["uncommitted"] == [], s
PY
  tmux capture-pane -p -t dd-c1 -S -200 | grep -q 'fake claude --model sonnet --effort medium --permission-mode bypassPermissions' || fail "interactive argv (no -p)"
  ! tmux capture-pane -p -t dd-c1 -S -200 | grep -q 'fake claude -p' || fail "the interactive session ran headless"
  pass "delegate start: fetch, worktree from origin/main, trusted, tmux session with the brief, outcome read from the pane; central clone untouched"

  rc=0; d start dd c2 --files a.txt --goal x --branch feat/2-b >"$tmp/d2.txt" 2>&1 || rc=$?
  [ "$rc" = 5 ] && grep -q "card c1 already holds a.txt" "$tmp/d2.txt" || { cat "$tmp/d2.txt"; fail "overlap not refused"; }
  d start dd c2 --files src/ --goal x --branch feat/2-b >/dev/null 2>&1 || fail "disjoint card refused"
  d start dd c3 --files schemas/0002_x.sql --goal x --branch feat/3-c >/dev/null 2>&1 || fail "hotspot card refused"
  rc=0; d start dd c4 --files schemas/0003_y.sql --goal x --branch feat/4-d >"$tmp/d4.txt" 2>&1 || rc=$?
  [ "$rc" = 5 ] && grep -q "hotspot schemas/ is held by card c3" "$tmp/d4.txt" || { cat "$tmp/d4.txt"; fail "hotspot not held"; }
  d cleanup dd c3 --force >/dev/null; d cleanup dd c2 --force >/dev/null
  pass "delegate: overlapping files and a held hotspot are refused (exit 5); disjoint cards run in parallel"

  git -C "$tmp/dd" remote set-url origin "$tmp/missing.git"
  rc=0; d start dd c5 --files docs/ --goal x --branch docs/5-e >"$tmp/d5.txt" 2>&1 || rc=$?
  [ "$rc" = 4 ] && grep -q "cannot fetch origin" "$tmp/d5.txt" && [ ! -e "$tmp/wt/docs-5-e" ] || { cat "$tmp/d5.txt"; fail "a failing fetch must stop the delegation"; }
  ! SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" doctor dd >"$tmp/doc.txt" 2>&1 || fail "doctor passed with an unreachable origin"
  grep -q "cannot reach origin" "$tmp/doc.txt" || { cat "$tmp/doc.txt"; fail "doctor message"; }
  git -C "$tmp/dd" remote set-url origin "$tmp/dd-origin.git"
  SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" doctor dd >"$tmp/doc.txt" 2>&1 || { cat "$tmp/doc.txt"; fail "doctor on a healthy project"; }
  pass "delegate: a failing fetch stops the delegation (exit 4, no worktree); doctor reports it and passes on a healthy project"

  ( cd "$tmp" && rm -rf dd-other && git clone -q dd-origin.git dd-other && cd dd-other && git config user.email t@t && git config user.name t \
    && git checkout -q main && echo z >z.txt && git add z.txt && git commit -qm "feat: z" && git push -q origin main )
  d status dd c1 --fetch | grep -q '"behind_main": 1' || fail "behind_main after main moved"
  ( cd "$tmp/wt/dd/feat-1-a" && SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" delegate sync-branch --verify >"$tmp/sync.txt" 2>&1 ) || { cat "$tmp/sync.txt"; fail "sync-branch"; }
  grep -q "verified" "$tmp/sync.txt" && git -C "$tmp/wt/dd/feat-1-a" log --oneline | grep -q "feat: z" || fail "sync-branch did not rebase and verify"
  d status dd c1 | grep -q '"behind_main": 0' || fail "behind_main after sync"
  ( cd "$tmp/dd-other" && echo changed >a.txt && git add a.txt && git commit -qm "feat: a" && git push -q origin main )
  before="$(git -C "$tmp/wt/dd/feat-1-a" rev-parse HEAD)"
  rc=0; ( cd "$tmp/wt/dd/feat-1-a" && SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" delegate sync-branch >"$tmp/sync.txt" 2>&1 ) || rc=$?
  [ "$rc" = 6 ] && grep -q "conflicts with main in: a.txt" "$tmp/sync.txt" && [ "$(git -C "$tmp/wt/dd/feat-1-a" rev-parse HEAD)" = "$before" ] \
    && [ -z "$(git -C "$tmp/wt/dd/feat-1-a" status --porcelain)" ] || { cat "$tmp/sync.txt"; fail "a conflict must abort and leave the branch unchanged"; }
  echo dirty >>"$tmp/wt/dd/feat-1-a/a.txt"
  rc=0; ( cd "$tmp/wt/dd/feat-1-a" && SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" delegate sync-branch >/dev/null 2>&1 ) || rc=$?
  [ "$rc" = 7 ] || fail "sync-branch with uncommitted changes must exit 7"
  git -C "$tmp/wt/dd/feat-1-a" checkout -q a.txt
  pass "delegate: behind-main is reported, sync-branch rebases and verifies, a conflict aborts cleanly (exit 6), uncommitted work is refused (exit 7)"

  echo x >"$tmp/wt/dd/feat-1-a/other.txt" && git -C "$tmp/wt/dd/feat-1-a" add other.txt && git -C "$tmp/wt/dd/feat-1-a" commit -qm "feat: stray"
  rc=0; d scope dd c1 >"$tmp/scope.json" || rc=$?
  [ "$rc" = 8 ] && grep -q '"other.txt"' "$tmp/scope.json" || { cat "$tmp/scope.json"; fail "scope must flag files outside the list"; }
  d review dd c1 --dry-run >"$tmp/rev.txt" || fail "review dry-run"
  grep -q "would run (tmux): dd-c1-review in .* omp --model openai-codex/gpt-6-sol --thinking high" "$tmp/rev.txt" || { cat "$tmp/rev.txt"; fail "the review runs on the other CLI"; }
  pass "delegate: scope flags a file outside the list (exit 8); review starts the other CLI (omp top)"

  # two projects may clone the same GitHub repo: files and branches are kept apart
  mkdir -p "$tmp/dd2-dir" && git clone -q "$tmp/dd-origin.git" "$tmp/dd2-dir/dd" 2>/dev/null
  printf 'projects:\n  dd:\n    dir: %s\n    repos:\n      dd: {github: acme/dd, hotspots: [schemas/]}\n      docs: {github: acme/dd-docs}\n  dd2:\n    dir: %s\n    repos:\n      dd: {github: acme/dd}\n' "$tmp" "$tmp/dd2-dir" >"$tmp/dd-projects.yaml"
  git clone -q "$tmp/dd-origin.git" "$tmp/docs" 2>/dev/null
  rc=0; d start dd c6 --files a.txt --goal x >"$tmp/d6.txt" 2>&1 || rc=$?
  [ "$rc" = 2 ] && grep -q "has several repos" "$tmp/d6.txt" || { cat "$tmp/d6.txt"; fail "a multi-repo project must ask for --repo"; }
  rc=0; d start dd2 x1 --files a.txt --goal x --branch feat/9-z >"$tmp/d7.txt" 2>&1 || rc=$?
  [ "$rc" = 5 ] && grep -q "card c1 already holds a.txt" "$tmp/d7.txt" || { cat "$tmp/d7.txt"; fail "a duplicate repo in another project must see c1's files"; }
  rc=0; d start dd2 x1 --files lib/ --goal x --branch feat/1-a >"$tmp/d7.txt" 2>&1 || rc=$?
  [ "$rc" = 11 ] && grep -q "already" "$tmp/d7.txt" || { cat "$tmp/d7.txt"; fail "a taken branch name must be refused (exit 11)"; }
  d start dd2 x1 --files lib/ --goal x --branch feat/9-lib --cli codex >"$tmp/d7.txt" 2>&1 || { cat "$tmp/d7.txt"; fail "the same repo in another project, other files and branch"; }
  tmux capture-pane -p -t dd2-x1 -S -200 | grep -q 'fake claude' && fail "project dd2 --cli codex ran claude" || true
  [ -d "$tmp/dd2-dir/.wt/dd/feat-9-lib" ] || [ -d "$tmp/wt/dd/feat-9-lib" ] || fail "second project's worktree"
  d cleanup dd2 x1 --force >/dev/null
  pass "delegate: several repos need --repo; the same GitHub repo in two projects shares overlap checks, branch names are unique (exit 11)"

  # the orca launcher, against a fake orca-ide that keeps its terminals in tmux
  cat >"$tmp/bin/orca-ide" <<'EOF'
#!/usr/bin/env python3
import json, subprocess, sys
a = sys.argv[1:]
def opt(name, default=None):
    return a[a.index(name) + 1] if name in a else default
def tm(*args):
    return subprocess.run(["tmux", *args], capture_output=True, text=True)
if a[:2] == ["terminal", "create"]:
    title, cwd = opt("--title"), opt("--worktree").removeprefix("path:")
    r = tm("new-session", "-d", "-s", "orca-" + title, "-x", "200", "-y", "50", "-c", cwd, opt("--command"))
    sys.exit(r.returncode) if r.returncode else print(json.dumps({"result": {"terminal": {"handle": "orca-" + title}}}))
elif a[:2] == ["terminal", "show"]:
    sys.exit(tm("has-session", "-t", opt("--terminal")).returncode)
elif a[:2] == ["terminal", "read"]:
    print(json.dumps({"result": {"text": tm("capture-pane", "-p", "-t", opt("--terminal"), "-S", "-100").stdout}}))
elif a[:2] == ["terminal", "send"]:
    if "--text" in a:
        tm("send-keys", "-t", opt("--terminal"), "-l", opt("--text"))
    if "--enter" in a:
        tm("send-keys", "-t", opt("--terminal"), "Enter")
elif a[:2] == ["terminal", "close"]:
    tm("kill-session", "-t", opt("--terminal"))
EOF
  chmod +x "$tmp/bin/orca-ide"
  rc=0; SWE_LAUNCHER=orca d start dd c7 --files lib/ --goal "via orca" --branch feat/7-orca --repo dd >"$tmp/d8.txt" 2>&1 || rc=$?
  [ "$rc" = 0 ] && grep -q "watch it in Orca" "$tmp/d8.txt" || { cat "$tmp/d8.txt"; fail "start through the orca launcher"; }
  for _ in $(seq 20); do SWE_LAUNCHER=orca d status dd c7 | grep -q '"outcome": "CARD DONE' && break; sleep 1; done
  SWE_LAUNCHER=orca d status dd c7 | grep -q '"outcome": "CARD DONE' || fail "outcome not read through the orca launcher"
  SWE_LAUNCHER=orca d stop dd c7 >/dev/null; ! tmux has-session -t orca-dd-c7 2>/dev/null || fail "orca terminal not closed"
  d cleanup dd c7 --force >/dev/null
  pass "orca launcher: a card runs in an Orca terminal (handle kept in state), its outcome is read from the screen, stop closes it"

  d orchestrate dd --dry-run >"$tmp/orch.txt" 2>&1 || true
  SWE_MODELS="$here/examples/models.codex-only.yaml" SWE_PROJECTS="$tmp/dd-projects.yaml" "$fleet" orchestrate dd --dry-run >"$tmp/orch.txt" 2>&1 || { cat "$tmp/orch.txt"; fail "orchestrate dry-run"; }
  grep -q "would run (tmux): dd-orchestrator in $tmp: .*codex --model gpt-6-sol" "$tmp/orch.txt" && grep -q "brief-orchestrator.md" "$tmp/orch.txt" || { cat "$tmp/orch.txt"; fail "orchestrate plan"; }
  mapfile -t cmd < <(SWE_MODELS="$here/examples/models.codex-only.yaml" "$fleet" models cmd developer)
  [ "${cmd[*]}" = "codex exec --model gpt-6-sol -c model_reasoning_effort=medium --dangerously-bypass-approvals-and-sandbox" ] || fail "codex headless argv: ${cmd[*]}"
  pass "orchestrate: any CLI (codex here) is started in the project directory with the orchestrator brief; codex has a headless command"

  echo '{"state":"OPEN"}' >"$tmp/view.json"
  rc=0; GH_VIEW="$tmp/view.json" d cleanup dd c1 >"$tmp/clean.txt" 2>&1 || rc=$?
  [ "$rc" = 2 ] && grep -q "not MERGED" "$tmp/clean.txt" && [ -d "$tmp/wt/dd/feat-1-a" ] || { cat "$tmp/clean.txt"; fail "cleanup must refuse an unmerged PR"; }
  echo '{"state":"MERGED"}' >"$tmp/view.json"
  GH_VIEW="$tmp/view.json" d cleanup dd c1 >/dev/null || fail "cleanup after merge"
  [ ! -e "$tmp/wt/dd/feat-1-a" ] && ! tmux has-session -t dd-c1 2>/dev/null && [ ! -e "$tmp/state/dd/c1.json" ] \
    && ! git -C "$tmp/dd" branch --list feat/1-a | grep -q . || fail "cleanup left something behind"
  pass "delegate: cleanup refuses an unmerged PR; after the merge it removes the session, worktree, branch and record"
else
  echo "SKIP swe-cli delegate tests: tmux is not installed"
fi

echo "all passed"
