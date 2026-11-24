# The issue

## ID and title

`<AREA>-<NN>: <outcome in a few words>`

| Part | Rule | Good | Bad |
|---|---|---|---|
| ID | area in capitals, hyphen, two or more digits; unique in the repository; numbers are never reused | `API-03` | `api3`, `Task 3`, `#3` |
| Title | outcome, 4 to 90 characters, no trailing period, no type prefix | `API-03: Cancel an open order` | `feat: cancel`, `API-03: working on cancel.` |

Areas are short and stable (`API`, `UI`, `DATA`, `OPS`, `DOC`, `TEST`, ...). A new area is one line in the epic or the
project's `AGENTS.md`, not a surprise in a title.

## Body (in this order)

```markdown
Lane: backend
Wave: 1
Difficulty: medium (one sentence: why this size)

## Goal
The outcome a caller or user can observe, in one short paragraph.

## Status
(only when work exists already) what is done, what is not.

## Read first
The files to read before touching anything, in order: the project's `AGENTS.md`, the spec section, the neighbours.

## Owned files (create or change only these)
- `path/one.rs` (new)
- `path/two.py` (the named function only)

## Forbidden
- every file not listed above (report a needed change in the PR text instead)
- dependency files and lock files unless the card says so

## Depends on
- nothing; start now      (or: `API-02` merged)

## Notes
Constraints, decisions already made, pitfalls, the commands to build.

## Done when (run from the repository root on the committed head; paste the output tails in the PR)
- `<test command>`
- `<lint command>`

## Branch and PR
- Branch `api-03/cancel-order` from `main`; commits `<type>(api-03): <summary>`; open a PR to `main`; do not merge it.
```

Sections *Goal*, *Read first*, *Owned files*, *Forbidden*, *Done when* and *Branch and PR* are required; *Status*,
*Depends on* and *Notes* are used when they have content. The three header lines (Lane, Wave, Difficulty) are required.

## What makes a package good

- **Closed scope**: the owned-file list is complete; two packages in the same wave never own the same file.
- **Runnable proof**: every *Done when* line is a command in backticks; "works" or "tested" is not a line.
- **Standalone**: the body names every file and command the agent needs; nothing depends on a chat.
- **Right size**: about one PR of at most a few hundred changed lines; larger work is an epic issue with a table of packages
  (`ID`, title, lane, difficulty, wave, depends on) and one package per row.

## Epic

An epic is an issue titled `<AREA>-00: <initiative>` (or the project's epic ID) with the table of packages and the waves.
Packages link it (`Refs #<epic>`); the epic closes when the last package merges.

## Old or duplicate issues

If an issue cannot be solved now: comment, create a package in this format that says "Replaces #N", link it in the comment and
close the old one. If it can be solved now: solve it, comment, close it. The comment and plan/verdict format is
[comments](comments.md).
