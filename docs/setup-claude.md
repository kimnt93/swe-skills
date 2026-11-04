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
  `subagents` in `cli/models.yaml`; rebuild with `make claude` after changing them.
- Switch the main session's model with `/model`. Use Opus for money-path or hard design work, Sonnet
  for most code, Haiku for mechanical edits.
- `claude update` moves the aliases `opus`, `sonnet`, `haiku` to the newest models; pin full ids in
  `models.yaml` when you want upgrades to be explicit.

## 4. Run it unattended (the orchestrator starts it in a worktree)

A project's orchestrator runs `swe-cli delegate start`, which starts `claude --model <tier model> --effort <effort>
--permission-mode bypassPermissions` interactively in a session (tmux or an Orca terminal) inside a git worktree for
each card, hands it the brief and reads the result ([delegation.md](delegation.md)). It uses the same subscription, so it shares your usage
limits with your interactive sessions.

```bash
claude auth login                                           # the CLI uses your Claude login
export SWE_MODELS=cli/examples/models.claude-only.yaml  # one CLI: claude
swe-cli models check
swe-cli project add orders --dir ~/work/orders --repo api=acme/orders-api --cli claude
swe-cli doctor orders
swe-cli orchestrate orders                                    # Claude Code as the orchestrator, in ~/work/orders
```

`cli/examples/models.claude-only.yaml` differs from the default file in three ways:

| Setting | Claude-only |
|---|---|
| clis | only `claude` |
| reviewers | the same CLI at tier `top`: a fresh Opus session sees only the diff and the card |
| omp roles, omp workers | removed |

**What you give up:** the second-family review. A reviewer from the same model family shares the
author's blind spots, so keep autopilot off (`autopilot.auto_merge: []`) and have a human read money-path
and `standard` PRs. Add `omp` (setup B) later to get the independent review.

## 5. Context limit

Claude models compact at 350k tokens (the 300 to 400k band), set once for every session:

```bash
swe-cli context apply      # adds "autoCompactWindow": 350000 to ~/.claude/settings.json (backup kept)
```

`swe-cli delegate` also sets `CLAUDE_CODE_AUTO_COMPACT_WINDOW=350000` for each card, and one-off
sessions can use `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000 claude`. Change the number under
`context.families.claude` in `cli/models.yaml`. Details: [context-and-sync.md](context-and-sync.md).

## 6. Protect your quota

- Keep about five sessions running at once; each is a full Claude Code session on the same subscription.
- Default cards to tier `mid`; reserve `top` for money-path, concurrency and designs.
- Put docs, lint and rename cards on tier `low`.
- When Claude Code reports a usage limit, `swe-cli delegate status` shows the stuck session. The manager runs on a
  non-Claude model, so it still answers: it tells you and asks whether to wait or restart the card with `--cli omp`.

## Pitfalls

- `bypassPermissions` is safe only because each card runs in its own worktree: never point a session at a
  checkout with uncommitted work. `swe-cli delegate` only uses worktrees it creates.
- The manager's model (Gemini) only routes; the code is written by the worker model in the table of `workers.claude`.
- The first time Claude Code opens a new folder it asks whether to trust it; `swe-cli delegate` pre-trusts the worktrees it creates.
- If `/swe` shows old skills after a rebuild, start a new session.
