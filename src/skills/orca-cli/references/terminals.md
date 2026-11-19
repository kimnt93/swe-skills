# Orca Terminal Management

Orca hosts interactive PTY terminals for each agent with granular control over input injection and state detection.

## Commands

### 1. Create a Terminal
Spawns a new terminal session in the targeted worktree:
```bash
ORCA terminal create --worktree active --command "<cmd>" --json
```

### 2. Send Input
Injects text into the active agent terminal:
```bash
ORCA terminal send --worktree active --text "<text>" [--enter] [--interrupt] --json
```
- `--enter`: Submits the input with a carriage return.
- `--interrupt`: Sends SIGINT (`Ctrl+C`) prior to input.

### 3. Wait for Idle (`--for tui-idle`)
Blocks until the terminal completes executing turns and returns to idle input:
```bash
ORCA terminal wait --for tui-idle --timeout-ms <milliseconds> --json
```

### 4. Read Terminal Scrollback
Fetches the last N lines of output from the terminal buffer:
```bash
ORCA terminal read --worktree active --lines 200 --json
```
