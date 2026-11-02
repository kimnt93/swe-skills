---
name: replay-test
description: "Prove a money-path change on a recorded day, not only on unit tests: replay an event stream (orders, fills, market data) through the real domain code, compare positions, balances and P&L to a golden file with exact decimals, and replay again with duplicated and redelivered events to prove idempotency. Use for any change to order, fill, position, balance, risk-limit or P&L code, and for every money-path card."
metadata:
  group: process
---

# Replay test

The **money-path** principle requires a replay. This skill is how. A unit test proves the case you
thought of; a replay proves the day that happened, and the duplicate and redelivery replays prove
the code survives Kafka's at-least-once delivery.

## The three pieces

1. **A recorded stream**, `testdata/replay/<name>.events.jsonl`: one event per line, in the order
   the service consumed them (from a topic dump, a DB export, or a staging day). Strip secrets and
   personal data. Keep it small enough to run in CI (thousands of events, not millions); add a
   second, larger stream for nightly runs if needed.
2. **A replay entrypoint** in the service that runs the *real* domain and application code: read
   JSON Lines on stdin, apply each event the way the consumer does, print the end state as one JSON
   object. No network, no clock, no randomness. See [entrypoint](references/entrypoint.md) for the
   contract and Go, Python and Rust shapes.
3. **A golden file**, `testdata/replay/<name>.golden.json`: the expected end state, reviewed by a
   human once, then changed only on purpose.

## Run it

```bash
R=<this skill>/scripts/replay.py
python3 $R record --events testdata/replay/day.events.jsonl --cmd "go run ./cmd/replay" --golden testdata/replay/day.golden.json
python3 $R check  --events testdata/replay/day.events.jsonl --cmd "go run ./cmd/replay" --golden testdata/replay/day.golden.json
python3 $R check  ... --mutate duplicate      # every event twice: same end state
python3 $R check  ... --mutate redeliver:3    # after each event, the 3 before it again: same end state
python3 $R --self-test                        # the script proves it can catch a non-idempotent engine
```

Add the three `check` runs to the service's `make verify` (a `replay` target called from
`verify-static`), so CI and every lane run them.

## Rules

- **Exact arithmetic.** The entrypoint prints money as strings or integers of minor units; the
  script compares decimals exactly. A float in the state is a bug to fix, not a tolerance to add.
- **The golden file changes only on purpose.** `record` refuses to overwrite it without `--force`.
  A changed golden file needs a sentence in the PR body saying which behaviour changed and why,
  and a human review of the diff.
- **Prove the replay can fail.** Before trusting a new stream, break the code on purpose (apply a
  fill twice, drop the dedup key) and watch `--mutate duplicate` fail. Then revert.
- **Say what you did not replay** in the PR: market conditions, symbols, or order types missing
  from the recorded streams.
- Ordering bugs between independent orders are out of scope here; for those use the
  `formal-verify` skill.
