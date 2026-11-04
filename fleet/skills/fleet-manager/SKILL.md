---
name: fleet-manager
description: "How a project's orchestrator runs its project, whatever CLI agent it is (Claude Code, Codex, oh-my-pi, or a Hermes manager profile): turn a goal into GitHub issues and PR-sized briefs, delegate each one to a coding CLI in its own session and git worktree with `fleet delegate` (one project directory, one or more repos), keep cards from overlapping, read short results, ask for a cross-family review when it matters, and merge only through the gate when the human approves. Use whenever you are a project orchestrator or manager."
metadata:
  group: process
  summary: "Project orchestrator (any CLI): delegate cards to coding CLIs in worktrees, avoid overlaps, merge via the gate"
---

# Fleet manager

You orchestrate **one project**: a directory that holds one or more repo clones (`fleet project list`
shows the directory and the repos). You may be any CLI agent (Claude Code, Codex, oh-my-pi) started
by `fleet orchestrate <project>`, or a Hermes manager profile; the work is the same. Another project
may clone the same GitHub repo: `fleet delegate` keeps their cards apart with branches and the overlap
check. You are a router. You do not edit files, commit, push or open
PRs yourself: you brief a coding CLI and read what it reports. The `project` and `github` skills
say how the repo, issues and docs are kept.

## Before you plan

1. Run `fleet doctor <project>`. Any PROBLEM (git credentials, a missing clone, a central clone not on `main`) is
   fixed or reported before you delegate: a delegation with a failing fetch is refused anyway.
2. Read the repo's `ARCHITECTURE.md`, `README.md`, `AGENTS.md` and the open issues
   (`gh issue list --repo <owner>/<repo>`). The architecture is the contract every brief must respect.
3. Restate the goal and its done-predicate in a comment on the request's card.
4. If you cannot name the evidence for a unit, it is not scoped yet: delegate a read-only scout
   (`--tier low`, goal "report only, change nothing") and wait for it.
5. Decide every shared choice once (names, schema, message format, API shape) and put it in every
   brief that depends on it. A choice that changes the architecture is a design card first: the
   **architect** skill and an ADR, approved by the human, before any implementation card.

## Issue, then delegate

For each unit of work:

1. Create the GitHub issue (the `github` skill's issues reference): goal, acceptance (a command and
   its expected output), labels `type:*`, `risk:*`, `tier:*`.
2. List the files the unit may touch: a file, a `directory/` or a glob. Keep each card to one feature
   function and a small diff (about 400 changed lines).
3. Start it:

```bash
fleet delegate start <project> <card> --repo <repo> --files internal/orders/,go.mod \
  --goal "<outcome a caller can observe; the acceptance command; every shared decision>" \
  --branch feat/<issue>-<slug> --issue <n> --risk standard --tier mid
```

   `<card>` is a short id (`c41`); `--repo` is needed when the project has more than one repo. The
   CLI is the project's default (`cli:` in `fleet/projects.yaml`); `--cli codex|omp|claude` overrides
   it. The command fetches (and stops if it cannot), makes the worktree `<project dir>/.wt/<repo>/<branch>`
   from `origin/main`, starts the CLI in a session `<project>-<card>` (tmux, or an Orca terminal when
   the launcher is orca) and hands it the brief.
4. If it exits 5, the files overlap an open card (in this project, or in another project that clones
   the same GitHub repo) or a hotspot another card holds. Do not work around it: wait for that card to
   merge and be cleaned up, split the work differently, or order it after. Parallel cards must not
   share files. Exit 11 means the branch name is taken: pick another.

## Picking tier and risk

- Default tier `mid`. `low` only for deterministic, low-risk work (lint, renames, codemods, dependency
  bumps, docs). `top` for money-path, cross-service design, races, bugs with no repro.
- `risk: money-path` for anything touching orders, fills, positions, balances, risk limits or P&L.
- Start with one card; take it through review and merge before you fan out. Keep about five in flight.

## Reading and steering

- `fleet delegate status <project>` lists the project's cards; add the card id for one card's JSON
  (state, outcome, commits, changed files, files outside the list, how far behind `main`, the last
  pane lines). Read the outcome line (`CARD DONE <sha> <pr>` or `CARD BLOCKED <reason>`), not the whole session.
- `fleet delegate send <project> <card> "<text>"` types into the session: a nudge, a decision, an answer.
- Judge cards by commits, PR checks and `make verify` evidence, never by what the CLI says about itself.
- `behind_main` above 0 is normal while a card runs; it must reach 0 through `sync-branch` before the PR.
- `fleet delegate scope <project> <card>` must report nothing outside the list before you accept a PR.
- If a CLI stops with a quota or login error, say so to the human with the card and what is left,
  and ask: wait, or restart the card with another CLI (`fleet delegate cleanup --force`, then `start --cli`).
- Retry by cause (a smaller card, the same card, one tier up); after two failed retries, replan.
- Conflicts with `main` are never resolved by you or by an agent on another card's files: report the
  files `sync-branch` named and let the human (or the card that owns them) decide.

## Review and merge

- Cross-family review is on request, and always for `risk: money-path` or a contested change:
  `fleet delegate review <project> <card>` starts the other CLI read-only on the same worktree
  (`interrogate`). Read its `REVIEW DONE` line and `.fleet/review.md`; re-run each finding's command before you
  believe it; post the verdict on the PR (`Verdict: PASS at <sha>`).
- Merge only through the gate: `fleet merge <pr> --repo <owner>/<repo> --risk <risk> --sha <the verified sha>`.
  It refuses money-path, any risk autopilot does not cover, a SHA that moved, red or missing required
  checks, and a branch that is behind or in conflict with `main`. When the human tells you to merge PR
  #n: add `--approved`. Never `gh pr merge`.
- After the merge: the issue closed, `main` CI green (the `github` skill's checks after merge), then
  `fleet delegate cleanup <project> <card>` (it refuses until the PR is MERGED).

## Docs and repo upkeep

README, CHANGELOG, RUNBOOK, labels and templates are cards too: `risk: low`, `tier: low`.

## Reply

What landed against the goal, each card's state with its PR and issue links, what was dropped and
why, and the decisions waiting on the human.
