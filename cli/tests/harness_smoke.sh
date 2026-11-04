#!/usr/bin/env bash
# harness_smoke: run each real harness once (claude, codex, omp, opencode) through the commands swe-cli builds.
# Needs the CLIs installed and logged in, and costs a few tokens, so it is NOT part of `make test`.
#   bash cli/tests/harness_smoke.sh [claude codex omp opencode]
# Per harness: (1) the headless command answers "pong"; (2) an interactive tmux session started by `swe-cli delegate`
# shows its prompt and receives the brief. A harness that is not installed or not logged in is reported, not failed.
set -uo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
main="$here/bin/main"; delegate="$here/bin/delegate"
command -v tmux >/dev/null || { echo "SKIP: tmux is not installed"; exit 0; }
tmp="$(mktemp -d)"; trap 'tmux ls 2>/dev/null | cut -d: -f1 | grep "^smoke-" | xargs -r -n1 tmux kill-session -t; rm -rf "$tmp"' EXIT
want=("$@"); [ ${#want[@]} -gt 0 ] || want=(claude codex omp opencode)
cat >"$tmp/config.yaml" <<'YAML'
manager: smoke-claude
launcher: tmux
clis:
  claude: {permission_mode: bypassPermissions, model: haiku, ready: "❯", busy: "esc to interrupt"}
  codex: {approval_policy: never, sandbox: danger-full-access, model: gpt-6-luna, ready: "›", busy: "esc to interrupt"}
  omp: {approval_mode: yolo, model: google-antigravity/gemini-3.8-flash, ready: "π >", busy: "⎋"}
  opencode: {model: opencode/big-pickle, ready: "ctrl+p commands", settle: 3, busy: "esc interrupt"}
agents:
  smoke-claude: {cli: claude, model: haiku, reasoning: low}
  smoke-codex: {cli: codex, model: gpt-6-luna, reasoning: low}
  smoke-omp: {cli: omp, model: google-antigravity/gemini-3.8-flash, reasoning: low}
  smoke-opencode: {cli: opencode, model: opencode/big-pickle}
reviewers: {claude: smoke-codex}
subagents: {}
omp_roles: {}
context: {default: {window: 272000, compact_at: 245000}, families: {claude: {window: 400000, compact_at: 350000}}, models: {}}
autopilot: {auto_merge: []}
YAML
mkdir -p "$tmp/proj" && git init -q --bare "$tmp/origin.git" && git clone -q "$tmp/origin.git" "$tmp/proj/app" 2>/dev/null
( cd "$tmp/proj/app" && git config user.email t@t && git config user.name t && git checkout -q -b main && echo hi >a.txt \
  && printf 'verify:\n\t@echo ok\n' >Makefile && git add . && git commit -qm init && git push -q origin main )
printf 'projects:\n  smoke:\n    dir: %s\n    repos:\n      app: {github: acme/app}\n' "$tmp/proj" >"$tmp/projects.yaml"
export SWE_MODELS="$tmp/config.yaml" SWE_PROJECTS="$tmp/projects.yaml" SWE_STATE="$tmp/state" SWE_READY_TIMEOUT=60
bad=0
for cli in "${want[@]}"; do
  command -v "$cli" >/dev/null || { echo "SKIP $cli: not installed"; continue; }
  agent="smoke-$cli"
  mapfile -t cmd < <(python3 "$main" models cmd "$agent")
  while IFS= read -r kv; do [ -n "$kv" ] && export "$kv"; done < <(python3 "$main" context env "$agent")
  answer="$(cd "$tmp" && timeout 150 "${cmd[@]}" "Reply with exactly the word: pong" </dev/null 2>&1 | tail -3)"
  if grep -qi pong <<<"$answer"; then echo "PASS $cli headless: ${cmd[*]}"; else echo "WARN $cli headless gave no pong (login or network?): $(tr '\n' ' ' <<<"$answer" | cut -c1-200)"; fi
  if python3 "$delegate" start smoke "$agent" --files "$agent.txt" --goal "Reply with the word ready." --branch "chore/$agent" --agent "$agent" >/dev/null 2>"$tmp/$cli.err"; then
    sleep 12
    if tmux capture-pane -p -t "smoke-$agent" -S -80 | grep -q "Read .swe/brief.md"; then echo "PASS $cli interactive: prompt shown, brief received"
    else echo "FAIL $cli interactive: the brief never reached the session"; bad=1; fi
  else echo "FAIL $cli interactive: $(cat "$tmp/$cli.err")"; bad=1; fi
done
exit $bad
