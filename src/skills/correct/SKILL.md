---
name: correct
description: "Find the mistakes agents keep repeating in a repo and make each one impossible: architecture first, then types, then a lint or check whose error names the fix, then a test, docs last. Use when you or the human correct the same mistake twice."
metadata:
  group: process
  summary: "Make a repeated agent mistake impossible with a check, not a sentence"
---

# Correct

Change the repo so the next agent can't make the mistake. Assume every contributor sees only the
files it opened, copies the nearest example, and takes the shortest path that compiles.

## 1. Find the mistake classes

Read recent review comments, reverts, fix-up commits, and the corrections in recent sessions. Group
them. A class counts once it has happened twice.

## 2. Fix each class at the highest level that works

1. **Architecture:** one owner per piece of state, one supported way to do each task; hide internals
   (Go `internal/`, Python `_private` modules, Rust `pub(crate)`) so the wrong import fails; delete the
   old way an agent would copy.
2. **Types:** make the bad state unrepresentable (the **type-system-discipline** principle).
3. **A check whose error names the fix:** a lint rule (`.golangci.yml`, ruff `pyproject.toml`,
   `clippy.toml`, `eslint.config`), a small checker like `go-code/scripts/structcheck`, or a CI step.
   If the pattern is already common, fail only on new occurrences.
4. **A test** of the behaviour.
5. **Docs or skill text last,** for judgment calls only.

## 3. Prove it

One commit per class. Prove each new check fails on a real past mistake. Run the same command
locally and in CI (`make verify`).

## 4. Keep the table

In the repo's `AGENTS.md`, keep a table: rule → what enforces it. When a rule exists but nothing
enforces it and the mistake repeats, enforce it now.

**Reply:** each class with its evidence, the level chosen, and why a higher level didn't work.
