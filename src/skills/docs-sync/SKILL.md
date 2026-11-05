---
name: docs-sync
description: "How the docs agent keeps a repo's docs/ true to one card's change: compare the diff with the existing docs, add or update the usage in docs/references/*.md and the summary index in docs/README.md, run every command it shows, commit in the card's worktree and hand back to the developer, who opens the PR. It never plans and never edits source. Use when a workflow node asks you to sync the docs of a change."
metadata:
  group: process
  summary: "Docs sync: compare a change with docs/, update the README index and references, hand back"
---

# Docs sync

Every implementation changes what a reader of the repo needs to know. You follow that change in `docs/`. You do not
plan: you compare, then update. Another repo that depends on this one reads `docs/README.md` first and opens a reference
file only for the section it needs, so `docs/` is the repo's public usage.

| Task | Read |
|---|---|
| where each kind of content goes, the README index, a reference file | [layout](references/layout.md) |

## Two modes (your brief says which; with a card it is always `follow`)

- **follow** (default): update `docs/` for the changes since the docs were last touched. The base is the card's base,
  or, in a docs-only task, the newest commit that changed `docs/` (`git log -1 --format=%H -- docs`).
- **rewrite**: `docs/` is stale or missing. Read the code (entry points, public API, commands, config keys) and write
  `docs/` again from it in the layout below; delete a reference the code no longer has. Still no plan: go topic by topic
  from what the code exposes.

Neither mode needs a strong model: you read, compare and write. When the brief tells you to open the PR (a docs-only
task), do it as the **github** skill says; inside a card you never do.

## Steps

1. **Compare.** `git diff <base>...HEAD` (the base is in your brief) lists what changed (in rewrite mode, list the code instead); `ls -R docs/` and
   `docs/README.md` list what the docs say today. Nothing else is read except the code the diff touches.
2. **Decide per change, not per plan.** For each changed public behaviour (an endpoint, a command, a flag, a
   config key, an event or table other repos use, an exit code, an error), find the section that describes it:
   - it exists and is now wrong: update it;
   - it does not exist: add it to the reference file of its topic, or a new `docs/references/<topic>.md`;
   - the change is internal (a refactor, a test, a private function): write nothing.
3. **Keep the index true.** `docs/README.md` stays a short summary plus an index: one line per reference file, with
   what it covers and when to open it. A new reference file gets its line in the same commit.
4. **Check.** Run every command you wrote or changed, open every path and link. A command that fails is a finding:
   fix the doc if the doc is wrong; if the code is wrong, stop with `NODE BLOCKED`.
5. **Commit** `docs(<scope>): ...` in the card's worktree (small, one topic per commit), plain words (the **deslop**
   skill). Do not push and do not open a PR: the developer does, with your commit in it.

## Last line, exactly one of

```
NODE DONE <head sha> <one line: the docs you changed, or "no docs change">
NODE BLOCKED <one-line reason>
```

## Never

Plan, split or create cards, edit source or tests, invent behaviour the diff does not have, ask the human, push, or
leave a command unrun.
