---
name: deslop
description: "Clean a diff before review: delete comments that restate code, dead code, debug output, unreasoned lint suppressions and defensive checks for impossible states, and make the PR text plain. Use before every review and commit, and when asked to tighten or unslop changes."
metadata:
  group: process
  summary: "Clean a diff before review: debug output, dead code, noisy comments"
---

# Deslop

Scope: the files the caller names, else the diff against `main`, including the working tree.
Change only what the diff added or touched.

## Remove

| Kind | Go | Python | Rust | TypeScript |
|---|---|---|---|---|
| debug output | `fmt.Println`, `log.Printf` left in | `print(`, `breakpoint()` | `dbg!`, `println!` | `console.log`, `debugger` |
| suppression without a reason | `//nolint` bare | `# noqa`, `# type: ignore` bare | `#[allow(...)]` bare | `// @ts-ignore`, `eslint-disable` bare |
| impossible-state guard | `if x == nil` after the boundary validated it | `if x is None` likewise | `.unwrap_or_default()` hiding a bug | `?.` on a value the type says is defined |
| dead code | unused funcs, commented-out code, unused params | same | same | unused exports, props |
| TODO | without an issue link | same | same | same |

**Comments:** keep only a non-obvious *why* the code can't show (a constraint, a link to the incident,
a units note). Delete comments that narrate what the next line does, phase markers (`// Step 1`), and
"added for X" history (that lives in git). A comment that states a constraint ("do not reorder: the
offset commit must follow the DB commit") is better as a test or a type: offer that, keep the comment
until it exists.

## Prove

Re-run the formatter, linter and tests of each language touched after the cleanup (`make verify`).
A cleanup that changes behaviour is not a cleanup: revert it.

## PR and commit text

Plain technical English: short sentences, one word per action, no filler ("This PR aims to...",
"robust", "seamless", "leverage"), no emoji, no claims without evidence. Say what changed, why,
and how it was verified.

**Reply:** what was removed (counts per kind), any constraint offered as a test, the verify tail.
