### Autonomous run

**You own the exit condition. Define done, then drive to it without stopping.**

1. Write the exit condition as a checkable predicate before the first step (tests green, the repro
   fixed, all N cards merged, p95 under target).
2. Pick a wake mechanism from the [harness](harness.md) reference (`/loop`, a `--goal` card, `hermes cron`).
3. Each iteration makes the smallest change the evidence justifies, checks it against the predicate,
   commits if it advanced, reverts if it didn't (the **sequence-verifiable-units** principle).
4. Fix what blocks the goal yourself (a flaky test, a broken script) in its own PR. Ask the human
   only for irreversible actions or a real product call.
5. Log each iteration in the decision trail: what changed, did the predicate move.
6. Stop when the predicate is met. A plateau is not a stop; a real dead end is, and you say so.

**Reply:** the predicate, iterations, what landed, what was reverted, the final state.
