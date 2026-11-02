# Go tests

*Verified with: the tests in assets/template pass with Go 1.26 against live infrastructure.*

Test behaviour at the lowest layer that can show it. Reference: `assets/template` (`*_test.go`,
`internal/e2e/e2e_test.go`).

## Unit tests

- **Table-driven with named cases**, one failure message that says expected vs got; `t.Run(tc.name, ...)`.
- **Fakes, not mock frameworks.** Ports are small interfaces; write a 10-line fake in the test file (`fakeRepo`, `fakeEvents`).
- **Inject time and randomness** (`Now func() time.Time`, an id generator, a `Sampler` with a fixed source). Never sleep to
  "wait for" logic; use channels, `sync.WaitGroup` or polling with a deadline.
- **Domain tests are free** (no I/O): cover every rule and boundary. Application tests use fakes and assert side effects
  (events published, repo calls). Handler tests go through `app.Test` and assert status, envelope and error `code`.
- **Race detector on:** `go test -race ./...`; a data race is a failing test. Run goroutine-heavy code with `-count=10`.
- **Config tests** assert that a missing password fails by name and that no secret value appears in the error.
- A new safeguard needs a test that fails when the safeguard is removed.

## Integration tests (`//go:build integration`)

Real PostgreSQL, Redis and Kafka, never mocks, for SQL, locking, TTLs and consumer behaviour. Keep them in
`internal/e2e` (or next to the adapter), skipped when the environment is not configured.

```bash
# disposable infrastructure (deployment-setup/assets/templates/docker-compose.infra.local.yaml)
docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka
scripts/health.sh --wait postgres,redis,kafka        # block until reachable (same gate as production)
set -a; . ./.env; set +a
go test -tags integration -race -count=1 ./internal/e2e/...
docker compose -f docker-compose.infra.local.yaml down -v
```

What to assert:

| Adapter | Assert |
|---|---|
| Postgres | migration applies; round trip; `ErrNoRows` maps to the sentinel; **zero values are stored, not NULL**; upsert is idempotent; `SKIP LOCKED` claim; transaction rolls back on error |
| S3 / RustFS | put/get/list/delete round trip; a missing key maps to `ErrNotFound`; bucket health check |
| Redis | a second lock holder is refused; release frees it; TTL expires |
| Kafka | seed the topic first, then publish until the consumer receives it; key and value intact; commit only after the handler succeeds |

Reset the disposable database at the start of the run (`DROP SCHEMA public CASCADE` behind a guard that refuses non-disposable
names, see `freshDatabase` in the scaffold) so leftovers from other tools never leak in. Use unique names per run (`uuid` topics, keys, groups) so reruns and parallel jobs never collide. A freshly started
single-node broker needs several seconds: gate with `health.sh --wait`, do not `sleep`.

## Benchmarks and profiling

`go test -bench . -benchmem ./...` for hot paths (matching loops, parsers, JSON); compare before/after with `benchstat`;
`pprof` before optimising. A hot loop must not allocate, log or query per iteration.

## CI

`golangci-lint fmt --diff ./...` (empty), `golangci-lint run ./...` (0 issues), `go vet ./...`, `go test -race ./...`, `govulncheck ./...`, `go build ./cmd/...`, plus the integration job
on the runner that has Docker. Run the toolchain in the same image the Dockerfile builds with.

## Example usage

- “Add table-driven tests for the order validation rules.”
- “Write an integration test for the Kafka consumer's at-least-once behaviour.”
