# Go scaffold

*Verified with: compiled, linted (golangci-lint 2.14, zero findings) and tested with Go 1.26, including -race and integration tests against live PostgreSQL, Redis, Kafka and RustFS.*

Start from `assets/template` rather than from a blank directory: it already encodes the stack
([stack](stack.md)) and the layering rules, and it builds.

## Layout

```text
cmd/api/main.go                      composition entry: config -> logger -> bootstrap -> app -> graceful shutdown
internal/config/                     the only reader of environment variables: loader.go + postgres.go redis.go kafka.go s3.go (*_FILE secrets, no defaults for passwords)
internal/domain/<aggregate>/         pure rules: no I/O, no framework, no logging, no time.Now (inject the clock)
internal/domain/apperr/              business error: status, stable code, safe message
internal/application/                use cases + the ports they need (ports.go); imports domain only
internal/infrastructure/postgres|redisx|kafkax|s3x/   adapters implementing ports; SQL (raw, as constants) and driver tags live here only
internal/interfaces/httpapi/         server.go (Fiber config, middleware order, routes), api/ (envelope), handlers/, middleware/
internal/models/                     JSON contract types (also the Swagger source)
internal/bootstrap/                  the only place where concrete adapters meet use cases
internal/logger/                     from the service-logging skill (unified log format)
schemas/                             goose migrations, immutable once released (NOT NULL DEFAULT columns: no pointers in Go)
.golangci.yml                        the Go standard: gofmt -s, goimports (module group), govet, staticcheck, revive, errcheck, ...
.env.example                         every variable the loaders read; secrets blank
```

Dependencies point inward: `interfaces -> application -> domain`; `infrastructure` implements application ports.

## Steps

1. Copy `assets/template/.` into the new repository; replace `example.com/service` with the module path
   (`grep -rl example.com/service . | xargs sed -i 's#example.com/service#<module>#g'`) and `example-service` in `.env.example`.
2. Delete adapters the service does not use (`kafkax`, `redisx`, `postgres`, `s3x`) together with their loader file in
   `internal/config`, their lines in `config.go`, `bootstrap` and `.env.example`. A service without Kafka also drops cgo: `CGO_ENABLED=0` builds.
3. Rename the sample `item` aggregate to the real one, or keep it as the pattern for the first feature
   ([feature](feature.md)).
4. `go mod tidy`, `cp .env.example .env`, fill the blank secrets (no defaults for passwords), then run the checks below.
5. Add deployment files with `deployment-setup` (Dockerfile, Swarm/local Compose, CI): same variable names, the
   health gate `scripts/health.sh`, `HEALTH_DEPS`, and a `migrate` one-shot job. Add tracing with `service-tracing`
   (`internal/telemetry`) and OpenTelemetry metrics.

## Checks (all must pass before the first commit)

```bash
golangci-lint fmt --diff ./...   # prints nothing (gofmt -s + goimports with the module as local prefix)
golangci-lint run ./...          # 0 issues: govet, staticcheck, revive (doc comments, naming), errcheck, ...
go test -race ./...
CGO_ENABLED=1 go build -trimpath -o bin/api ./cmd/api
! grep -rEn '"github.com/(go-pg|redis|confluentinc|gofiber)|zerolog' internal/domain internal/application
! grep -rEn 'internal/(infrastructure|interfaces)' internal/application internal/domain
```

With live infrastructure (see `deployment-setup/assets/templates/docker-compose.infra.local.yaml`):
`go test -tags integration -race ./internal/e2e/...` ([test](test.md)).

## Rules baked into the template

- **Struct rules:** plain value fields, no pointers, no `omitempty` (rows, JSON models, the response envelope, config); rows use
  `pg:"col,use_zero"` and `pg:"-"` for ignored fields; SQL is raw and lives in constants ([postgres](postgres.md)).
- **Everything from the environment:** one `Loader` collects every missing variable by name; secrets (`*_PASSWORD`, `S3_*_KEY`,
  `INTERNAL_SERVICE_TOKEN`) have no default and may come from `NAME_FILE`; `TestEnvExampleIsComplete` keeps `.env.example` honest.
- Config fails by variable name and never prints values; a missing password is an error, not a default.
- Handlers only bind, call one use case and answer through the envelope; infrastructure errors become a generic 500.
- The API follows the [api-contract](../../api-contract/SKILL.md) skill: port 3000, routes under `/v1`, Swagger at `/docs`, and
  `/healthz` (identity, `api_versions`, non-secret config and one check per required dependency; 503 when one is down), at the root and
  not under `/v1`. There is no `/readyz`.
- Shutdown on SIGTERM: stop accepting, finish in-flight requests (15 s), then close the producer (drains) and pools.
- One process per `cmd/<name>`; a second process (worker, matcher) gets its own `cmd/` and shares `internal/`.

## Example usage

- “Scaffold a new Go API service for orders in our stack.”
- “Start a Kafka-consumer service with the same layout.”
