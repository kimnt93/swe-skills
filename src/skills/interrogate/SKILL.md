---
name: interrogate
description: "Adversarial review of a diff or a design: adversaries try to break it, and only findings proven by a run survive. Use before shipping a contested or risky change, for 'challenge this', 'find blind spots', 'review this branch', and as the brief of the cross-family reviewer lane."
metadata:
  group: process
  upstream: "cursor/plugins pstack@ae5650f skills/interrogate (rewritten)"
---

# Interrogate

Adversaries try to break the change. **A finding survives only when a command proves it.** Report
findings; don't fix them.

## Frame

- **Scope:** what the user names, else the branch diff from its merge base with `main`.
- **Intent:** restate it from the request, the commits, the PR body and the card.

## Fan out

- **In one harness:** 2–3 adversaries (in Claude Code, `subagent_type: "@PLUGIN@:adversary"`), each
  in its own worktree, on tiers `top` and `mid`.
- **Cross-family (preferred for a PR):** the other lane reviews (`fleet lane review <author lane> <card>`).
- **Wide or risky change:** a Hermes swarm card with both lanes as adversaries.

Brief each adversary with the scope, the intent, and:

> Break this change. Prove each finding with a run against the real code: a failing test, a repro
> script, or command output showing the wrong behaviour. Report the title, the exact command, the
> output it printed, and the output the intent requires. Leave out anything you did not run: style,
> naming, and risks that need a future change. No findings is a valid result.

Attacks worth trying in this stack:

| Area | Try |
|---|---|
| Go/Fiber API | missing or malformed body, wrong content type, huge payload, a missing header (`x-internal-service-token`), the response envelope on every error path |
| Kafka consumers | a duplicate message, out of order, a poison message, a crash between the DB commit and the offset commit |
| PostgreSQL | NULL or zero in each new column, a concurrent update of the same row, a migration on a big table |
| Python ML | a different seed, an empty or skewed batch, NaN and inf in features, train/serve skew |
| Rust | overflow, an empty input, a panic path (`unwrap`, indexing), a PyO3 call with the GIL held |
| Frontend | an API error envelope, a slow or empty response, a refresh mid-flow, keyboard-only use |
| everything | a missing or blank env variable; `audit_api.py` and `probe_api.py` for services |

## Verify and report

Re-run every finding's command yourself. Keep it only if it reproduces **and** breaks the intent.
Merge findings with one root cause.

- **Intent:** the restatement.
- **Findings:** command, output, how it breaks the intent, who found it. Or "no verified findings".
- **Dropped:** per adversary, how many and why.
