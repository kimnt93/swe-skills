---
name: integrator
description: "How an agent brings an open pull request up to date with main and resolves its merge conflicts safely: rebase, resolve only inside files its own card owns, re-run make verify, get a fresh review of the resolution, and stop and hand over when a conflict touches another card's files or a hotspot. Use whenever a card's branch is behind or in conflict with main, `sync-branch` reported conflicts, or `swe-cli merge` refused a branch that is behind."
metadata:
  group: process
  summary: "Integrator: rebase a PR on main, resolve conflicts only in its own files, re-verify, re-review"
---

# Integrator

A PR that is behind `main` is rebased; one that conflicts is resolved **only when the resolution is
inside the card's own files and its meaning is clear**. Otherwise you stop. A workflow node starts you in the
card's worktree when the merge gate finds the branch behind `main` or in conflict.

## Steps

1. **Read the situation:** `swe-cli delegate status <project> <card> --fetch` (files, base, behind) and the
   card's file list (`swe-cli delegate scope <project> <card>`).
2. **Rebase:** `swe-cli delegate sync-branch`. It fetches, rebases on `origin/main` and aborts cleanly on a
   conflict, naming the files. No conflict: go to step 5.
3. **Decide who owns each conflicting file.**
   - In the card's file list and not a hotspot: you may resolve it.
   - Outside the list, a hotspot (migrations, lockfiles, generated clients, route registries), or a file
     another open card holds: **stop**. Report the files and the other card to the manager. A person
     (or the card that owns the files) resolves it.
4. **Resolve** (`git rebase origin/main`, edit, `git add`, `git rebase --continue`):
   - Keep both sides' intent: read the commits behind each side (`git log origin/main -- <file>`, the `why` skill).
   - Never drop `main`'s change to make the build pass, and never take "ours" or "theirs" wholesale.
   - A conflict you cannot explain in one sentence: stop and report it.
5. **Prove:** `swe-cli delegate sync-branch --verify` (fetch again, `make verify`). A failing verify after a
   clean rebase is a behaviour conflict: report it with the failing command; do not patch around it.
6. **Push your own branch:** `git push --force-with-lease origin <branch>`. Never another branch, never `main`.
7. The resolution is new code at a new SHA: the workflow sends it to the reviewer again; the old verdict
   does not carry over.
8. Last line, exactly one of:

```
CARD DONE <head sha> <pr url>
CARD BLOCKED <one-line reason>
```

## Never

- Resolve inside files outside the card's list, or edit anything beyond the conflict and what it forces.
- Merge, approve your own resolution, or skip `make verify`.
- Rebase a branch someone else pushed to.
