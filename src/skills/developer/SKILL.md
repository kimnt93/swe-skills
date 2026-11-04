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

1. Work only in your worktree and only in the card's files. Another file is a new card: stop and say so.
2. **Test first** (the **tdd** skill): a failing test that states the goal, then the smallest change that passes.
   Money-path cards also get a replay test (**replay-test**).
3. Small Conventional Commits (the **github** skill), one feature function, a small diff. Run **deslop** before
   the last commit.
4. Before the PR: `swe-cli delegate sync-branch --verify` (fetch, rebase on the latest `origin/main`, `make
   verify`). On conflicts it aborts; stop and report the files, do not resolve them (the integrator does).
5. Done means `make verify` exits 0 on the committed head and `swe-cli delegate scope <project> <card>` reports
   nothing outside the file list.
6. Push the branch and open the PR (`Closes #<issue>`), lint it (`pr_lint.py`), check the result (**github**).
   A rebased, already-pushed branch is pushed with `--force-with-lease`, your branch only.
7. When your brief carries review findings or a failing check, fix exactly those, on the same branch, and
   push; do not open a second PR.

## Last line, exactly one of

```
CARD DONE <head sha> <pr url>
CARD BLOCKED <one-line reason>
```

## Never

Push to `main`, touch files outside the list, resolve a conflict in another card's files, skip or weaken a
test, or report done without the `make verify` tail.
