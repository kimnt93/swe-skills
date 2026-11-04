# Principles

The `principles` skill holds 22 short rules, each in its own file with what it means in Go, Python, Rust and
TypeScript. The router opens only the ones whose "applies" line matches the task and names in its reply each
one that changed a decision. Below: the rule in a line, and when it bites.

## Core

### laziness-protocol
The smallest change that solves the problem. One caller means no interface (a Go `interface`, a Python
`Protocol`, a Rust `trait` with a single implementation is a layer to remove, unless it is a port); no new
dependency for what the standard library does; no option nobody asked for. Applies when a diff is growing.

### subtract-before-you-add
Remove what the change makes dead first (unused functions, flags, env variables and their `.env.example`
lines, stale consumers), as its own green commit, then add. Applies when sequencing a feature or rewrite.

### foundational-thinking
Get the data shape right and the code becomes obvious: name the domain type and its table first, scaffold
before features (config, port, adapter tested on real infra, use case, handler), decide who owns anything
concurrent actors share. Applies before writing logic.

### build-the-lever
If you will do it more than once, or a reviewer must trust it, write the tool: a codemod instead of 40 edits,
a script that proves a data migration, `make verify` instead of a list of commands. The tool is the artefact.

### attack-the-premise
When two fixes sharing one assumption failed the same check, stop and test the assumption directly with a
five-minute probe ("each message arrives once", "this column is never NULL", "the test hits PostgreSQL").

### redesign-from-first-principles
When a requirement does not fit, design as if it had been known on day one, then migrate in verifiable steps.
A new boolean threaded through five functions, or a special case in every handler, is the sign of bolting on.

## Architecture

### model-the-domain
Encode the domain in a structure, not scattered conditionals: order and position lifecycles are state machines
with one transition function that rejects illegal moves; repeated `if kind ==` becomes a table or sum type;
money is a type; the domain does no I/O and reads no clock.

### boundary-discipline
Validate once at the edge (HTTP body, Kafka message, environment, database row, external API) into typed
values, then trust the types inside; business logic is pure functions; errors leave through the one envelope.

### type-system-discipline
Make illegal states unrepresentable: distinct types for distinct meanings, sum types over flags, no `any`,
`interface{}` or `dict[str, Any]` in the domain, types derived from the authoritative schema (OpenAPI, SQL).

### make-operations-idempotent
The same input applied twice gives the same end state. Kafka is at-least-once: dedup by a stable key with a
unique constraint and `ON CONFLICT DO NOTHING` (or `SET NX`); commit the offset after the database commit;
upserts for converging state; re-runnable migrations. Prove it by sending the duplicate.

### separate-before-serializing-shared-state
Remove the sharing first (partition by key, per-worker state merged on read, one worktree per agent); add a
lock only when one writer is a real invariant, and then make it structural and test the race.

### migrate-callers-then-delete-legacy-apis
For an internal API change, move every caller and delete the old one in the same wave; no compatibility layer.
The exception is a contract outside the repo (a public route, a topic, a column another team reads): there use
expand, migrate, contract with a dated removal.

### minimize-reader-load
Count the hops a reader makes to answer one question and cut them: collapse one-caller wrappers, keep mutable
state small and local, prefer a function that fits one screen. A refactor that lowers no one's load is not worth keeping.

## Verification

### prove-it-works
Check the real thing, not a proxy: "it compiles" is not proof. Run `make verify` on the committed head
(including the e2e tests and a live probe), query the real rows, show a before and after number, paste the
command and its output, say what you could not check.

### fix-root-causes
Trace the symptom to the first place the system went wrong. A `nil` check is a fix only if the value can
legitimately be missing; a retry only for a transient failure; `recover()`, a bare `except` and
`unwrap_or_default()` that swallow errors are symptom guards. Name the cause in one sentence with evidence.

### sequence-verifiable-units
Small units that each end green, checked before the next, ordered so the sequence explains itself (deletions,
scaffold, behaviour, cleanup; for migrations expand, migrate, contract, each its own PR). Never "test it all at the end".

### test-behavior-not-implementation
Assert what a caller can observe (handler response, use-case result, row written, message published), against
real infrastructure in integration tests, in table-driven form. A test that only checks a mock was called is
testing the implementation.

### explain-the-number
Before reporting a measurement, find what limits it (CPU, database, lock, partition count), whether the work
really happened, and that it repeats (`benchstat`, `pytest-benchmark` stats, criterion), that the same conditions held before and after, and that it matters end to end.

## Delegation and meta

### guard-the-context-window
Keep summaries in the main thread and bulk in subagents or files: send log reading, profile parsing and wide
searches to a subagent and take back the finding with `file:line`; brief subagents with paths, not pasted content.

### never-block-on-the-human
Proceed on reversible work and let the human correct after the fact. Ask only for irreversible actions
(production data, deploys, force-pushes to shared branches, money-path merges) and for product calls no
experiment can settle.

### encode-lessons-in-structure
Turn a repeated lesson into something that fails: a type, then a lint or checker (`.golangci.yml`, ruff,
`clippy.toml`, `structcheck`), a test, a CI step, and only last a sentence in a skill. The `correct` skill runs this loop.

## Domain

### money-path
Code that moves or counts money is held to a higher bar. Orders, fills, executions, positions, balances,
margin, risk limits, fees and P&L: top tier only (never a `low` model, never reviewed by one); proven on a
replay of a recorded day plus duplicate and redelivery runs (`replay-test`); idempotent under retries; exact
arithmetic (decimal or integer minor units, never floats); the order lifecycle a named state machine; never
auto-merged; every PR lists what it did not replay.
