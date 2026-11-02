# Go refactor

Behaviour does not change. Each step compiles, passes the tests and could be committed alone.

## Procedure

1. **Pin behaviour.** Run `go test -race ./...` first. If the code under change has no test, write a characterization test
   (table of inputs -> current outputs, including errors) before touching it ([test](test.md)).
2. **Name the smell and the target.** One refactor per commit: extract function/package, narrow an interface, inject a
   dependency, replace a global, split a file, flatten nesting. State the target layout in the commit message.
3. **Move in small steps.** Rename with `gopls`/`go vet` guidance; move a type and fix imports; keep the old name only until
   the last caller moves. Do not mix a refactor with a bug fix or a library change.
4. **Verify after every step:** `golangci-lint fmt --diff ./...`, `golangci-lint run ./...`, `go vet ./...`, `go test -race ./...`, `go build ./cmd/...`, and the dependency
   rules below.

## Common refactors (target shape)

| Smell | Target |
|---|---|
| Handler holds SQL, rules or formatting | handler -> use case -> port; rule into `domain`; SQL into `infrastructure` |
| `pgx`/`go-pg`/`redis`/`kafka` imported in domain or application | declare a port in `application/ports.go`, implement it in `infrastructure`, wire in `bootstrap` |
| Interface declared next to its implementation, large | move to the **consumer**, keep only the methods it calls |
| Package-level mutable state, `init()` side effects | explicit constructor taking dependencies; compose in `bootstrap` |
| `time.Now()`, `rand`, `uuid` inside logic | inject `Now`/id functions; domain becomes deterministic |
| `context.Background()` deep in the call chain | thread the request `ctx`; cleanup uses a fresh short context |
| Swallowed or string-compared errors | wrap with `%w`, sentinels or `*apperr.Error`, `errors.Is/As` |
| Goroutine without owner | owner struct with `Run(ctx)`, stop on `ctx.Done()`, `WaitGroup` on shutdown |
| File over ~400 lines or catch-all `util` package | new small package named for the noun, one reason to change |
| ORM chains, pointer fields, `omitempty` on rows/models | raw SQL constants, plain value structs with `pg:"col,use_zero"` and `pg:"-"` ([postgres](postgres.md)) |
| N+1 queries, unbounded lists | one query with `IN (?)`/`= ANY`, `LIMIT`, an index ([postgres](postgres.md)) |
| Hand-rolled JSON/HTTP/Redis wrappers | the stack's library ([stack](stack.md)) |

## Guard rails

```bash
! grep -rEn '"github.com/(go-pg|redis|confluentinc|gofiber)|zerolog' internal/domain internal/application
! grep -rEn 'internal/(infrastructure|interfaces)' internal/application internal/domain
```

Stop and ask when a refactor needs a public API change, a schema change or touches a released migration. Do not delete data,
build artifacts or unrelated files.

## Example usage

- “Split this 900-line handler file and move the SQL behind a repository port.”
- “Remove the package-level Redis client and inject it.”
