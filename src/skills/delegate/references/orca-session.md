# Orca CLI Session Orchestration Reference

This guide details how to orchestrate multi-agent tasks inside Orca (the Agent Development Environment desktop application) via its command-line interface.

Orca provides two superpowers for agent orchestration:
1. **Isolated Git Worktrees**: Every agent can work on a separate branch in an isolated folder, preventing collision with the main working tree.
2. **Interactive PTY Terminals**: Live terminal sessions with keystroke emulation, idle-state detection (`--for tui-idle`), and scrollback reading.

---

## 1. Resolving the Executable

Never hardcode bare `orca` on Linux outside an active Orca-managed terminal, as `/usr/bin/orca` maps to GNOME's screen reader and will trigger speech synthesis.

Use this resolution logic:
```bash
if [ -n "$ORCA_CLI_COMMAND" ]; then
  ORCA="$ORCA_CLI_COMMAND"
elif [ -n "$ORCA_DEV_REPO_ROOT" ]; then
  ORCA="orca-dev"
elif [ -x "$HOME/.local/bin/orca-ide" ]; then
  ORCA="$HOME/.local/bin/orca-ide"
elif [ "$TERM_PROGRAM" = "Orca" ] || [ -n "$ORCA_AGENT_PANE" ]; then
  ORCA="orca"
else
  ORCA="orca-ide"
fi
```

Verify that Orca is running:
```bash
$ORCA status --json
```

---

## 2. Managing Worktrees

Create an isolated worktree for a delegated task:
```bash
# List existing worktrees
$ORCA worktree list --json

# Create a dedicated worktree for a task
$ORCA worktree create --repo id:<repoId> --name delegate-codex-task --json
```

The output returns the worktree ID and local directory path:
```json
{
  "worktreeId": "wt_98fbc123-4567-89ab-cdef",
  "path": "/home/user/workspaces/app/delegate-codex-task",
  "branch": "delegate-codex-task"
}
```

---

## 3. Terminal Lifecycle & Dispatching

### Step 1: Create or Target a Terminal
Spawn the agent CLI inside the active or newly created worktree:
```bash
$ORCA terminal create --worktree active --command "codex" --json
```
This returns a terminal handle (e.g. `term_3108a5c7-...`).

### Step 2: Dispatch the Brief
Inject the self-contained brief into the terminal:
```bash
$ORCA terminal send --worktree active --text "$BRIEF" --enter --json
```

Flags:
- `--enter`: Appends a carriage return / newline to submit the prompt.
- `--interrupt`: Sends `Ctrl+C` before sending text if previous command is stuck.

### Step 3: Wait for Completion (`tui-idle`)
Instead of guessing sleep timers, Orca provides native PTY state detection:
```bash
$ORCA terminal wait --for tui-idle --timeout-ms 300000 --json
```
- `--for tui-idle`: Blocks until the interactive CLI agent finishes its turn, stops emitting tokens/tool calls, and returns to the idle input prompt.
- `--timeout-ms`: Maximum duration to wait before returning a timeout status.

### Step 4: Read Output Buffer
Read recent terminal lines to inspect output or error messages:
```bash
$ORCA terminal read --worktree active --lines 200 --json
```

---

## 4. Worktree Review & Cleanup

After the agent finishes:
1. Change directory to the worktree path:
   ```bash
   cd "$WORKTREE_PATH"
   git status --short
   git diff
   ```
2. Run project tests:
   ```bash
   make verify
   ```
3. Hand back to the user or orchestrator:
   - If accepted: merge the worktree branch into main.
   - If completed: delete the worktree:
     ```bash
     $ORCA worktree delete --worktree <worktreeId> --json
     ```
