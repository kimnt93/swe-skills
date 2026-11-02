<!-- applies: Apply before writing logic: choosing types and data shapes, ordering scaffold against features, deciding what concurrent actors share. -->
# Foundational Thinking

Get the data shape right and the code becomes obvious.

1. Name the shape first: the domain struct (Go), frozen dataclass or `msgspec.Struct` (Python), struct or enum (Rust), and the SQL table it maps to.
2. Scaffold before features: config, the port, the adapter with a test against real PostgreSQL / Redis / Kafka, then the use case, then the handler (inside-out, as the language skills say).
3. Ask what concurrent actors share: two consumers of one topic, two requests on one row, two workers on one Redis key. Decide the owner before writing code.
