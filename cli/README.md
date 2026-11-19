# swe-cli (`<plugin>-cli`)

Developer automation CLI for AI coding agents and playbooks.

## Commands

```bash
swe-cli update [harness...] [--no-pull] [--dry-run]
                                      # git pull latest code, rebuild plugin, reinstall into harnesses
swe-cli playbooks                     # list all available playbooks and their slash commands
swe-cli delegate [options]            # delegate coding tasks via Orca sessions, T3 Code threads, or CLI relays
swe-cli config [show|path|init]       # inspect active config or initialize default config.json
swe-cli doctor                        # health check for agent CLIs, Orca, T3 Code, git, gh
swe-cli models show                   # inspect configured agents, CLIs, models, and reasoning
swe-cli models set <agent> [flags]    # update agent configuration in config.json
swe-cli name                          # print the plugin name (default: swe)
swe-cli changelog show                # inspect repository CHANGELOG.md
swe-cli changelog check <pr>          # check if PR has a changelog entry
```

## Configuration (`config.json`)

Configuration is managed in `config.json`, resolved in priority order:
1. Custom env var (`$SWE_CONFIG`)
2. Local directory (`./config.json`)
3. Installed plugin directory (`dist/swe/config.json`)
4. OS configuration directory (`~/.config/swe/config.json`)

Example `config.json`:

```json
{
  "default_agent": "codex",
  "delegation": {
    "engine": "auto",
    "timeout_ms": 300000,
    "yolo": true
  },
  "orca": {
    "enabled": true,
    "binary": "orca"
  },
  "t3": {
    "enabled": true,
    "binary": "t3"
  },
  "agents": {
    "developer-junior": {
      "cli": "codex",
      "model": "o3-mini",
      "reasoning": "medium"
    },
    "developer-senior": {
      "cli": "claude",
      "model": "claude-sonnet-5-5",
      "reasoning": "high"
    },
    "reviewer": {
      "cli": "claude",
      "model": "claude-sonnet-5-5",
      "reasoning": "high"
    },
    "documenter": {
      "cli": "omp",
      "model": "gemini-2.5-flash",
      "reasoning": "low"
    }
  }
}
```

## Delegation

The `swe-cli delegate` command (and `/swe:delegate` skill) dispatches implementation tasks using:
- **Orca CLI Sessions**: Isolated Git worktrees with interactive PTY terminals and idle detection (`--for tui-idle`).
- **T3 Code Threads**: Isolated thread execution via `t3 thread start --wait --json`.
- **Direct Headless Relays**: Non-interactive command invocation (`codex exec`, `claude -p`, `omp`, `pi -p`, etc.).
- **Review-First Verification**: Automatically runs test verification gates (`--verify`) and outputs `git diff --stat` before committing.
