#!/usr/bin/env bash
# build_test: prove the build, the validator and the installer, without touching the live harnesses.
#
#   tests/build_test.sh            build, validate, rename, copy-install, guards
#   tests/build_test.sh --claude   also load the built plugin in Claude Code and run /<name> (uses a few Haiku tokens)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cd "$root"
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

# 1. default name and an override both build and validate
unset PLUGIN_NAME PLUGIN_TITLE PLUGIN_DOMAIN PLUGIN_HOMEPAGE
python3 scripts/build.py >/dev/null
python3 dist/swe/scripts/validate_skills.py >/dev/null || fail "validate swe"
[ -f dist/swe/skills/swe/SKILL.md ] || fail "router not renamed to swe"
grep -q '"name": "swe-skills"' dist/swe/.claude-plugin/marketplace.json || fail "swe marketplace"
PLUGIN_NAME=qa PLUGIN_DOMAIN=acme.test python3 scripts/build.py >/dev/null
python3 dist/qa/scripts/validate_skills.py >/dev/null || fail "validate qa"
grep -q '^name: qa$' dist/qa/skills/qa/SKILL.md || fail "router name"
grep -q '"name": "qa"' dist/qa/.claude-plugin/plugin.json || fail "plugin manifest name"
grep -q '"homepage": "https://acme.test/qa"' dist/qa/.claude-plugin/plugin.json || fail "default homepage from the domain"
grep -q '"name": "qa-skills"' dist/qa/.claude-plugin/marketplace.json || fail "marketplace name"
grep -q '`/qa:go-code`' dist/qa/skills/qa/SKILL.md || fail "skill index"
grep -q '^\*\*Start here\*\*$' dist/qa/skills/qa/SKILL.md || fail "grouped index"
grep -q 'PUBLIC_DOMAIN=acme.test' dist/qa/skills/deployment-setup/assets/templates/deploy/prod.env || fail "PLUGIN_DOMAIN in templates"
! grep -rqE '@(PLUGIN|DOMAIN|OWNER|HOMEPAGE|SKILL_INDEX)@' dist/qa || fail "placeholder left"
pass "build: default 'swe', and PLUGIN_NAME=qa PLUGIN_DOMAIN=acme.test, both valid"

# 1b. subagents: rendered, with the model models.yaml gives their tier
grep -q '^model: sonnet$' dist/qa/agents/worker.md || fail "worker model from models.yaml"
grep -q '^model: opus$' dist/qa/agents/adversary.md || fail "adversary model from models.yaml"
grep -q 'qa' dist/qa/agents/adversary.md || fail "adversary not rendered"
[ -f dist/qa/LICENSE ] && grep -q '/qa <task>' dist/qa/README.md || fail "LICENSE or README"
[ -f dist/qa/CHANGELOG.md ] || fail "CHANGELOG in the plugin"
pass "agents: worker=sonnet, adversary=opus from models.yaml; LICENSE, README, CHANGELOG shipped"

# 1c. the owner's rule: no org name and no vq anywhere in the source, docs or build
hits="$(grep -rIniE 'vietquant|viet-quant|\bvq\b|vq-|VQ_' --exclude-dir=.git --exclude-dir=dist . dist/qa | grep -v '^./tests/build_test.sh:' || true)"
[ -z "$hits" ] || { echo "$hits" | head -20; fail "org name or vq found"; }
pass "no org name or vq in source, docs or build"

# 1d. the skill reference is generated from the skills and must be current
python3 scripts/gen_docs.py --check >/dev/null || fail "docs/skills.md is out of date: make docs"
pass "docs: skills.md matches the skills"

# 2. bad names are refused
PLUGIN_NAME=Bad_Name python3 scripts/build.py >/dev/null 2>&1 && fail "accepted Bad_Name"
PLUGIN_NAME=go-code python3 scripts/build.py >/dev/null 2>&1 && fail "accepted a name that collides with a skill"
pass "build: invalid and colliding names refused"

# 3. copy install (Hermes / OpenCode style): router unprefixed, others prefixed, every link resolves, uninstall is clean
PLUGIN_HOME="$tmp/home" python3 dist/qa/scripts/install.py install --agent hermes --plugin no >/dev/null
base="$tmp/home/.hermes/skills/qa"
[ -f "$base/qa/SKILL.md" ] || fail "router dir"
[ -f "$base/qa-go-code/SKILL.md" ] || fail "prefixed dir"
python3 - "$base" <<'EOF' || fail "installed links or names"
import pathlib, re, sys
base = pathlib.Path(sys.argv[1])
for md in base.rglob("*.md"):
    for target in re.findall(r"\]\(([^)#\s]+)", md.read_text()):
        if not target.startswith(("http", "mailto")) and not (md.parent / target).resolve().exists():
            sys.exit(f"broken link {md.relative_to(base)} -> {target}")
for skill_md in base.glob("*/SKILL.md"):
    name = re.search(r"^name:\s*(\S+)", skill_md.read_text(), re.M).group(1)
    if name != skill_md.parent.name:
        sys.exit(f"name {name} != dir {skill_md.parent.name}")
EOF
PLUGIN_HOME="$tmp/home" python3 dist/qa/scripts/install.py uninstall --agent hermes >/dev/null
[ -z "$(find "$tmp/home" -name SKILL.md)" ] || fail "uninstall left skills"
pass "install: copy mode, links and names valid, uninstall clean"

# 4. the validator catches what it is meant to catch (in a scratch copy)
cp -r dist/qa "$tmp/broken"
printf '\nUse the **arena** skill and `AskQuestion`. See the **nope** principle and [x](missing.md).\n' \
  >>"$tmp/broken/skills/tdd/SKILL.md"
sed -i 's/^metadata:$/disable-model-invocation: true\nmetadata:/' "$tmp/broken/skills/how/SKILL.md"
out="$(python3 "$tmp/broken/scripts/validate_skills.py" || true)"
for expected in "disable-model-invocation stops the router" "**arena** skill is not in this stack" "tool- or repository-specific term" "**nope** principle has no file" "broken link missing.md"; do
  grep -qF "$expected" <<<"$out" || fail "validator missed: $expected"
done
sed -i '/^  summary:/d' "$tmp/broken/skills/why/SKILL.md"
out="$(python3 "$tmp/broken/scripts/validate_skills.py" || true)"
grep -qF "metadata.summary is required" <<<"$out" || fail "validator missed a missing summary"
pass "validator: dangling skill, non-portable term, dangling principle, broken link"

# 5. optional: Claude Code loads the built plugin and /<name> answers with the stack index
if [ "${1:-}" = "--claude" ]; then
  (cd "$tmp" && timeout 180 claude -p --model haiku --plugin-dir "$root/dist/qa" "/qa") >"$tmp/claude.txt" 2>&1 \
    || { cat "$tmp/claude.txt"; fail "claude run"; }
  grep -q "/qa:go-code" "$tmp/claude.txt" || { cat "$tmp/claude.txt"; fail "/qa did not print the index"; }
  (cd "$tmp" && timeout 180 claude -p --model haiku --plugin-dir "$root/dist/qa" \
    "List the subagent types available to you whose names start with qa. Reply with only the names, one per line.") \
    >"$tmp/agents.txt" 2>&1 || { cat "$tmp/agents.txt"; fail "claude agents run"; }
  grep -q "qa:worker" "$tmp/agents.txt" && grep -q "qa:adversary" "$tmp/agents.txt" \
    || { cat "$tmp/agents.txt"; fail "plugin agents not visible"; }
  pass "claude: /qa prints the stack; agents qa:worker and qa:adversary are loaded"
fi
rm -rf dist/qa
echo "all passed"
