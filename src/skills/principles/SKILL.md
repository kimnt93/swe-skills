---
name: principles
description: "The engineering principles of the @PLUGIN@ plugin, one short file each with what it means in Go, Python, Rust and TypeScript: when it applies and what it requires. Read the index at the start of a task and open every principle whose applies line matches: idempotency for Kafka consumers, explain-the-number for a benchmark or a model score, money-path for orders and P&L."
metadata:
  group: process
  upstream: "cursor/plugins pstack@ae5650f skills/principle-* (rewritten for our stack; money-path is our own)"
---

# Principles

Open a principle when its "applies" text matches the task, then follow it. Name each principle that changed a decision in your reply.

## Core

| Principle | Applies |
|---|---|
| [laziness-protocol](references/laziness-protocol.md) | Apply when a diff is growing: a new layer, interface, option, helper or dependency is about to appear. |
| [subtract-before-you-add](references/subtract-before-you-add.md) | Apply when sequencing a feature, a refactor or a rewrite. |
| [foundational-thinking](references/foundational-thinking.md) | Apply before writing logic: choosing types and data shapes, ordering scaffold against features, deciding what concurrent actors share. |
| [build-the-lever](references/build-the-lever.md) | Apply to any non-trivial work: edits across many files, migrations, data fixes, checks. Build the tool that does it or proves it instead of working by hand. |
| [attack-the-premise](references/attack-the-premise.md) | Apply when two or more fixes that share one assumption have failed the same check. |
| [redesign-from-first-principles](references/redesign-from-first-principles.md) | Apply when a new requirement does not fit the current design. |

## Architecture

| Principle | Applies |
|---|---|
| [model-the-domain](references/model-the-domain.md) | Apply when writing stateful logic, or when code branches on the same fields in several places. |
| [boundary-discipline](references/boundary-discipline.md) | Apply when wiring HTTP handlers, Kafka consumers, config loading, database reads, or calls to external APIs. |
| [type-system-discipline](references/type-system-discipline.md) | Apply when designing types or a function signature in Go, Python or Rust. |
| [make-operations-idempotent](references/make-operations-idempotent.md) | Apply when designing a Kafka consumer, a retry, a job, a migration step, or any handler that can run twice after a crash. |
| [separate-before-serializing-shared-state](references/separate-before-serializing-shared-state.md) | Apply when concurrent actors (goroutines, async tasks, threads, consumers, workers) might write the same row, key, file or branch. |
| [migrate-callers-then-delete-legacy-apis](references/migrate-callers-then-delete-legacy-apis.md) | Apply when a new internal API replaces an old one that still has callers. |
| [minimize-reader-load](references/minimize-reader-load.md) | Apply when code is hard to follow: many layers between a question and its answer, or hidden state. |

## Verification

| Principle | Applies |
|---|---|
| [prove-it-works](references/prove-it-works.md) | Apply after completing a task, before saying it is done. |
| [fix-root-causes](references/fix-root-causes.md) | Apply when debugging. |
| [sequence-verifiable-units](references/sequence-verifiable-units.md) | Apply to multi-step work (migrations, sweeps, many similar edits) and to how commits and PRs are ordered. |
| [test-behavior-not-implementation](references/test-behavior-not-implementation.md) | Apply when writing, changing or keeping a test. |
| [explain-the-number](references/explain-the-number.md) | Apply before trusting, reporting or acting on a measured number: latency, throughput, memory, a speedup, a backtest result. |

## Delegation and meta

| Principle | Applies |
|---|---|
| [guard-the-context-window](references/guard-the-context-window.md) | Apply when output is large: long logs, big files, many search results, profiles, fan-out planning. |
| [never-block-on-the-human](references/never-block-on-the-human.md) | Apply when tempted to ask "should I do X?" about reversible work. |
| [encode-lessons-in-structure](references/encode-lessons-in-structure.md) | Apply when the same instruction is written a second time, or the same correction is made twice. |

## Domain

| Principle | Applies |
|---|---|
| [money-path](references/money-path.md) | Apply whenever a change touches orders, fills, executions, positions, balances, margin, risk limits, fees or P&L, or the messages and tables that carry them. |
