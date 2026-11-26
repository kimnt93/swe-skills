---
name: developer
description: "How the developer agent implements one card in its own worktree: test first, the smallest change inside the card's files, sync with main, make verify on the committed head, then push the branch and open the PR. Use when a workflow node asks you to build a card, fix review findings, or fix a failing check on your own branch."
metadata:
  group: process
  summary: "Developer: one card in one worktree, test first, verify on the head, push and open the PR"
---

# Developer

You implement **one card**: the goal, files and branch in your brief. Language and craft come from the
**swe** router and the language skill it picks; this skill is the delivery contract.

## Steps

**Before any step:** `issue_gate.py issue <n> --repo <owner>/<repo>` (the **github** skill) must allow the card's issue.
Refused (done, not planned, duplicate or not approved): change nothing and report the reason.

0. **Branch first.** Your branch must be `<type>/<issue>-<slug>` (the **github** skill). Your brief names it; check
   `git branch --show-current` against that. If the brief has no issue number, create the issue with `gh issue create`
   and rename the branch (`git branch -m`) before the first commit. Never commit on `main` or on a branch that breaks the pattern.
1. Work only in your worktree and only in the card's files. Another file is a new card: stop and say so.
   **Send no data the card does not ask for:** no new or wider call, telemetry, SDK, upload, CI or install step that
   sends, unless the issue names that destination and data. The review fails it
   ([outbound data](../security-review/references/outbound-data.md)). A card that needs one it does not name: stop and
   say so. Run the [security scan](../security-review/SKILL.md#the-scan) before the PR and resolve its items.
2. **Test first** (the **tdd** skill): a failing test that states the goal, then the smallest change that passes.
   Money-path cards also get a replay test (**replay-test**).
3. Small Conventional Commits (the **github** skill), one feature function, a small diff. Run **deslop** before
   the last commit.
4. Before the PR: fetch, rebase on the newest `origin/main` under your name
   (`agent_identity.py git --author "<your name>" -- rebase origin/main`), then run the project's verify command. On a
   conflict, stop and report the files; do not resolve it (the integrator does).
5. Done means the verify command (`make verify`, or the issue's `Done when`) exits 0 on the committed head and
   `git diff --name-only origin/main...HEAD` lists nothing outside the card's files.
6. Push the branch and open the PR (`Closes #<issue>`), lint it (`pr_lint.py`), check the result (**github**).
   A rebased, already-pushed branch is pushed with `--force-with-lease`, your branch only.
7. When your brief carries review findings or a failing check, fix exactly those, on the same branch, and
   push; do not open a second PR.

## Phases

A card runs in up to three steps; your brief says which (`phase:` in the goal). Without a phase, do everything above.

- **phase: code.** Steps 0 to 3 and 5, then stop: no push, no PR. Last line `NODE DONE <head sha> <one line>`.
  The docs agent follows your change next, in this worktree.
- **phase: pr.** The docs agent has committed to your branch. Run steps 4 to 6 with its commit included (read
  `docs/` once to see it is there), and put "docs: updated" or "docs: no change" in the PR body.

## When a bot started you

Your brief's `Deliver` line says how far you go (open the PR, commit only, or report only). Report **once**, with
`worker_done` to that bot, in the [agent report](../bot-orchestration/assets/agent-report.template.md) format; put the PR
URL under `Did`. Message nobody else and start no helpers ([bot-orchestration](../bot-orchestration/SKILL.md)). The last
line below is for workflow nodes.

## Last line, exactly one of

```
CARD DONE <head sha> <pr url>
CARD BLOCKED <one-line reason>
```

## Never

Push to `main`, touch files outside the list, resolve a conflict in another card's files, skip or weaken a
test, or report done without the `make verify` tail.
