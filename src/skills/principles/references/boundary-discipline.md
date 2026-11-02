<!-- applies: Apply when wiring HTTP handlers, Kafka consumers, config loading, database reads, or calls to external APIs. -->
# Boundary Discipline

Validate once, at the edge. Trust types inside.

| Boundary | Parse into |
|---|---|
| HTTP request | Fiber body → a request struct, validated (Go); Litestar + `msgspec.Struct` (Python); axum extractor + serde (Rust) |
| Kafka message | decode + validate into the domain event, or send to the dead-letter path with the reason |
| environment | the one `config` module, at start-up; fail fast naming the variable, never print its value |
| database row | a row struct with `NOT NULL DEFAULT` columns; no NULL leaks inward |
| external API | a typed client in an adapter; timeouts and retries live here |

Inside the boundary, business logic is pure functions over validated types: no re-validation, no `nil` checks for things the boundary already rejected. Errors leave through the one response envelope.
