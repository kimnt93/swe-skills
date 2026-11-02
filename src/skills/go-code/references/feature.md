# Go feature

Read the code around the change first (one sibling per layer) and write what reads like it. Work inside-out so each
layer compiles and is tested before the next one depends on it.

## Order of work

1. **Understand the contract.** Inputs, outputs, error cases, who calls it, idempotency, concurrency (replicas), money/time.
   If the rule comes from an external market or regulation, cite the source in a comment.
2. **Domain** (`internal/domain/<pkg>`): the rule as pure code and a table-driven test. No I/O, logging or `time.Now()`
   (inject `Now`). New business failures are sentinels or `*apperr.Error` with a stable code.
3. **Application** (`internal/application`): the use case and, if it needs I/O, a **port declared where it is used** (small
   interface in `ports.go`). The use case owns flow and validation, not SQL. Test it with hand-written fakes.
4. **Infrastructure** (`internal/infrastructure/...`): implement the port with raw SQL constants and plain `pg`-tagged structs
   (`use_zero`, no pointers, no `omitempty`) ([postgres](postgres.md),
   [redis](redis.md), [kafka](kafka.md)); add `var _ application.X = (*Y)(nil)`. A schema change
   adds a goose migration (never edit a released one).
5. **Interface** ([fiber-api](fiber-api.md)): model types in `internal/models`, a thin handler, the route in
   the single route table, error mapping in `api.Map`, Swagger annotations, then `make swagger`.
6. **Composition**: wire the new adapter in `internal/bootstrap` only.
7. **Tests** ([test](test.md)): domain table test, use-case test with fakes, `app.Test` for the endpoint, and an
   integration test when SQL, locking, Redis or Kafka behaviour is involved. A new safeguard needs a test that fails when
   the safeguard is removed.
8. **Observability**: structured log with identity fields only (no secrets/payloads), metrics for new pipeline stages,
   dependency spans for new outbound calls (`service-tracing`).
9. **Docs**: README/AGENTS, `.env.example` and deployment variables for any new setting; API docs regenerated.

## Cross-cutting checks

- `ctx` first parameter of anything that does I/O; never stored in a struct; cleanup after cancellation uses a fresh context.
- Wrap errors with context and `%w`; compare with `errors.Is/As`; no `panic` in request or consumer paths.
- Replicas are concurrent: a "do once" job needs a database or Redis claim, not an in-memory flag.
- Every goroutine has an owner and a stop condition; wait for it on shutdown.
- New dependency? Stop and check [stack](stack.md).

## Verify

```bash
golangci-lint fmt --diff ./... && golangci-lint run ./... && go test -race ./...
go build ./cmd/...
! grep -rEn '"github.com/(go-pg|redis|confluentinc|gofiber)|zerolog' internal/domain internal/application
! grep -rEn 'internal/(infrastructure|interfaces)' internal/application internal/domain
go test -tags integration -race ./internal/e2e/...      # when SQL / Redis / Kafka behaviour changed
```

## Example usage

- “Add cancel-order: domain rule, use case, Postgres update with a lock, endpoint and tests.”
- “Add a Kafka consumer that updates positions and is safe to replay.”
