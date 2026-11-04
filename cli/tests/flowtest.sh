#!/usr/bin/env bash
# flowtest: prove the workflow runner end to end against fake claude / omp / gh and a scratch repo.
# Plan -> parallel cards (build, checks, review with a fix round) -> report -> manager merge -> clean.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
fleet="$here/bin/main"
tmp="$(mktemp -d)"
cleanup() { tmux ls 2>/dev/null | cut -d: -f1 | { grep '^ft-' || true; } | while read -r s; do tmux kill-session -t "$s" 2>/dev/null || true; done; rm -rf "$tmp"; return 0; }
trap cleanup EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }
command -v tmux >/dev/null || { echo "SKIP flowtest: tmux is not installed"; exit 0; }

mkdir -p "$tmp/bin" "$tmp/fs"
export SWE_STATE="$tmp/state" SWE_TMP="$tmp/ftmp" CLAUDE_JSON="$tmp/claude.json" SWE_READY_TIMEOUT=20 SWE_POLL=1 FAKE_STATE="$tmp/fs"
export SWE_PROJECTS="$tmp/projects.yaml" PATH="$tmp/bin:$PATH"

# --- fakes: one agent script for claude and omp, one gh
cat >"$tmp/bin/claude" <<'EOF'
#!/usr/bin/env python3
import json, os, re, subprocess, sys, time
state = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..", "fs")  # the tmux server does not inherit the test env
name = os.path.basename(sys.argv[0])
os.makedirs(".swe", exist_ok=True)
ARGV = f"{name} " + " ".join(sys.argv[1:]) + "\n"
print(f"fake {name} " + " ".join(sys.argv[1:]), flush=True)
print("❯ π >", flush=True)
def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()
for line in sys.stdin:
    m = re.search(r"\.swe/(brief-[\w-]+\.md)", line)
    if not m:
        continue
    brief = open(os.path.join(".swe", m.group(1))).read()
    role = re.search(r"# You are the ([\w-]+)", brief).group(1)
    report = re.search(r"Write your report to `([^`]+)`", brief).group(1)
    files = re.search(r"files you may change: (.*)", brief)
    open(f".swe/argv-{role}.txt", "w").write(ARGV)
    print("esc to interrupt", flush=True)
    time.sleep(2)
    if role == "planner":
        plan = re.search(r"Write the plan to (\S+)", brief).group(1)
        cards = [{"id": "c1", "title": "a", "goal": "add a", "files": ["src/a.txt"], "risk": "standard", "tier": "mid", "workflow": "card"},
                 {"id": "c2", "title": "b", "goal": "add b", "files": ["src/b.txt"], "risk": "standard", "tier": "mid", "workflow": "card"}]
        if "documentation" in brief.lower() or "docs-card" in brief:
            cards = [{"id": "d1", "title": "doc", "goal": "write docs", "files": ["docs/"], "risk": "low", "workflow": "docs-card", "type": "docs"}]
        json.dump({"summary": "s", "cards": cards}, open(plan, "w"))
        open(report, "w").write("planned\n")
        print(f"NODE DONE {len(cards)} card(s) planned", flush=True)
    elif role in ("developer", "documenter", "ci-fixer", "integrator", "scribe"):
        first = files.group(1).split(",")[0].strip() if files else "note.txt"
        target = first + "item.txt" if first.endswith("/") else first
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        open(target, "a").write(role + "\n")
        sh("git", "add", target)
        sh("git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", f"feat: {role}")
        sha = sh("git", "rev-parse", "--short", "HEAD")
        branch = sh("git", "branch", "--show-current")
        pr_file = os.path.join(state, "pr-" + branch.replace("/", "-"))
        import fcntl
        with open(os.path.join(state, "pr.lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not os.path.exists(pr_file):
                n = len([f for f in os.listdir(state) if f.startswith("pr-")]) + 1
                open(pr_file, "w").write(str(n))
        n = open(pr_file).read()
        open(os.path.join(state, f"head-{n}"), "w").write(sh("git", "rev-parse", "HEAD"))
        open(report, "w").write(f"{role} did the work at {sha}\n\n## Learned\n- make verify is the proof command\n")
        print(f"CARD DONE {sha} https://example.test/acme/app/pull/{n}", flush=True)
    elif role == "reviewer":
        sha = sh("git", "rev-parse", "--short", "HEAD")
        for f in os.listdir(state):
            if f.startswith("behind-"):
                os.unlink(os.path.join(state, f))
        verdict, n = "PASS", 0
        if os.path.exists(os.path.join(state, "always-fail")):
            verdict, n = "FAIL", 2
        elif os.path.exists(os.path.join(state, "fail-once")) and not os.path.exists(".swe/failed-once"):
            open(".swe/failed-once", "w").write("1")
            verdict, n = "FAIL", 1
        open(report, "w").write(f"review {verdict}\n")
        print(f"REVIEW DONE {sha} {n} {verdict}", flush=True)
    else:
        open(report, "w").write("verified\n")
        print("NODE DONE 0 regression(s) filed, 0 finding(s) logged", flush=True)
    print("❯ π >", flush=True)
EOF
chmod +x "$tmp/bin/claude"; ln -s claude "$tmp/bin/omp"
cat >"$tmp/bin/gh" <<'EOF'
#!/usr/bin/env bash
s="$FAKE_STATE"; args="$*"
case "$1 $2" in
  "pr view")
    if [[ "$args" == *"--json state"* ]]; then [ -e "$s/merged-any" ] && echo '{"state":"MERGED"}' || echo '{"state":"OPEN"}'; exit 0; fi
    if [[ "$args" == *headRefName* ]]; then echo "{\"headRefName\":\"$(cat "$s/prbranch-$3")\"}"; exit 0; fi
    n="$3"; head="$(cat "$s/head-$n" 2>/dev/null || true)"; m=CLEAN; [ -e "$s/behind-$n" ] && m=BEHIND
    files='[{"path":"CHANGELOG.md"}]'; [ -e "$s/nolog-$n" ] && files='[{"path":"a.py"}]'
    echo "{\"headRefOid\":\"$head\",\"state\":\"OPEN\",\"isDraft\":false,\"mergeStateStatus\":\"$m\",\"title\":\"feat: card $n\",\"url\":\"https://github.com/o/r/pull/$n\",\"files\":$files,\"labels\":[]}";;
  "pr checks") echo '[{"name":"verify","bucket":"pass"}]';;
  "pr merge") echo "MERGED $*" >>"$s/gh.log"; touch "$s/merged-any";;
  "auth status") exit 0;;
