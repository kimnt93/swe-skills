# 08 — fleet-live

status: human (logins, gateway restart, merging the first PRs) · needs: 07

## Goal

Hermes Kanban runs real cards on the pilot repo: card → lane → `make verify` → cross-family review
→ PR → human merge. One card, then 3, then about 10 in parallel.

## Steps

1. `bash fleet/tests/selftest.sh --hermes` passes. `ln -sf "$PWD"/fleet/bin/fleet ~/.local/bin/fleet`.
2. **Human logins** (interactive): `omp login openai-codex`, `hermes auth add anthropic`,
   `hermes auth add gemini` (or point the cheap brains at another provider in `fleet/models.yaml`).
3. Pick exact ids with `hermes model` and `omp models ls`; edit `fleet/models.yaml`; then
   `fleet models check` reports only missing profiles.
4. `fleet bootstrap` (root, lanes, board settings).
5. **Add the pilot project:** `fleet project add <name> --repo <clone> --github <owner>/<repo> --description "..."`
   (the manager `pm-<name>`, the board `<name>`, the Hermes project), then `fleet models check` = 0 problems,
   and the human runs `hermes gateway restart`. Ask `pm-<name>` to adopt the repo (the `project` skill:
   `setup_repo.sh`, templates, `ARCHITECTURE.md`).
6. **One card:** a small `risk: low`, `tier: mid` card on lane `claude` (body per `fleet-manager`),
   created by the manager (issue first, then the card with `--skill fleet-worker --skill github`).
   Watch with `hermes kanban watch --board <name>`. Check `.fleet/evidence.json`, the PR, the omp
   review and its verdict SHA. **Human** merges.
7. Fix whatever broke, with a test in `fleet/tests/selftest.sh`, before the next step.
8. Three independent cards across both lanes, then about ten; then one rough goal given to the root profile, routed to the manager and split by it.

## Verify

```bash
fleet models check                                   # 0 problem(s)
hermes kanban diagnostics --board <name>            # no errors, nothing stranded
gh pr list --state merged --repo <owner>/<repo>       # merged lane PRs
```

## Done when

20 cards merged with 0 reverts, and at least one review returned `request_changes` with a proven
finding that was then fixed.

## Log
