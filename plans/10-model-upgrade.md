# 10 — model-upgrade

status: runbook · human: only when the managers' model changes

## When

A new model ships (say Opus 6), a model is retired, or a lane's cost or quality changes.

## Steps

1. `claude update`: the claude lane's `opus` / `sonnet` / `haiku` aliases now mean the newest
   models, unless `fleet/models.yaml` pins full ids.
2. Edit `fleet/models.yaml` where needed: pinned worker ids, the omp lane, the board and lane
   brains, `omp_roles`, the subagents' tiers.
3. `fleet models check`: 0 problems (each id exists where it runs, each provider is logged in).
4. `fleet models apply`, then `fleet models show`.
5. `make claude omp hermes`, so the plugin's subagents get the new models.
6. For a change to the managers' model (`board.manager`), run the router's `eval` playbook first: 10 past goals
   through the old and the new model, card graphs scored blind. Switch only if the new one is not
   worse. **Human** approves.
7. Clear per-card overrides that pin the old model: `hermes kanban set-model <id> none`.
8. Commit `chore(fleet): <model> for <agents>` with the `show` output in the body.

Skills never change in an upgrade: they name tiers, not models.
