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
for name in build plan quick solo refactor-plan review ship test security; do
  grep -q "/swe:playbook-$name" <<<"$out" || fail "playbooks list missing /swe:playbook-$name"
done
[ "$(grep -c '| /swe:playbook-' <<<"$out")" = 9 ] || fail "playbooks list must show exactly nine pipelines"
grep -q "^playbook-build .*DEFAULT" <<<"$out" || fail "playbooks list must mark playbook-build as the default"
grep -q "^playbook-quick .*Only when named" <<<"$out" || fail "playbooks list must say quick runs only when named"
! grep -qE "/swe:playbook( |$)" <<<"$out" || fail "playbooks list still shows the removed dispatcher"
! grep -q "playbook-deliver" <<<"$out" || fail "playbooks list still shows the removed playbook-deliver"
! grep -q "playbook-complete" <<<"$out" || fail "playbooks list still shows the removed playbook-complete"
grep -q "^playbook-solo .*Only when named" <<<"$out" || fail "playbooks list must say solo runs only when named"
grep -q "^playbook-solo .*no review" <<<"$out" || fail "playbooks list must say solo has no review"
grep -q "^playbook-test .*fixes nothing" <<<"$out" || fail "playbooks list must say the test pipeline fixes nothing"
grep -q "^playbook-quick .*no review" <<<"$out" || fail "playbooks list must say quick has no review"
grep -q "^playbook-security .*changes nothing" <<<"$out" || fail "playbooks list must say the security audit changes nothing"
pass "cli: playbooks lists the nine pipelines, build as the default, quick and solo only when named"

# 3. Config management
cfg_file="$tmp/test_config.json"
"$cli" config init "$cfg_file" >/dev/null || fail "config init"
[ -f "$cfg_file" ] || fail "config init did not create file"
grep -q '"agent_table"' "$cfg_file" || fail "config init contents invalid"
! "$cli" config init "$cfg_file" >/dev/null 2>&1 || fail "config init overwrote an existing file"

export SWE_CONFIG="$cfg_file"
[ "$("$cli" config path)" = "$cfg_file" ] || fail "config path resolution with SWE_CONFIG"
"$cli" config show | grep -q "agent_table" || fail "config show"
pass "cli: config show, path, and init work with config.json"

# 4. The agent table: no table stops, a filled row answers, there is no models command
unset AGENT_TABLE
export XDG_CONFIG_HOME="$tmp/xdg"
! "$cli" agents row medium >/dev/null 2>"$tmp/stop.txt" || fail "agents row without a table"
grep -q "^STOP" "$tmp/stop.txt" || fail "agents row must say STOP"
"$cli" agents init "$tmp/table.md" >/dev/null || fail "agents init"
! "$cli" agents check --table "$tmp/table.md" >/dev/null 2>&1 || fail "an unfilled table must stop"
sed -i -e 's/<harness>/harness-a/' -e 's/<model>/model-a/' -e 's/<effort>/high/' "$tmp/table.md"
"$cli" agents check --table "$tmp/table.md" >/dev/null || fail "a filled table"
"$cli" agents row medium --table "$tmp/table.md" | grep -qx "Run on: harness harness-a, model model-a, reasoning effort high" \
  || fail "agents row"
! "$cli" models show >/dev/null 2>&1 || fail "the removed models command still answers"
pass "cli: agents reads only the team's table and stops without it"

# 5. Doctor health check
"$cli" doctor >"$tmp/doctor.txt" || fail "doctor"
grep -q "Doctor Health Check" "$tmp/doctor.txt" || fail "doctor output format"
pass "cli: doctor executes environment and tool discovery"

# 6. Delegate command
"$cli" delegate --self-test >/dev/null || fail "delegate --self-test"
printf 'Row: medium\nbuild it\n' >"$tmp/brief.md"
printf '#!/bin/sh\nexit 99\n' >"$tmp/orca-shim" && chmod +x "$tmp/orca-shim"  # a dry run starts nothing
plan="$(ORCA_CLI_COMMAND="$tmp/orca-shim" "$cli" delegate --brief "$tmp/brief.md" --table "$tmp/table.md" --dry-run)"
grep -q "orchestration worker-start .*--agent harness-a --model model-a --effort high" <<<"$plan" || fail "delegate dry-run"
! ORCA_CLI_COMMAND="$tmp/orca-shim" "$cli" delegate --brief "$tmp/brief.md" --table "$tmp/none.md" --dry-run >/dev/null 2>&1 \
  || fail "delegate ran without a table"
pass "cli: delegate starts one Orca worker from the table's row, and nothing without a table"

# 7. Update command dry-run
up="$("$cli" update --dry-run)"
grep -q "Updating" <<<"$up" && grep -q "Would execute" <<<"$up" || fail "update dry-run"
pass "cli: update --dry-run previews build and install"

# 8. Changelog command
"$cli" changelog show | grep -q "Changelog" || fail "changelog show"
pass "cli: changelog commands work"

echo "all passed"
