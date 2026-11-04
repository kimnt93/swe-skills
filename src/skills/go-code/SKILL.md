---
name: go-code
description: The default language for every HTTP API and backend service in this stack (the router's language table). Write, change or review Go code - new services and projects, HTTP APIs (Fiber v3), PostgreSQL (go-pg v10 with raw SQL), Redis (go-redis v9), Kafka (confluent-kafka-go), S3/RustFS object storage (AWS SDK v2), env config and secrets, features, tests and refactors. Use for any Go task such as add Postgres or Redis, consume or produce Kafka, store files in S3, add an endpoint, scaffold a service, write tests or refactor; it routes to the matching reference and carries the Go code standard (gofmt, goimports, golangci-lint, no pointers and no omitempty in structs) and the readable-code rules (one statement per line, 100 columns, multi-line SQL).
metadata:
  group: language
  summary: "Default for APIs, services and Kafka consumers: Go with Fiber v3, Postgres, Redis, S3"
  version: "1.0"
---

# Go code

One entry point for Go work. Read this page, then **read the references that match the request** (table below) before writing code.

**Go with Fiber v3 is the default for every new HTTP API, service, Kafka consumer and worker.** ML goes to `py-code`,
a measured hot path to `rust-code`, web UIs to `ts-code` (which calls this service through its OpenAPI file).

## How to work

1. **Discover the project first.** Read `go.mod`, `AGENTS.md`/`README`, the layout (`cmd/`, `internal/...`) and one sibling file per layer you will touch.
   Follow what the project already does; use the defaults below only for new code or when the project has no convention.
2. **Pick the topics** from the request and read the matching reference(s). Several usually apply (for example "add Postgres to this service" =
   [postgres](references/postgres.md) + the environment section below + [feature](references/feature.md) for the order of work).
3. **Implement inside-out** (domain, application port, adapter, handler, composition), reusing the tested files in `assets/template`
   instead of writing adapters from scratch.
4. **Write it readable.** Before you write code, read [readable-code](references/readable-code.md) and follow it for every line you add or change: one statement per line, spaces, short lines, small functions, multi-line SQL. Run the formatter, then check your own diff against its list.
5. **Verify** with the checks at the bottom; report what ran and what did not (live infrastructure, race detector).

## Which reference to read

| The request mentions | Read |
|---|---|
| new service, new project, "start", layout, bootstrap, graceful shutdown | [scaffold](references/scaffold.md) (the tested skeleton in `assets/template`) |
| which library, stack, JSON speed, code standard, naming, lint | [stack](references/stack.md) |
| endpoint, route, handler, middleware, Fiber, Swagger, response envelope, validation | [fiber-api](references/fiber-api.md) |
| API contract: `/v1` versions, `/docs` Swagger, `/healthz`, `/internal` (service token + caller headers), port 3000, host `{service}.{env}.{host}`, refactor an API | the `api-contract` skill |
| Postgres, SQL, query, repository, migration, goose, struct rows, transaction | [postgres](references/postgres.md) |
| formatting, readability, long lines, clean up, review, **writing or formatting any SQL query** | [readable-code](references/readable-code.md) |
| use the ORM (`pg.DB.Model`), "swap to an ORM" | the `db-orm` skill (go-pg v10; opt-in; **raw SQL is the default**) |
| migration, schema change, new column or index, goose | the `db-migrations` skill (goose SQL files) |
| Redis, cache, lock, TTL, idempotency key, pub/sub | [redis](references/redis.md) |
| Kafka, topic, consumer, producer, stream, partition, offset | [kafka](references/kafka.md) |
| S3, RustFS, MinIO, bucket, object, file, artifact, upload | [s3](references/s3.md) |
| add a feature, use case, business rule, new capability end to end | [feature](references/feature.md) |
| tests, table tests, integration test, race, benchmark, CI | [test](references/test.md) |
| refactor, clean up, restructure, split, simplify, remove ORM or pointers | [refactor](references/refactor.md) |
| logging, tracing, metrics, Dockerfile, Compose, CI deploy | the `service-logging`, `service-tracing`, `service-errors` (Sentry/GlitchTip), `data-realtime-metrics`, `deployment-setup` skills |

## Rules that always apply

- **Stack:** Fiber v3, go-pg v10 with **raw SQL by default (an ORM only when asked: `db-orm`)**, go-redis v9, confluent-kafka-go v2 (cgo), AWS SDK v2 for S3/RustFS, zerolog, goose, OpenTelemetry. Do not
  add a second library for a concern the project already covers ([stack](references/stack.md)).
- **Code standard:** gofmt `-s` + goimports (std, third-party, module groups), `golangci-lint` with `assets/template/.golangci.yml` (0 findings), doc
  comments on exported identifiers, `MixedCaps` and initialisms (`ID`, `URL`), errors lower-case and wrapped with `%w`, `ctx` first, early returns.
- **Readable code, always:** one statement per line, spaces around every operator, at most 100 columns (`gofmt` never wraps: you do), a condition has at most two
  operands (more: one `if` per rule, each with its own error), a chain has at most three calls per line, a function fits one screen, a blank line between steps, and
  **SQL is written multi-line, one clause and one column per line**. Never compress code to save lines ([readable-code](references/readable-code.md): bad/good examples).
- **Structs:** plain value fields, **no pointers and no `omitempty`** (rows, JSON models, config) so every field has a zero default.
  Enforced: `go run scripts/structcheck <dir>` (run by `make verify`) fails on any data struct that breaks it;
  a field that truly needs a pointer says why with `//structcheck:allow <reason>`. Rows use raw SQL
  constants and `pg:"col,use_zero"` tags, `pg:"-"` for ignored fields; columns are `NOT NULL DEFAULT ...`.
- **Layers:** `interfaces -> application -> domain`; adapters implement ports; domain does no I/O and reads no clock; handlers are thin.
  Enforced: `go run scripts/archcheck <module root>` (run by `make verify`) fails any import that crosses the layers;
  only `bootstrap`, `cmd` and `e2e` wire everything together.
- **Environment only:** one `config` package; variables follow the contract below; secrets from `NAME` or `NAME_FILE` with **no default**; `.env.example`
  lists everything with secrets blank; errors name the variable and never print a value.

| Infrastructure | Variables | Example file |
|---|---|---|
| PostgreSQL | `POSTGRES_HOST/PORT/DB/USER/PASSWORD/SSLMODE/POOL_SIZE` | `assets/env/postgres.env.example` |
| Redis | `REDIS_HOST/PORT/DB/PASSWORD/POOL_SIZE` | `assets/env/redis.env.example` |
| Kafka | `KAFKA_BOOTSTRAP_SERVERS/SECURITY_PROTOCOL/SASL_*/CONSUMER_GROUP` | `assets/env/kafka.env.example` |
| S3 / RustFS | `S3_ENDPOINT/REGION/BUCKET/FORCE_PATH_STYLE/ACCESS_KEY/SECRET_KEY` | `assets/env/s3.env.example` |

The loaders are `assets/template/internal/config/` (`loader.go` plus one file per infrastructure); copy only the ones the service uses.

## Verify

```bash
golangci-lint fmt --diff ./... && golangci-lint run ./...      # formatting and lint: no output / 0 issues
go vet ./... && go test -race ./...
docker compose -f docker-compose.infra.local.yaml up -d && scripts/health.sh --wait postgres,redis,kafka,s3     # deployment-setup templates
set -a; . ./.env; set +a; go test -tags integration -race ./internal/e2e/...                                      # live adapters
```

## Example prompts

- "add Postgres to this service" / "list open orders with a bounded query and an index" -> postgres, feature
- "consume the orders topic and upsert into Postgres, at-least-once" -> kafka, postgres
- "store each report as JSON in RustFS" -> s3 · "add a per-account lock" -> redis · "scaffold a new Go API" -> scaffold
