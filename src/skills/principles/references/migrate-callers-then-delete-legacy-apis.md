<!-- applies: Apply when a new internal API replaces an old one that still has callers. -->
# Migrate Callers, Then Delete the Legacy API

Move every caller and delete the old API in the same wave. No compatibility layer for internal code.

- Find every caller (`gopls references`, `rg`, `cargo check` after removing the symbol, `pyright`).
- Migrate them with a codemod when there are many (the **build-the-lever** principle).
- Delete the old function, type or endpoint in the same PR or the next one, never "later".
- The exception is a contract outside the repo (a public `/v1` route, a Kafka topic another team reads, a DB column another service queries): there, use expand → migrate → contract with a dated removal.
