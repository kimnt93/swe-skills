# Setup A: Claude Code on your Claude subscription

Claude Code is the coding agent, signed in with your Claude subscription (Pro or Max), no API key.
The plugin adds `/swe`, the skills, and two subagents.

## 1. Sign in

```bash
claude auth login           # choose the Claude account (subscription) option
claude auth status --text   # shows the account and plan
gh auth login               # agents push and open PRs as this GitHub user
```

## 2. Install the plugin

```bash
make claude                 # user scope; PLUGIN_NAME=acme make claude for another name
claude plugin list          # swe@swe-skills, enabled
```

For one project only: `make claude SCOPE=project PROJECT_DIR=~/code/orders` (committed with the repo).
Without installing: `claude --plugin-dir dist/swe`.

## 3. Use it by hand (the recommended start)

```text
cd ~/code/orders && claude
/swe add an endpoint to cancel an open order
```

- The router picks the model tier for subagents: `swe:worker` runs on Sonnet (tier `mid`),
  `swe:adversary` (the reviewer in `/swe:interrogate`) on Opus (tier `top`). Both come from
  `subagents` in `fleet/models.yaml`; rebuild with `make claude` after changing them.
- Switch the main session's model with `/model`. Use Opus for money-path or hard design work, Sonnet
  for most code, Haiku for mechanical edits.
- `claude update` moves the aliases `opus`, `sonnet`, `haiku` to the newest models; pin full ids in
  `models.yaml` when you want upgrades to be explicit.

## 4. Run it unattended as a lane (Hermes)

A lane runs `claude -p --model <tier model> --effort <effort> --permission-mode bypassPermissions`
in a git worktree for each card. It uses the same subscription, so it shares your usage limits with
your interactive sessions.

```bash
hermes auth add anthropic                                   # project managers use your Claude login
export FLEET_MODELS=fleet/examples/models.claude-only.yaml  # one lane: claude, all brains on Claude
fleet models check && fleet bootstrap
fleet project add orders --repo ~/code/orders --github acme/orders --description "Orders API"
```

`fleet/examples/models.claude-only.yaml` differs from the default two-lane file in four ways:

| Setting | Claude-only |
|---|---|
| lanes | only `claude` |
| root brain | Claude Haiku (no Gemini login needed) |
| reviewers | the same lane at tier `top`: a fresh Opus session sees only the diff and the card |
| omp roles, omp workers | removed |

**What you give up:** the second-family review. A reviewer from the same model family shares the
author's blind spots, so keep autopilot off (`autopilot.auto_merge: []`) and have a human read money-path
and `standard` PRs. Add the `omp` lane (setup B) later to get the independent review.

## 5. Context limit

Claude models compact at 350k tokens (the 300 to 400k band), set once for every session:

```bash
fleet context apply      # adds "autoCompactWindow": 350000 to ~/.claude/settings.json (backup kept)
```

A fleet lane also exports `CLAUDE_CODE_AUTO_COMPACT_WINDOW=350000` for each card, and one-off
sessions can use `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000 claude`. Change the number under
`context.families.claude` in `fleet/models.yaml`. Details: [context-and-sync.md](context-and-sync.md).

## 6. Protect your quota

- Keep `kanban.max_in_progress_per_profile` at 2 (the default) or lower; each running card is a full
  Claude Code session.
- Default cards to tier `mid`; reserve `top` for money-path, concurrency and designs.
- Put docs, lint and rename cards on tier `low`.
- When Claude Code reports a usage limit, the card fails and the dispatcher retries after a
  cooldown (`respawn_guarded`); `hermes kanban diagnostics --board <project>` shows it. Lower
  concurrency instead of raising retries.

## Pitfalls

- `bypassPermissions` is safe only because each card runs in its own worktree: never point a lane at a
  checkout with uncommitted work.
- The brain model of a lane (Haiku here) only runs `fleet lane` and copies evidence; the code is
  written by the worker model in the table of `workers.claude`.
- If `/swe` shows old skills after a rebuild, start a new session.