esac
EOF
chmod +x "$tmp/bin/gh"

# --- a project: directory with one clone of a scratch origin
git init -q --bare "$tmp/origin.git"; mkdir -p "$tmp/proj"
git clone -q "$tmp/origin.git" "$tmp/proj/app" 2>/dev/null
( cd "$tmp/proj/app" && git config user.email t@t && git config user.name t && git checkout -q -b main \
  && printf 'verify:\n\t@echo ok\n' >Makefile && git add . && git commit -qm "chore: init" && git push -q origin main )
printf 'projects:\n  ft:\n    dir: %s\n    description: Flow demo\n    repos:\n      app: {github: acme/app}\n' "$tmp/proj" >"$SWE_PROJECTS"

# 1. the workflows are valid and the graph shows roles, harnesses, tiers
"$fleet" flow validate >"$tmp/val.txt" || { cat "$tmp/val.txt"; fail "validate"; }
"$fleet" flow graph card | grep -q "reviewer \[other/top/high\]" || fail "graph"
printf 'nodes:\n  a: {role: nobody}\n  b: {needs: [a], role: developer}\n  c: {needs: [b], role: developer}\n' >"$tmp/bad.yaml"
mkdir -p "$tmp/proj/.swe/workflows"; cp "$tmp/bad.yaml" "$tmp/proj/.swe/workflows/bad.yaml"
"$fleet" flow validate ft bad >"$tmp/val.txt" && fail "a workflow with an unknown role validated"
grep -q "unknown role" "$tmp/val.txt" || fail "unknown role message"
printf 'nodes:\n  a: {needs: [b], role: developer}\n  b: {needs: [a], role: developer}\n' >"$tmp/proj/.swe/workflows/bad.yaml"
"$fleet" flow validate ft bad >"$tmp/val.txt" || true
grep -q "cycle" "$tmp/val.txt" || fail "cycle not found"
rm "$tmp/proj/.swe/workflows/bad.yaml"
"$fleet" flow run ft feature --goal "two files" --dry-run >"$tmp/dry.txt"
grep -q "planner \[project/mid/high\]" "$tmp/dry.txt" || fail "dry-run"
pass "flow: workflows validate (unknown role and cycles are found); graph and dry-run show role, harness, tier, effort"

