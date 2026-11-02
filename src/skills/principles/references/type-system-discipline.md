<!-- applies: Apply when designing types or a function signature in Go, Python or Rust. -->
# Type-System Discipline

Make illegal states unrepresentable.

- Distinct types for distinct meanings: `type OrderID string`, `type Price decimal.Decimal` (Go); `NewType` or a small `msgspec.Struct` (Python); newtypes (Rust).
- Sum types over flags: a Rust `enum`, a Python union of frozen dataclasses with `match`, a Go sealed interface or a status type with one switch that the linter checks for exhaustiveness.
- No `any` / `interface{}` / `dict[str, Any]` in the domain. Parse external data at the boundary into a real type.
- Derive types from the authoritative schema (OpenAPI, the SQL schema, the Kafka message schema) instead of hand-copying them.
