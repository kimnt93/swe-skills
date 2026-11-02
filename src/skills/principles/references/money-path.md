<!-- applies: Apply whenever a change touches orders, fills, executions, positions, balances, margin, risk limits, fees or P&L, or the messages and tables that carry them. -->
# Money Path

Code that moves or counts money is held to a higher bar than the rest of the stack, because a
wrong answer there is a loss, not a bug report.

- **Top tier only.** Never give money-path work to a `low` tier model, and never let one review it.
- **Prove it on a replay, not only on unit tests.** Replay a recorded stream of market data,
  orders and fills through the changed code, and diff positions, balances and P&L against a
  known-good result (the **replay-test** skill). A unit test proves the case you thought of; a replay
  proves the day that happened.
- **Idempotent under retries and duplicates.** Kafka is at-least-once and brokers resend fills.
  Every handler must give the same end state when a message arrives twice or out of order (the
  **make-operations-idempotent** principle). Test it by sending the duplicate (`replay.py check --mutate duplicate`).
- **Exact arithmetic.** Prices, quantities and amounts use decimal or integer minor units with an
  explicit rounding rule. Never floats for money.
- **Model the order lifecycle as a state machine** with named states and allowed transitions, not
  scattered booleans (the **model-the-domain** principle). An illegal transition is an error, logged
  and counted.
- **No auto-merge.** A money-path PR needs a human approval after the cross-family review.
- **Say what you did not test.** Every money-path PR lists the scenarios it did not replay.
