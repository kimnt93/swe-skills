# T3 Code Thread Delegation Reference

This guide details how to orchestrate multi-agent tasks inside **T3 Code** via its command-line interface `t3`.

T3 Code provides local agent workspaces, thread execution, and Git worktree isolation for concurrent agent tasks.

---

## 1. Resolving the Executable

T3 Code installs its CLI shim to `~/.t3/bin/t3` or system PATH `/usr/bin/t3code`:
```bash
if command -v t3 >/dev/null 2>&1; then
  T3="t3"
elif [ -x "$HOME/.t3/bin/t3" ]; then
  T3="$HOME/.t3/bin/t3"
elif command -v t3code >/dev/null 2>&1; then
  T3="t3code"
else
  echo "T3 Code is not installed"
fi
```

Verify service status:
```bash
$T3 status
```

---

## 2. Dispatching Tasks via Threads

### One-Shot Synchronous Execution
Dispatch a task with a self-contained brief, wait for completion, and capture output in JSON:
```bash
$T3 thread start \
  --worktree delegate-task-branch \
  --model claude-3-7-sonnet \
  --wait \
  --json \
  . \
  "$BRIEF"
```

Arguments & Flags:
- `.` (project): Target directory or project path.
- `message`: Task brief or prompt (can be `-` to read from stdin).
- `--worktree <branch>`: Runs the agent in an isolated Git worktree on the specified branch instead of modifying active files directly.
- `--model <slug>`: Specific model to run the thread with.
- `--provider <id>`: Provider instance identifier.
- `--wait`: Blocks until the agent finishes its turn, exiting 0 on success.
- `--json`: Formats output as structured JSON.

---

## 3. Asynchronous Thread Control

For long-running tasks, orchestrate threads incrementally:

### Step 1: Start Thread
```bash
THREAD_ID=$($T3 thread start --title "Feature Task" . "$BRIEF")
```

### Step 2: Check Thread State
```bash
$T3 thread show "$THREAD_ID"
```

### Step 3: Send Additional Instructions
```bash
$T3 thread send "$THREAD_ID" "Run test verification and report results"
```

---

## 4. Inspection & Verification Gate

After thread execution completes:
1. Inspect modified files in the worktree:
   ```bash
   git status --short
   git diff --stat
   ```
2. Run project verification command:
   ```bash
   make verify
   ```
3. Return results following the review-first philosophy before landing.
