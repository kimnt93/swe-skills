# Setup B: oh-my-pi (omp)

oh-my-pi is the coding agent. It can use several providers (OpenAI through a Codex login, Google
through Antigravity, Anthropic, ...), so one lane can run strong and cheap models from different
families.

## 1. Sign in to the providers you want

```bash
omp login                       # pick a provider; or name it:
omp login openai-codex          #   GPT models through your Codex/ChatGPT login
omp login anthropic             #   optional: Claude models through omp
# Gemini models come from the google-antigravity provider: log in to it the way `omp login` offers
omp models ls                   # the exact ids: <provider>/<model>
gh auth login
```

## 2. Install the plugin

```bash
make omp                        # PLUGIN_NAME=acme make omp for another name
omp plugin list                 # swe@swe-skills
```

In omp, skills are `/skill:swe <task>` for the router and `/skill:<skill>` for the rest (for example
`/skill:go-code`, `/skill:interrogate`).

## 3. Use it by hand

```text
cd ~/code/orders && omp
/skill:swe add an endpoint to cancel an open order
```

Useful flags: `--model <provider/id>`, `--thinking low|medium|high`, `-p` (print mode),
`--max-time 45m`, `--approval-mode yolo` (only in a disposable worktree).
The model roles omp uses for its own subagents (`default`, `smol`, `slow`) are written by
`fleet models apply` from `omp_roles` in `fleet/models.yaml`.

## 4. Run it unattended as a lane (Hermes)

A lane runs `omp -p --model <id> --thinking <level> --approval-mode yolo --max-time 45m` in a
worktree for each card.

```bash
export FLEET_MODELS=fleet/examples/models.omp-only.yaml    # one lane: omp
fleet models check          # every id must exist in `omp models ls`; fix models.yaml if not
fleet bootstrap
fleet project add orders --repo ~/code/orders --github acme/orders --description "Orders API"
```

Tiers in the default file:

| Tier | Model | Use |
|---|---|---|
| `top` | `openai-codex/gpt-6-sol`, thinking high | money-path, hard design, the reviewer |
| `mid` | `openai-codex/gpt-6-sol`, thinking medium | most cards |
| `low` | `google-antigravity/gemini-3.8-flash`, thinking low | mechanical cards, docs, scouting |

**The reviewer's family:** with one lane, the reviewer is the same lane at tier `top`. Make it a
different model from the one that wrote the card: write `mid` and `low` cards with Gemini or GPT
and review with the other, by editing `workers.omp` in `models.yaml` (for example `mid` on
`google-antigravity/gemini-3.8-flash` high and `top` on `openai-codex/gpt-6-sol`). Run `fleet models
show` to see the result.

## 5. Context limit

Nothing per model: log in and use the model. omp compacts at one global threshold,
`compaction.thresholdTokens`, set to 245000 (the default policy, the same as Codex):

```bash
fleet context apply      # writes compaction.thresholdTokens into ~/.omp/agent/config.yml (backup kept)
omp config get compaction.thresholdTokens
```

Change it under `context.default` in `fleet/models.yaml`. Details: [context-and-sync.md](context-and-sync.md).

## 6. Plugin skills for omp's own agents

omp's subagents (`scout`, `task`, ...) use the model roles above. The plugin's Claude Code
subagents (`swe:worker`, `swe:adversary`) do not exist in omp: for an adversarial review use
`/skill:interrogate`, which starts subagents on omp's roles.

## Pitfalls

- `omp models ls` lists only providers you are logged in to; a missing id is a login problem first.
- `--approval-mode yolo` skips approvals: only inside a worktree created for a card.
- After `make omp` start a new omp session; `omp plugin list` confirms the version.
