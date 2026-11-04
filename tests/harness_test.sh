#!/usr/bin/env bash
# harness_test: the plugin installs into every harness the installer knows, in a scratch home.
#   - copy mode (--plugin no) for every harness, user and project scope: the router and every skill
#     land, every `name:` equals its directory, every link resolves, uninstall leaves nothing
#   - plugin mode (dry run) for Claude Code, Codex and oh-my-pi issues the marketplace + install commands
#   - the Makefile's harness targets are exactly the installer's harnesses
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

python3 scripts/build.py >/dev/null
name="$(cli/bin/main name)"
dist="dist/$name"
installer="$dist/scripts/install.py"
expected="$(python3 -c "import json; print(len(json.load(open('$dist/build.json'))['skills']))")"
mapfile -d ' ' -t harnesses < <(python3 "$installer" agents --names | tr -d '\n')

check_tree() {  # <dir> <label>
  python3 - "$1" "$expected" "$name" <<'PY' || fail "$2: installed tree"
import pathlib, re, sys
base, expected, name = pathlib.Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
skills = list(base.rglob("SKILL.md"))
assert len(skills) == expected, f"{len(skills)} skills installed, expected {expected}"
assert any(p.parent.name == name for p in skills), f"router {name} missing"
for md in skills:
    declared = re.search(r"^name:\s*(\S+)", md.read_text(), re.M).group(1)
    assert declared == md.parent.name, f"{md}: name {declared} != directory {md.parent.name}"
for md in base.rglob("*.md"):
    for target in re.findall(r"\]\(([^)#\s]+)", md.read_text()):
        if not target.startswith(("http", "mailto")) and not (md.parent / target).resolve().exists():
            raise AssertionError(f"{md.relative_to(base)}: broken link {target}")
PY
}

count=0
for harness in "${harnesses[@]}"; do
  [ -n "$harness" ] || continue
  home="$tmp/home-$harness"; mkdir -p "$home"
  PLUGIN_HOME="$home" python3 "$installer" install --agent "$harness" --plugin no >"$tmp/out.txt" 2>&1 || { cat "$tmp/out.txt"; fail "$harness: install"; }
  check_tree "$home" "$harness (user scope)"
  PLUGIN_HOME="$home" python3 "$installer" uninstall --agent "$harness" --plugin no >/dev/null 2>&1 || fail "$harness: uninstall"
  [ -z "$(find "$home" -name SKILL.md)" ] || fail "$harness: uninstall left skills"
  project="$tmp/project-$harness"; mkdir -p "$project"
  python3 "$installer" install --agent "$harness" --plugin no --scope project --project-dir "$project" >"$tmp/out.txt" 2>&1 || { cat "$tmp/out.txt"; fail "$harness: project install"; }
  check_tree "$project" "$harness (project scope)"
  count=$((count + 1))
done
pass "copy mode: $count harnesses install $expected skills at user and project scope, uninstall cleanly"

for tool in claude codex omp; do
  out="$(python3 "$installer" install --agent "$tool" --plugin yes --dry-run 2>&1)"
  grep -qE "$tool plugin marketplace (add|update)" <<<"$out" && grep -qE "$tool plugin (install|add) .*$name@$name-skills" <<<"$out" \
    || { echo "$out"; fail "$tool: plugin commands"; }
done
pass "plugin mode: claude, codex and omp register the $name-skills marketplace and install $name@$name-skills"

declared="$(sed -n '/^HARNESSES/,/^$/p' Makefile | tr -s ' \\\n' '\n' | grep -E '^[a-z-]+$' | grep -vx 'HARNESSES' | sort | tr '\n' ' ')"
actual="$(printf '%s\n' "${harnesses[@]}" | grep -E '^[a-z-]+$' | sort | tr '\n' ' ')"
[ "$declared" = "$actual" ] || { echo "Makefile: $declared"; echo "installer: $actual"; fail "Makefile harness targets differ from the installer's"; }
pass "Makefile targets equal the installer's harnesses"
echo "all passed"
