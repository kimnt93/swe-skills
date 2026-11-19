# Direct Headless CLI Relay Reference

When running outside an Orca or T3 desktop environment, tasks can be dispatched directly to implementer CLIs in non-interactive/headless mode.

---

## Agent CLI Matrix

| Agent | CLI Binary | Headless Execution Command | Notes |
| :--- | :--- | :--- | :--- |
| **OpenAI Codex** | `codex` | `codex exec "$BRIEF"` | Non-interactive execution; edits workspace files directly. |
| **Claude Code** | `claude` | `claude -p "$BRIEF"` | Runs in print/headless mode with specified prompt. |
| **Oh My Pi** | `omp` | `omp --prompt "$BRIEF"` | Executes prompt in headless mode. |
| **Pi Agent** | `pi` | `pi -p "$BRIEF"` | Headless CLI agent for fast edits and refactors. |
| **Antigravity** | `agy` | `agy -p "$BRIEF"` | Non-interactive execution mode for Antigravity tasks. |
| **OpenCode** | `opencode` | `opencode exec "$BRIEF"` | Executes command non-interactively in workspace. |
| **Devin CLI** | `devin` | `devin run "$BRIEF"` | Dispatches task to Devin background worker. |
| **Aider** | `aider` | `aider --message "$BRIEF" --no-git` | `--no-git` prevents Aider from committing automatically. |
| **Cursor Agent** | `cursor-agent`| `cursor-agent "$BRIEF"` | Cursor headless agent runner. |
| **Cline CLI** | `cline` | `cline -p "$BRIEF"` | Cline CLI headless execution. |

---

## Guardrails for Direct Headless Relays

1. **Working Tree Isolation**:
   Create a temporary Git branch before headless execution:
   ```bash
   git checkout -b delegate-tmp-<agent>-<task>
   ```
2. **Review-First Enforcement**:
   - For tools with auto-commit flags, always pass `--no-git` or similar flags.
   - Never allow the runner to invoke `git push` or commit autonomously.
3. **Execution Timeouts**:
   Wrap direct execution with timeouts (default 300 seconds) to prevent hangs when an agent waits on interactive user input.
