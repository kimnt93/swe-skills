# Context limits

How long a session may grow before each agent compacts it.

One policy in the project's `models.yaml`, applied to every tool:

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
```

## What lands where

| Tool | Setting | Value | File |
|---|---|---|---|
| Claude Code | `autoCompactWindow` | 350000 | `~/.claude/settings.json` |
| Claude Code in a delegated session | env `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 350000 (set by `swe-cli delegate` and `swe-cli lane` for each card) | none: per card |
| Codex | `model_context_window`, `model_auto_compact_token_limit` | 272000, 245000 | `~/.codex/config.toml` (top level; tables and comments kept) |
| oh-my-pi | `compaction.thresholdTokens` | 245000 | `~/.omp/agent/config.yml` |

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

One run only, without touching any file: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000 claude`, or
`omp config set compaction.thresholdTokens 200000`.

## Notes

- **oh-my-pi** has one global threshold, so every model there compacts at the default 245k. That fits
  "log in and use the model": nothing else to configure per model. A Claude model used through omp
  compacts earlier than it would in Claude Code, which is the safe side.
- **Plugin subagents** (`swe:worker`, `swe:adversary`) inherit the session's setting; they run short.
- **To change a number**, edit `models.yaml` and run `swe-cli context apply`.
- **Not verified:** that Claude Code starts compacting exactly at 350000 for `autoCompactWindow:
  350000`. Claude Code accepts the setting and uses it as the compaction window (checked by running
  it with the setting), but a 350k-token session is too costly to run as a test. Watch one long
  session and move the number if it compacts earlier or later than you want.
