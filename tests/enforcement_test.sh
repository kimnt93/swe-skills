#!/usr/bin/env bash
# enforcement_test: every rule the skills enforce fails on a bad example and passes on the clean
# template, and every shipped script that has a self-test passes it.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
skills="$root/src/skills"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

# 1. Go data structs: no pointers, no omitempty (go-code/scripts/structcheck)
sc="$skills/go-code/scripts/structcheck"
(cd "$sc" && go test ./... >/dev/null) || fail "structcheck unit tests"
(cd "$sc" && go run . "$skills/go-code/assets/template") || fail "structcheck on the clean Go template"
rc=0
(cd "$sc" && go run . "$root/tests/fixtures/bad-go") >"$tmp/go.txt" 2>&1 || rc=$?
[ "$rc" = 1 ] || { cat "$tmp/go.txt"; fail "structcheck must exit 1 on the bad fixture"; }
grep -q "Order.Price is a pointer" "$tmp/go.txt" && grep -q "Order.Note uses omitempty" "$tmp/go.txt" \
  || { cat "$tmp/go.txt"; fail "structcheck findings"; }
pass "go: structcheck passes the template, fails the bad fixture with both findings"

# 1b. Go layering (go-code/scripts/archcheck)
ac="$skills/go-code/scripts/archcheck"
(cd "$ac" && go test ./... >/dev/null) || fail "archcheck unit tests"
(cd "$ac" && go run . "$skills/go-code/assets/template") || fail "archcheck on the clean Go template"
rc=0
(cd "$ac" && go run . "$root/tests/fixtures/bad-arch-go") >"$tmp/arch.txt" 2>&1 || rc=$?
[ "$rc" = 1 ] && grep -q "the domain does no I/O" "$tmp/arch.txt" && grep -q "application may import only domain, application" "$tmp/arch.txt" \
  || { cat "$tmp/arch.txt"; fail "archcheck on the breaching fixture"; }
pass "go: archcheck passes the template, fails a domain I/O import and an application -> adapter import"

# 2. Python imports: no pydantic, no pandas (ruff TID251 in the py-code template)
ruff=(ruff)
command -v ruff >/dev/null || ruff=(uv tool run ruff)
config="$skills/py-code/assets/template/pyproject.toml"
(cd "$skills/py-code/assets/template" && "${ruff[@]}" check . >/dev/null) || fail "ruff on the clean Python template"
"${ruff[@]}" check --config "$config" --no-cache "$root/tests/fixtures/bad-py" >"$tmp/py.txt" 2>&1 && fail "ruff must fail the bad fixture"
grep -q "TID251.*Use polars" "$tmp/py.txt" && grep -q "TID251.*Use msgspec" "$tmp/py.txt" \
  || { cat "$tmp/py.txt"; fail "ruff banned-api messages"; }
pass "python: ruff passes the template, bans pydantic and pandas with the fix in the message"

# 2b. Python layering (import-linter contracts in the py-code template)
li=(lint-imports)
command -v lint-imports >/dev/null || li=(uv tool run --from import-linter lint-imports)
(cd "$skills/py-code/assets/template" && PYTHONPATH=src "${li[@]}" --no-cache >"$tmp/li.txt" 2>&1) || { cat "$tmp/li.txt"; fail "lint-imports on the clean Python template"; }
rc=0
(cd "$root/tests/fixtures/bad-arch-py" && PYTHONPATH=src "${li[@]}" --no-cache >"$tmp/li.txt" 2>&1) || rc=$?
[ "$rc" = 1 ] && grep -q "Contracts: 0 kept, 2 broken" "$tmp/li.txt" || { cat "$tmp/li.txt"; fail "lint-imports on the breaching fixture"; }
rm -rf "$skills/py-code/assets/template/.import_linter_cache" "$root/tests/fixtures/bad-arch-py/.import_linter_cache"
pass "python: lint-imports passes the template, breaks both contracts on the breaching fixture"

# 3. every shipped script with a self-test passes it
count=0
while IFS= read -r script; do
  python3 "$script" --self-test >"$tmp/self.txt" 2>&1 || { cat "$tmp/self.txt"; fail "self-test: ${script#$skills/}"; }
  count=$((count + 1))
