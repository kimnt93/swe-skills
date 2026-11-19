---
name: orca-cli
description: "Operate Orca-managed worktrees, terminals, automations, and embedded browser through the orca CLI. Use for managing isolated agent sessions, keystroke injection, idle-wait detection, and taking web preview screenshots."
metadata:
  group: platform
  summary: "Operate Orca worktrees, terminals, automations, and embedded browser via orca CLI"
---

# Orca CLI

This skill provides instructions for controlling the Orca Agent Development Environment through the `orca` CLI.

## 1. Resolve the CLI Executable

Choose the executable once and reuse it for later commands:

- If `ORCA_CLI_COMMAND` environment variable is set, use its value.
- Otherwise, in a dev checkout whose session exposes `ORCA_DEV_REPO_ROOT`, use `orca-dev`.
- Otherwise, on Linux outside an Orca-managed terminal, use `orca-ide` (avoids resolving to the system screen reader).
- Otherwise, use `orca`.

*(Below, `ORCA` refers to the executable resolved above)*.

---

## 2. Core Capabilities

- **Worktree Management**: Create, switch, list, and delete isolated Git worktrees for concurrent agent turns. See the [Worktree Reference](references/worktrees.md).
- **Terminal Management**: Spawn interactive PTY terminals, send keystrokes, wait for idle with `--for tui-idle`, and read scrollbacks. See the [Terminal Reference](references/terminals.md).
- **Embedded Browser**: Open dev servers, render web applications, and capture screenshots. See the [Browser Reference](references/browser.md).

---

## 3. Quick Reference

```bash
# Check status
ORCA status --json

# Create isolated task worktree
ORCA worktree create --repo id:<repoId> --name feature-branch --json

# Launch agent in worktree
ORCA terminal create --worktree active --command "codex" --json

# Send brief and wait for idle
ORCA terminal send --worktree active --text "$BRIEF" --enter --json
ORCA terminal wait --for tui-idle --timeout-ms 300000 --json
ORCA terminal read --worktree active --lines 200 --json
```
