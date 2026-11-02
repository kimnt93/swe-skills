<!-- applies: Apply when writing stateful logic, or when code branches on the same fields in several places. -->
# Model the Domain

Encode the domain in a structure, not in scattered conditionals.

- Order and position lifecycles are state machines: a named state type plus one transition function that rejects illegal moves (Go: `type Status string` + `func (o Order) Apply(e Event) (Order, error)`; Python: `enum.StrEnum` + a pure function; Rust: an `enum` with `match` that must be exhaustive).
- Repeated `if kind == ...` chains become a table (a map of handlers) or a sum type.
- Money is a type (decimal or integer minor units with a currency), not a `float64`.
- The domain package does no I/O and reads no clock: time comes in as an argument.
