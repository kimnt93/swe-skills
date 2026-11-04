# Setup C: Codex CLI

Codex CLI is a coding agent on your ChatGPT login (OpenAI models). It can be a project's default coding CLI,
a reviewer, or the project's orchestrator.

## 1. Sign in

```bash
codex login                     # ChatGPT account (device authorization also works over SSH)
gh auth login
```

## 2. Install the plugin

```bash
make codex                      # PLUGIN_NAME=acme make codex for another name
```

In Codex the router is `$swe:swe <task>`; the other skills are `$swe:<skill>`.

## 3. Use it by hand

```text
cd ~/code/orders && codex
$swe:swe add an endpoint to cancel an open order
```

## 4. Run it in the fleet

```bash
export FLEET_MODELS=fleet/examples/models.codex-only.yaml    # one CLI: codex
fleet models check
fleet project add orders --dir ~/work/orders --repo api=acme/orders-api --cli codex
fleet doctor orders
fleet orchestrate orders                                     # Codex as the orchestrator, in ~/work/orders
```

`fleet delegate start` runs `codex --model <id> -c model_reasoning_effort=<effort> --ask-for-approval never
--sandbox danger-full-access` in a session inside a git worktree (the worktree is the sandbox boundary; do not
use this on a checkout you care about). It answers Codex's "trust this directory" dialog. Headless one-shots
(`fleet lane`) use `codex exec --dangerously-bypass-approvals-and-sandbox`.

| Tier | Model | Use |
|---|---|---|
| `top` | `gpt-6-sol`, effort high | money-path, hard design |
| `mid` | `gpt-6-sol`, effort medium | most cards |
| `low` | `gpt-6-sol`, effort low | mechanical cards, docs, scouting |

Put the model ids your login offers under `workers.codex` in `fleet/models.yaml`. The prompt and busy markers
(`clis.codex.ready` and `busy`) were taken from one Codex version; if `fleet delegate` reports that Codex never
showed its prompt, attach to the session, read what the prompt looks like and fix `ready`.

## 5. Context limit

Codex takes `model_context_window` and `model_auto_compact_token_limit` (272000 / 245000 by default):
`fleet context apply` writes them into `~/.codex/config.toml` (backup kept).
