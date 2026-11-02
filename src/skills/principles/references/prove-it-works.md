<!-- applies: Apply after completing a task, before saying it is done. -->
# Prove It Works

Check the real thing, not a proxy.

- "It compiles" and "tests should pass" are not proof. Run them, and read the output.
- For a service change: `make verify` on the committed head, which includes the e2e tests and a live probe (`/healthz`, the changed `/v1` route, the Kafka round trip, the row in PostgreSQL).
- For a data change: query the actual rows.
- For perf: a before/after number (the **explain-the-number** principle).
- Paste the command and the tail of its output in the reply or the PR. Say what you could not check.