# 2. a feature: plan -> two cards in parallel -> report; the reviewer is another family; a review FAIL gets one fix round
touch "$FAKE_STATE/fail-once"
"$fleet" flow run ft feature --goal "two files" >"$tmp/run1.txt" 2>&1 || { tail -30 "$tmp/run1.txt"; fail "flow run"; }
python3 - "$SWE_TMP/swe/ft/r1/run.json" <<'PY' || { cat "$tmp/run1.txt"; fail "run state"; }
import json, sys
d = json.load(open(sys.argv[1]))
n = d["nodes"]
assert d["status"] == "ready", d["status"]
assert all(n[k]["status"] == "done" for k in ("plan", "cards", "report", "c1/build", "c2/build", "c1/checks", "c1/review", "c2/review")), {k: v["status"] for k, v in n.items()}
assert n["c1/review"]["cli"] == "omp" and n["c1/build"]["cli"] == "claude", (n["c1/review"]["cli"], n["c1/build"]["cli"])
assert n["c1/review"].get("rounds") == 1 and n["c2/review"].get("rounds") == 1, "the FAIL round"
assert n["c1/review"]["outputs"]["verdict"] == "PASS"
b1, b2 = n["c1/build"], n["c2/build"]
assert max(b1["started"], b2["started"]) < min(b1["finished"], b2["finished"]), "the two builds did not overlap"
assert len(d["ready"]) == 2 and {e["pr"] for e in d["ready"]} == {"1", "2"}, d["ready"]
PY
grep -rqF 'Enable only these `swe` skills for this role: developer, swe, tdd, deslop, changelog, github' "$tmp/proj/.wt/app/" || fail "build node did not get only its skills"
grep -rqF 'Disable every other `swe` skill' "$tmp/proj/.wt/app/" || fail "brief does not disable the other plugin skills"
grep -rq "^## Learned" "$SWE_TMP/swe/ft/r1/report.md" || fail "learned facts are not collected into the run report"
! grep -rq "go-code" "$tmp/proj/.wt/app/"*/.swe/brief-*.md || fail "a build brief names a language skill the role does not enable"
grep -q "ready to merge (2)" "$SWE_TMP/swe/ft/r1/report.md" || fail "report"
pass "flow feature: plan, two cards in parallel (own worktrees), checks, review by omp (another family), one fix round each, report lists 2 PRs ready"

# 3. a small model for documentation: haiku on claude, no effort flag
rm -f "$FAKE_STATE/fail-once"
"$fleet" flow run ft docs --goal "write docs" >"$tmp/run2.txt" 2>&1 || { tail -30 "$tmp/run2.txt"; fail "docs run"; }
argv="$(cat "$tmp/proj/.wt/app/"*/.swe/argv-documenter.txt)"
case "$argv" in *"--model haiku"*) ;; *) fail "documentation did not run on haiku: $argv";; esac
case "$argv" in *--effort*) fail "haiku got an effort flag: $argv";; esac
grep -q '"cli": "claude"' "$SWE_TMP/swe/ft/r2/run.json" && grep -q '"tier": "low"' "$SWE_TMP/swe/ft/r2/run.json" || fail "docs tiers"
pass "flow docs: the documenter runs on the low tier (haiku, no effort flag); its reviewer is the other family"

