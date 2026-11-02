# Design red flags

Screen every sketch against this list. One flag is a question; several are a different design.

| Flag | Looks like | Instead |
|---|---|---|
| pass-through layer | a service that only calls the repository with the same arguments | call the port from the use case directly |
| one-implementation interface | `type Store interface` with one struct and no port reason | a concrete type until a second one exists |
| boolean parameters | `Send(msg, true, false)` | an options struct or two functions |
| stringly typed | `status string`, `kind: str`, `type: string` | an enum or a named type with constants |
| nullable everything | `*int` fields, `Optional[...]` everywhere, `?:` props | value fields with defaults; required fields required |
| shared mutable state | a package-level map, a module global, a React context written from many places | an owner (one goroutine, one store, server state in the data layer) |
| I/O in the domain | the domain package imports `pgx`, `requests`, `fetch` | a port; the adapter does the I/O |
| time read inside logic | `time.Now()`, `datetime.now()` in a pure function | pass the time in |
| logic in the handler | a Fiber handler, Litestar route or React component with business rules | move it to the use case or a pure function |
| hidden coupling | two services reading the same table | one owner; the other calls its API or consumes its topic |
| float money | `float64` price, `number` amount | decimal or integer minor units |
