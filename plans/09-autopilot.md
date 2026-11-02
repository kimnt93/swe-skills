# 09 — autopilot

status: human (flips the switch; samples merged PRs) · needs: 08

## Goal

Low-risk cards merge without a human click; the human samples afterwards. Everything is built: this
is a configuration change plus a sampling habit.

## What exists

- `fleet merge <pr> --risk <r> --sha <sha>`: merges only an allowed risk class, at the reviewer's
  verified SHA, with every required check passed; never money-path; never a PR without required
  checks. The `fleet-worker` review step calls it after a clean verdict.
- `autopilot.auto_merge` in `fleet/models.yaml`, empty by default.

## Steps

1. Gate: plan 08 is done (20 clean merges). If not, stop.
2. Pin model ids in `fleet/models.yaml` (replace the `opus` / `sonnet` / `haiku` aliases with full
   ids) so no model changes during an autopilot run. `fleet models check && fleet models apply`.
3. **Human:** set `autopilot.auto_merge: [low]`.
4. Add the sampling jobs with `hermes cron`: weekly, list the week's auto-merged PRs for the human to
   read; daily, a triage card for every red CI run on main.
5. After two weeks with no blocking defect in the samples, ask the human about `[low, standard]`.

## Verify

```bash
bash fleet/tests/selftest.sh          # the merge guard cases
fleet models show | tail -1           # autopilot auto_merge: ['low']
hermes cron list
```

## Log