# 4. the manager merges (a branch that is behind gets the reviewer to update it), then cleans: nothing is left
touch "$FAKE_STATE/behind-2" "$FAKE_STATE/nolog-1"
"$fleet" flow merge ft r1 --approved >"$tmp/nolog.txt" 2>&1 && fail "a PR without a changelog entry was merged"
grep -q "CHANGELOG.md is missing" "$tmp/nolog.txt" && grep -q "flow run ft changelog" "$tmp/nolog.txt" || { cat "$tmp/nolog.txt"; fail "missing changelog not reported"; }
rm -f "$FAKE_STATE/nolog-1"
"$fleet" flow merge ft r1 --approved >"$tmp/merge.txt" 2>&1 || { cat "$tmp/merge.txt"; fail "flow merge"; }
[ "$(grep -c '^MERGED pr merge' "$FAKE_STATE/gh.log")" = 2 ] || { cat "$FAKE_STATE/gh.log"; fail "both PRs were not merged"; }
grep -q "the reviewer updates the branch" "$tmp/nolog.txt" || fail "a behind branch was not handed to the reviewer"
"$fleet" flow merge ft r2 --approved >/dev/null 2>&1 || fail "merge r2"
log="$tmp/proj/changelog/project.md"
[ -f "$log" ] && [ "$(grep -c 'feat: \|`app` feat' "$log")" -ge 3 ] && grep -q '^## 20' "$log" && [ -f "$tmp/proj/changelog/app.md" ] || { cat "$log" 2>&1; fail "merged PRs not recorded in changelog/"; }
"$fleet" changelog show --project ft --repo app | grep -q "feat" || fail "changelog show"
"$fleet" flow clean ft r1 >"$tmp/clean.txt" 2>&1 || { cat "$tmp/clean.txt"; fail "flow clean r1"; }
"$fleet" flow clean ft r2 >"$tmp/clean.txt" 2>&1 || { cat "$tmp/clean.txt"; fail "flow clean r2"; }
[ ! -e "$SWE_TMP/swe/ft/r1" ] && [ ! -e "$SWE_TMP/swe/ft/r2" ] || fail "tmp run directories remain"
[ "$(git -C "$tmp/proj/app" worktree list | wc -l)" = 1 ] || { git -C "$tmp/proj/app" worktree list; fail "worktrees remain"; }
[ -z "$(git -C "$tmp/proj/app" branch --list 'feat/*' 'docs/*')" ] || fail "branches remain"
[ -z "$(ls "$SWE_STATE/ft" 2>/dev/null)" ] || fail "card records remain"
! tmux ls 2>/dev/null | grep -q '^ft-' || fail "sessions remain"
[ "$(git -C "$tmp/proj/app" branch --show-current)" = main ] && [ -z "$(git -C "$tmp/proj/app" status --porcelain)" ] || fail "central clone not clean"
pass "flow merge + clean: the manager merges the ready PRs (a behind branch is updated by the reviewer first), then no session, worktree, branch, record or tmp directory is left"

# 5. a review that keeps failing exhausts its fix rounds: the run needs attention, the card is not ready, nothing merges
touch "$FAKE_STATE/always-fail"
"$fleet" flow run ft feature --goal "two files" >"$tmp/run3.txt" 2>&1 && fail "a run whose reviews always FAIL reported success"
rm -f "$FAKE_STATE/always-fail"
r3="$(sed -n 's/^run \(r[0-9]*\):.*/\1/p' "$tmp/run3.txt" | tail -1)"
python3 - "$SWE_TMP/swe/ft/$r3/run.json" <<'PY' || { tail -20 "$tmp/run3.txt"; fail "exhausted review state"; }
import json, sys
d = json.load(open(sys.argv[1])); n = d["nodes"]
assert d["status"] == "attention", d["status"]
assert n["c1/review"]["status"] == "failed" and n["c1/review"].get("rounds") == 2, n["c1/review"]
assert not d.get("ready"), d.get("ready")
PY
"$fleet" flow merge ft "$r3" --approved >/dev/null 2>&1 && fail "flow merge merged a run with nothing ready"
"$fleet" flow clean ft "$r3" >/dev/null 2>&1 || fail "clean r3"
pass "flow review FAIL: two fix rounds then the node fails, the run needs attention, nothing is ready to merge"

# 6. the changelog workflow works on an existing PR branch (workspace pr), runs its checks on that PR and a review
git -C "$tmp/proj/app" push -q origin main:refs/heads/feat/existing
echo feat/existing >"$FAKE_STATE/prbranch-9"; echo 0000 >"$FAKE_STATE/head-9"
"$fleet" flow run ft changelog --input pr=9 --input repo=acme/app >"$tmp/run4.txt" 2>&1 || { tail -30 "$tmp/run4.txt"; fail "changelog run"; }
r4="$(sed -n 's/^run \(r[0-9]*\):.*/\1/p' "$tmp/run4.txt" | tail -1)"
python3 - "$SWE_TMP/swe/ft/$r4/run.json" <<'PY' || { tail -20 "$tmp/run4.txt"; fail "changelog state"; }
import json, sys
d = json.load(open(sys.argv[1])); n = d["nodes"]
assert all(n[k]["status"] == "done" for k in ("add", "checks", "review", "report")), {k: v["status"] for k, v in n.items()}
assert n["add"]["cli"] == "claude" and n["add"]["tier"] == "low" and n["review"]["cli"] == "omp", (n["add"]["cli"], n["add"]["tier"])
PY
"$fleet" flow clean ft "$r4" >/dev/null 2>&1 || fail "clean r4"
pass "flow changelog: a scribe on the low tier works on an existing PR branch, checks run on that PR, another family reviews"
echo "all passed"
