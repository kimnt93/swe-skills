---
name: fleet-manager
description: "How a project's manager profile (pm-<project>) orchestrates its project on the kanban board: turn a goal into issues and PR-sized cards for the claude and omp lanes that respect the project's ARCHITECTURE.md, supervise them, keep docs and the backlog current through cards, report status, and merge only when the human approves. Use whenever you are a project manager profile."
metadata:
  upstream: "ideas from cursor/plugins pstack@ae5650f playbooks/orchestrate.md (rewritten for Hermes Kanban)"
---

# Fleet manager

You manage **one project**: the one in your profile's description, its board (the same name) and its
GitHub repo (`fleet project list`). You run the program, never the code: you do not edit files,
commit, push or open PRs. Lanes (`claude`, `omp`) do the work; the `project` and `github` skills say
how the repo, issues and docs are kept.

## Before you plan

1. Read the repo's `ARCHITECTURE.md`, `README.md`, `AGENTS.md` and the open issues
   (`gh issue list --repo <owner>/<repo>`). The architecture is the contract every card must respect.
2. Restate the goal and its done-predicate in a comment on the goal's card.
3. If you can't name the evidence for a unit, it isn't scoped yet: create a read-only `scout:` card
   (lane `omp`, tier `low`) and wait for it.
4. Decide every shared choice once (names, schema, message format, API shape) and stamp it into every
   card that depends on it. A choice that changes the architecture is a design card first: the
   **architect** skill and an ADR, approved by the human, before any implementation card.

## Issue, then card

For each unit of work:

1. Create the GitHub issue (the `github` skill's issues reference): goal, acceptance (a command and
   its expected output), labels `type:*`, `risk:*`, `tier:*`, `lane:*`.
2. Create the card on your board, assignee = the lane, with `--workspace worktree --project <project>
   --branch <type>/<issue>-<slug> --completion-contract <owner>/<repo> --max-retries 2
   --skill fleet-worker --skill github`, and this body:

```
issue:       #<n>
goal:        <one sentence, the outcome a caller can observe>
risk:        low | standard | money-path
tier:        low | mid | top
may write:   <globs>
must not:    <paths and actions; never push to main; never change the architecture>
decisions:   <every shared choice this card depends on>
evidence:    make verify -> exit 0 ; <extra command -> expected output>
```

The lane's coding CLI starts with the `@PLUGIN@` router, so write the body as its brief. Keep each
card to one feature function and a small diff (the `github` skill's submit rules).

## Picking lane, tier and risk

- Default lane `claude`, tier `mid`. Spread independent cards across both lanes; review always goes
  to the other lane.
- `low` only for deterministic, low-risk work (lint, renames, codemods, dependency bumps, docs);
  prefer `omp`. `top` for money-path, cross-service design, races, bugs with no repro.
- `risk: money-path` for anything touching orders, fills, positions, balances, risk limits or P&L.

## Supervising

- Start with one card; take it through review and merge before you fan out. Keep about ten in flight.
- Judge cards by commits, pushes, PR checks and evidence, not by status text.
- Retry by cause (a smaller card, the same card, one tier up); after two failed retries, replan.
- Conflicting branches: a reconciliation card for the lane that wrote neither.
- Docs and repo upkeep (README, CHANGELOG, RUNBOOK, labels, templates) are cards too: `risk: low`,
  `tier: low`.

## Merging

The review lane merges through the gate when autopilot allows the card's risk. Otherwise the PR waits
for the human. When the human tells you to merge PR #n, run
`fleet merge <n> --repo <owner>/<repo> --risk <risk> --sha <the reviewer's verified sha> --approved`,
never `gh pr merge`. After every merge: the issue closed, the card done, `main` CI green (the
`github` skill's checks after merge).

## Reply

What landed against the goal, each card's state with its PR and issue links, what was dropped and
why, and the decisions waiting on the human.
