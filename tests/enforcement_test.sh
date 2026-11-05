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
python3 - "$root" <<'PY' || fail "play skills"
import re, sys
from pathlib import Path
root = Path(sys.argv[1]); bad = []
for f in sorted((root / "src/skills").glob("play*/SKILL.md")):
    text = f.read_text(encoding="utf-8")
    if not re.search(r"^  group: start$", text, re.M):
        bad.append(f"{f.parent.name}: group must be start")
    if f.parent.name == "play":
        continue
    wf = re.search(r"swe-cli flow run <project> ([\w-]+)", text)
    if not wf or not (root / "cli/workflows" / f"{wf.group(1)}.yaml").is_file():
        bad.append(f"{f.parent.name}: names no existing workflow ({wf.group(1) if wf else 'none'})")
if bad:
    raise SystemExit("; ".join(bad))
PY
pass "play skills: each is group start and names a workflow that exists in cli/workflows"
echo "all passed"
