# Context limits and login sync

Two things this page sets up: how long a session may grow before each agent compacts it, and how a
single login on the Hermes `default` profile reaches every other profile.

## 1. Context limits

One policy in `cli/models.yaml`, applied to every tool:

```yaml
context:
  default: {window: 272000, compact_at: 245000}   # Codex, Gemini, GPT, and anything not listed
  families:
    claude: {window: 400000, compact_at: 350000}  # opus, sonnet, haiku, fable, claude-* ids
  models: {}                                      # exact overrides: "<model id>": {window: N, compact_at: N}
```

| Field | Meaning |
|---|---|
| `window` | the most tokens a session may hold (the cap we allow) |
| `compact_at` | where the agent starts compacting: the summary replaces the older turns |
| `families.claude` | Claude models: 300 to 400k, compacting at 350k |
| `default` | every other model: the price step you described, about 272k, compacting at 245k |
| `models` | one model that needs its own numbers, for example `gemini-3.8-flash: {window: 200000, compact_at: 150000}` |

```bash
swe-cli context show          # what each tool will get
swe-cli context apply         # write Claude Code, Codex and oh-my-pi (each file is backed up first)
swe-cli sync                  # write the Hermes profiles (also part of swe-cli bootstrap)
```

### What lands where

| Tool | Setting | Value | File |
|---|---|---|---|
| Claude Code | `autoCompactWindow` | 350000 | `~/.claude/settings.json` |
| Claude Code in a delegated session | env `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 350000 (set by `swe-cli delegate` and `swe-cli lane` for each card) | none: per card |
| Codex | `model_context_window`, `model_auto_compact_token_limit` | 272000, 245000 | `~/.codex/config.toml` (top level; tables and comments kept) |
| oh-my-pi | `compaction.thresholdTokens` | 245000 | `~/.omp/agent/config.yml` |
| Hermes, each profile | `model.context_length`, `compression.threshold_tokens`, `compression.threshold` | by the profile's model: 400000 / 350000 / 0.88 for Claude, 272000 / 245000 / 0.91 for the rest | `<profile>/config.yaml` |

Examples of what the files look like afterwards:

```json
// ~/.claude/settings.json (one added key; everything else untouched)
{ "autoCompactWindow": 350000 }
```

```toml
# ~/.codex/config.toml
model_context_window = 272000
model_auto_compact_token_limit = 245000
```

```yaml
# ~/.omp/agent/config.yml
compaction:
  thresholdTokens: 245000
```

```yaml
# ~/.hermes/profiles/pm-orders/config.yaml (a Sonnet manager)
model:
  context_length: 400000
compression:
  threshold_tokens: 350000
  threshold: 0.88
```

One run only, without touching any file: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000 claude`, or
`omp config set compaction.thresholdTokens 200000`.

### Notes

- **Hermes ratio.** Hermes compacts at the lower of `threshold` times the window and
  `threshold_tokens`, and raises any ratio under 0.75 for windows below 512k. So `fleet` sets the
  ratio to `compact_at / window`, rounded up (0.88 and 0.91), and lets `threshold_tokens` decide.
- **oh-my-pi** has one global threshold, so every model there compacts at the default 245k. That fits
  "log in and use the model": nothing else to configure per model. A Claude model used through omp
  compacts earlier than it would in Claude Code, which is the safe side.
- **Plugin subagents** (`swe:worker`, `swe:adversary`) inherit the session's setting; they run short.
- **To change a number**, edit `cli/models.yaml` and run `swe-cli context apply && swe-cli sync`.
- **Not verified:** that Claude Code starts compacting exactly at 350000 for `autoCompactWindow:
  350000`. Claude Code accepts the setting and uses it as the compaction window (checked by running
  it with the setting), but a 350k-token session is too costly to run as a test. Watch one long
  session and move the number if it compacts earlier or later than you want.

## 2. Log in once, sync to every profile

Hermes profiles are separate homes. What is shared and what is not:

| Item | Shared with the profiles? | What `swe-cli sync` does |
|---|---|---|
| OAuth logins (Claude Pro or Max, OpenAI Codex, xAI) and logins saved by `hermes auth add` | **Yes, automatically.** Every profile reads the default profile's `auth.json` as a fallback, per provider | nothing to copy (copying an OAuth token would break it: refresh tokens are single use). It checks the login and warns when a profile has its own login that hides the default's |
| API keys in `.env` (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, any `*_API_KEY`, `*_BASE_URL`) | **No**, each profile has its own `.env` | copies them from the default's `.env` into each profile's `.env` (mode 600) |
| Messaging tokens (`TELEGRAM_*`, `DISCORD_*`, `SLACK_*`, `WHATSAPP_*`, ...) | never | never copied: one bot belongs to one gateway |
| models, context limits, skills directories | no | applied from `cli/models.yaml` to every profile |

### The routine

```text
1. hermes auth add anthropic        # on the default profile; or add the key to ~/.hermes/.env
2. hermes                            # open Hermes on the default profile
3. /sync                             # one slash command
```

Reply, for example:

```text
login: anthropic logged in; gemini logged in
default: already in sync
pm-orders: env +GEMINI_API_KEY; 3 setting(s): model.context_length, compression.threshold, compression.threshold_tokens
claude: already in sync
omp: already in sync
done in 3.8s
```

`/sync` is a Hermes quick command (`quick_commands.sync` in the default profile's `config.yaml`,
`type: exec`). It runs `swe-cli sync` on the host with no model call, works in the CLI and in every chat
gateway, and finishes in about a second when nothing changed. Hermes ends a quick command after 30
seconds and redacts secrets in its output. `swe-cli bootstrap` installs it; or by hand:

```bash
hermes config set quick_commands.sync.type exec
hermes config set quick_commands.sync.command "python3 /path/to/swe-skills/cli/bin/main sync"
```

Outside Hermes: `swe-cli sync` (and `swe-cli sync --dry-run` to see what would change). Run it after
`hermes auth add`, after changing `cli/models.yaml`, after `swe-cli project add`, and after rotating
an API key.

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `login: anthropic not logged in on default` | log in on the default profile: `hermes auth add anthropic` |
| `warning: omp has its own gemini login` | that profile ignores the default's login; list its entries with `hermes -p omp auth list`, then `hermes -p omp auth remove gemini <id>` |
| `/sync` answers "unknown command" in a one-shot call | one-shot modes (`hermes -z`, `hermes chat -q`) send the text to the model; use the interactive CLI or a chat gateway |
| `pm-x: missing, run: swe-cli bootstrap` | the profile does not exist yet: `swe-cli bootstrap` or `swe-cli project add` |
| `/sync` times out | something is very slow (a hung `hermes` call); run `swe-cli sync` in a shell to see where |