done < <(grep -rl -- '--self-test' "$skills"/*/scripts/*.py | sort)
[ "$count" -gt 0 ] || fail "no self-tests found"
pass "self-tests: $count shipped scripts"

# 3b. shell scripts with a self-test
bash "$skills/project/scripts/setup_repo.sh" --self-test >"$tmp/repo.txt" 2>&1 || { cat "$tmp/repo.txt"; fail "setup_repo.sh self-test"; }
pass "setup_repo.sh: repo settings, branch protection, labels (fake gh)"

# 4. verify.mk renders: static gates, structcheck for Go, live probe with the service name
mkdir -p "$tmp/svc"
cp "$skills/verify-create/assets/verify.mk" "$tmp/svc/"
printf 'include verify.mk\nlint:\n\t@true\ntest-race:\n\t@true\n' >"$tmp/svc/Makefile"
touch "$tmp/svc/go.mod"
make -s -n -C "$tmp/svc" verify-static PLUGIN_SKILLS=/x >"$tmp/mk.txt"
grep -q "/x/api-contract/scripts/audit_api.py" "$tmp/mk.txt" && grep -q "go-code/scripts/structcheck && go run" "$tmp/mk.txt" \
  && grep -q "go-code/scripts/archcheck && go run" "$tmp/mk.txt" \
  || { cat "$tmp/mk.txt"; fail "verify.mk static gates"; }
pass "verify.mk: static gates include the contract audit, structcheck and archcheck"
python3 - "$root" <<'PY' || fail "playbook skills"
import re, sys
from pathlib import Path
root = Path(sys.argv[1]); bad = []
expected = {"playbook", "playbook-plan", "playbook-review", "playbook-quick"}
actual = {p.parent.name for p in (root / "src/skills").glob("playbook*/SKILL.md")}
if actual != expected:
    bad.append(f"playbooks must be exactly {sorted(expected)}, got {sorted(actual)}")
for f in sorted((root / "src/skills").glob("playbook*/SKILL.md")):
    text = f.read_text(encoding="utf-8")
    if not re.search(r"^  group: start$", text, re.M):
        bad.append(f"{f.parent.name}: group must be start")
    if not re.search(r'^  summary: ".+"$', text, re.M):
        bad.append(f"{f.parent.name}: must have non-empty summary")
checks = {
    "playbook-review": ["different model family", "PASS", "FAIL", "fix"],
    "playbook-plan": ["architect", "plan comment", "CTO", "send it back", "**Stop here.**", "/orchestration"],
    "playbook-quick": ["No architect", "CTO/CEO merges", "send it back", "--match-head-commit", "/orchestration", "of 3.", "Stopped by", "can-remove"],
    "playbook": ["playbook-plan", "playbook-review", "playbook-quick"],
}
for name, needles in checks.items():
    text = (root / "src/skills" / name / "SKILL.md").read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            bad.append(f"{name}: missing {needle!r}")
# one catalog: the page and the repo labels equal the machine copy the linter reads
import json, subprocess
skills = root / "src/skills"
catalog = json.loads((skills / "work-package/assets/catalog.json").read_text(encoding="utf-8"))
page = (skills / "write-issue/references/catalog.md").read_text(encoding="utf-8")
def table(heading):
    section = page.split(f"## {heading}")[1].split("\n## ")[0]
    return re.findall(r"^\| `([^`]+)` \|", section, re.M)
for key, heading in (("types", "Task type"), ("lanes", "Lane"), ("difficulties", "Difficulty"), ("flags", "Flags"),
                     ("priorities", "Priority"), ("issue_kinds", "Issue kinds"), ("comment_kinds", "Comment kinds")):
    if table(heading) != list(catalog[key]):
        bad.append(f"catalog.md '{heading}' lists {table(heading)}, catalog.json has {list(catalog[key])}")
labels = [x["name"] for x in json.loads((skills / "project/assets/labels.json").read_text(encoding="utf-8"))]
want = [n for g in ("types", "lanes", "difficulties", "flags") for n in catalog[g]]
if labels != want:
    bad.append(f"project/assets/labels.json differs from the catalog: {sorted(set(labels) ^ set(want))}")
# every filled example passes the linter; every template has the sections the linter asks for
sys.path.insert(0, str(skills / "work-package/scripts"))
import package_lint as L
lint = [sys.executable, str(skills / "work-package/scripts/package_lint.py")]
plan = skills / "playbook-plan"
def issue(kind, title, difficulty, path):
    return ["issue", "--kind", kind, "--title", title, "--label", "enhancement", "--label", "backend",
            "--label", difficulty, "--body-file", str(path)]
for args in (
    issue("planning", "EXPORT-00: Export the filtered order list as CSV", "medium", plan / "assets/example/card.md"),
    issue("epic", "BULK-00: Epic — Export any list", "hard", skills / "write-issue/assets/example/epic.md"),
    ["comment", "--kind", "plan", "--body-file", str(plan / "assets/example/plan-comment.md")],
    ["comment", "--kind", "epic-plan", "--body-file", str(skills / "write-comment/assets/example/epic-plan.md")],
    ["comment", "--kind", "decision", "--body-file", str(plan / "assets/example/acceptance.md")],
):
    run = subprocess.run(lint + args, capture_output=True, text=True, env={k: v for k, v in __import__("os").environ.items() if k != "AGENT_NAME"})
    if run.returncode:
        bad.append(f"{args[-1]}: {run.stdout.strip() or run.stderr.strip()}")
for name in L.TEMPLATES:
    _, _, sections = L.read_template(name)
    text = L.template_path(name).read_text(encoding="utf-8")
    if not sections or text.rstrip().splitlines()[-1] != "Created: <author>" or L.GENERATED_RE.search(text):
        bad.append(f"{name} template: needs sections, 'Created: <author>' as its last line and no tool footer")
for name, kind in (("verdict-pass.md", "verdict"), ("verdict-fail.md", "verdict")):
    bad += [f"{name}: {x}" for x in L.lint_comment(kind, (skills / "write-comment/assets/example" / name).read_text(encoding="utf-8"))]
run = subprocess.run([sys.executable, str(root / "scripts/gen_docs.py"), "--check"], capture_output=True, text=True)
if run.returncode:
    bad.append(f"generated files are stale (make docs): {run.stdout.strip()}")
# no skill tells an agent to commit without its name
for doc in sorted(skills.rglob("*.md")):
    for line in doc.read_text(encoding="utf-8").splitlines():
        if re.match(r"\s*git commit\b", line):
            bad.append(f"{doc.relative_to(skills)}: plain 'git commit'; use agent_identity.py git -- commit")
# the quick playbook's example: issues, comments and PR body pass the linters
import os
sys.path.insert(0, str(skills / "github/scripts"))
import pr_lint as P
quick = skills / "playbook-quick/assets/example"
os.environ.pop("AGENT_NAME", None)
def text(name):
    return (quick / name).read_text(encoding="utf-8")
for name, kind, title, lane in (("parent.md", "epic", "ORD-00: Epic — Order times in the user's zone", "backend"),
                                ("issue-api.md", "package", "ORD-01: Return order times in UTC", "backend"),
                                ("issue-web.md", "package", "ORD-02: Show order times in the local zone", "frontend")):
    bad += [f"{name}: {x}" for x in L.lint_issue(kind, title, ["bug", lane, "simple"], text(name))]
for name, kind in (("changes.md", "decision"), ("fix.md", "fix"), ("acceptance.md", "decision"), ("merge.md", "merge"),
                   ("stopped.md", "decision")):
    bad += [f"{name}: {x}" for x in L.lint_comment(kind, text(name))]
branch, title = "ord-02/local-order-times", "fix(ord-02): show local order times"
bad += [f"pr.md (work-package): {x}" for x in L.lint_pr(branch, title, text("pr.md"))]
bad += [f"pr.md (github): {x}" for x in P.lint(branch, title, text("pr.md"), [], 40, [], 400)
        + P.lint_author(text("pr.md"), [("4f2c9a1d", ["Developer (example)"])], [])]
# no quick command or message removes a worktree by force or deletes its branch
for doc in sorted((skills / "playbook-quick").rglob("*.md")):
    for line in doc.read_text(encoding="utf-8").splitlines():
        if re.search(r"worktree (rm|remove) .*--(force|delete-branch)", line):
            bad.append(f"{doc.relative_to(skills)}: forced or branch-deleting worktree removal: {line.strip()}")
# a squash or merge commit is authored by the account, not the agent: every documented merge is a rebase
for doc in sorted(skills.rglob("*.md")):
    for line in doc.read_text(encoding="utf-8").replace("\\\n", " ").splitlines():
        if re.match(r"\s*gh pr merge\b", line) and ("--rebase" not in line or re.search(r"--(squash|merge)\b", line)):
            bad.append(f"{doc.relative_to(skills)}: merge with --rebase so commits keep the agent's name: {line.strip()}")
for doc in sorted(skills.rglob("*")):
    if doc.is_file() and doc.suffix in (".md", ".sh", ".py") and "-cli merge" in doc.read_text(encoding="utf-8"):
        bad.append(f"{doc.relative_to(skills)}: names a CLI merge command that does not exist")
plan = skills / "playbook-plan"
commands = (plan / "references/orchestration.md").read_text(encoding="utf-8").replace("\\\n", " ")
for line in commands.splitlines():
    if "orchestration gate-create --" in line and ("--question" not in line or re.search(r"--(run|reason)\b", line)):
        bad.append(f"gate-create takes --task and --question, not --run or --reason: {line.strip()}")
if bad:
    raise SystemExit("; ".join(bad))
PY
pass "playbook skills: exactly three CTO pipelines, valid metadata, plan/review/quick boundaries and comment format"
echo "all passed"
