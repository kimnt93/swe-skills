#!/usr/bin/env bash
# selftest: prove the simplified swe-cli command without touching live environment.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
cli="$here/bin/main"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

# 1. Plugin name
[ "$("$cli" name)" = "swe" ] || fail "name"
pass "cli: name outputs plugin name"

# 2. Playbooks listing
out="$("$cli" playbooks)"
grep -q "playbook-plan" <<<"$out" || fail "playbooks list missing playbook-plan"
for name in quick complete review ship; do
  grep -q "/swe:playbook-$name" <<<"$out" || fail "playbooks list missing /swe:playbook-$name"
done
! grep -qE "/swe:playbook( |$)" <<<"$out" || fail "playbooks list still shows the removed dispatcher"
! grep -q "playbook-deliver" <<<"$out" || fail "playbooks list still shows the removed playbook-deliver"
pass "cli: playbooks lists the five pipelines and their slash commands"

# 3. Config management
cfg_file="$tmp/test_config.json"
"$cli" config init "$cfg_file" >/dev/null || fail "config init"
[ -f "$cfg_file" ] || fail "config init did not create file"
grep -q "default_agent" "$cfg_file" || fail "config init contents invalid"

export SWE_CONFIG="$cfg_file"
[ "$("$cli" config path)" = "$cfg_file" ] || fail "config path resolution with SWE_CONFIG"
"$cli" config show | grep -q "default_agent" || fail "config show"
pass "cli: config show, path, and init work with config.json"

# 4. Models and agents
"$cli" models show | grep -q "developer-senior" || fail "models show"
"$cli" models set developer-senior --model custom-model-v1 >/dev/null || fail "models set"
grep -q "custom-model-v1" "$cfg_file" || fail "models set did not persist to config.json"
[ "$("$cli" models subagent worker)" = "custom-model-v1" ] || fail "models subagent worker"
[ "$("$cli" models subagent adversary)" = "claude-sonnet-5-5" ] || fail "models subagent adversary"
pass "cli: models show, set, and subagent resolve and persist"

# 5. Doctor health check
"$cli" doctor >"$tmp/doctor.txt" || fail "doctor"
grep -q "Doctor Health Check" "$tmp/doctor.txt" || fail "doctor output format"
pass "cli: doctor executes environment and tool discovery"

# 6. Delegate command
"$cli" delegate --self-test >/dev/null || fail "delegate --self-test"
plan="$("$cli" delegate --agent codex --dry-run)"
grep -q '"agent": "codex"' <<<"$plan" || fail "delegate dry-run"
pass "cli: delegate self-test and dry-run execution plan"

# 7. Update command dry-run
up="$("$cli" update --dry-run)"
grep -q "Updating" <<<"$up" && grep -q "Would execute" <<<"$up" || fail "update dry-run"
pass "cli: update --dry-run previews build and install"

# 8. Changelog command
"$cli" changelog show | grep -q "Changelog" || fail "changelog show"
pass "cli: changelog commands work"

echo "all passed"
