# Go stack

*Verified with: Go 1.26, fiber v3.5, go-pg v10.15, go-redis v9.23, confluent-kafka-go v2.15, aws-sdk-go-v2 s3, sonic 1.15, zerolog 1.35, golangci-lint 2.14, otel-go 1.47. Kafka needs cgo (bundled librdkafka).*

One stack per language keeps services reviewable and lets skills stay small. Use these libraries unless the
project already has a different, working choice (then follow the project: never mix two for one concern in
one service). Versions are those the templates were tested with, not pins: use the project's `go.mod`.

| Concern | Library | Why / rule |
|---|---|---|
| Language | Go 1.26+ | `gofmt`, `go vet`, `go test -race` clean |
| HTTP API | `github.com/gofiber/fiber/v3` | thin handlers, one response envelope ([fiber-api](fiber-api.md)) |
| JSON (hot paths) | `github.com/bytedance/sonic` via Fiber `JSONEncoder`/`JSONDecoder`; stdlib `encoding/json` elsewhere | benchmark before widening; never parse what you only forward |
| PostgreSQL | `github.com/go-pg/pg/v10` with **raw SQL** | SQL constants + `pg`-tagged plain structs (`use_zero`, `pg:"-"` for ignored fields), no pointers, no `omitempty`; maintenance-mode library, so keep it behind the repository port ([postgres](postgres.md)) |
| Migrations | `github.com/pressly/goose/v3` | immutable ordered SQL files in `schemas/`; run as a one-shot job |
| Redis | `github.com/redis/go-redis/v9` | locks, caches, wake-ups ([redis](redis.md)) |
| Object store (S3, RustFS) | `github.com/aws/aws-sdk-go-v2/service/s3` | custom endpoint, path-style, static keys from env ([s3](s3.md)) |
| Kafka | `github.com/confluentinc/confluent-kafka-go/v2` | idempotent producer, manual-commit consumer ([kafka](kafka.md)); needs `CGO_ENABLED=1` |
| Logging | `github.com/rs/zerolog` via the `service-logging` skill | unified JSON fields, `trace_id`/`span_id` |
| Tracing | OpenTelemetry via the `service-tracing` skill | dependency mode by default |
| Metrics | OpenTelemetry via `data-realtime-metrics` for pipelines | shared metric contract |
| Config | environment only (+ `joho/godotenv` locally); `NAME_FILE` for secrets | one `config` package; no defaults for passwords |
| IDs | `github.com/google/uuid` | UUID text at the edge |
| API docs | `swaggo/swag` + `gofiber/contrib/v3/swaggo` | regenerate after route/model changes |
| Concurrency | `golang.org/x/sync/errgroup`, `sync.WaitGroup` | every goroutine has an owner and a stop condition |
| WebSocket / MQTT feeds | `lxzan/gws` (or `gorilla/websocket`), `eclipse/paho.mqtt.golang` | ingestion services |
| Tests | stdlib `testing`, table-driven, hand-written fakes; `-tags integration` against real containers | no mock framework needed ([test](test.md)) |

**Raw SQL, plain structs:** queries are SQL constants; rows are plain structs mapped with `pg:"column,use_zero"` tags and
`pg:"-"` for ignored fields; there are no pointers and no `omitempty` anywhere (rows, JSON models, config), so a missing value is
a zero value. Every secret comes from the environment (`NAME` or `NAME_FILE`), with no default.

`pgx v5` is an acceptable PostgreSQL driver when the repository already uses it (and goose uses it through
`database/sql` for migrations only); do not run go-pg and pgx for the same data in one service.

## Code standard (the common Go format)

Write idiomatic Go as defined by *Effective Go*, the *Go Code Review Comments* and `gofmt`; the linter enforces it.

- **Format:** `gofmt -s` and `goimports` (imports in three groups: standard library, third-party, this module, separated by a
  blank line). Never hand-format. `golangci-lint fmt ./...` applies both; CI runs `golangci-lint fmt --diff` and fails on output.
- **Lint:** `golangci-lint run ./...` with `assets/template/.golangci.yml` (govet, staticcheck, errcheck, unused, ineffassign, revive,
  errorlint, noctx, bodyclose, misspell). The scaffold passes with zero findings; keep it that way.
- **Naming:** `MixedCaps`, never underscores; initialisms keep their case (`ID`, `URL`, `HTTP`, `JSON`, `SQL`: `userID`, `ServeHTTP`);
  packages are short, lower-case, singular nouns (`order`, not `orders`, `utils`, `common`); no stutter (`order.New`, not
  `order.NewOrder`); receivers are one or two letters, consistent across methods (`s *Store`), never `self`/`this`.
- **Comments:** every exported identifier has a full-sentence doc comment starting with its name; every package has one
  `// Package x ...` comment; comments explain why, not what.
- **Errors:** last return value; `fmt.Errorf("verb object: %w", err)` with lower-case text and no trailing punctuation;
  sentinels `ErrFoo`, types `FooError`; compare with `errors.Is/As`; handle every error (errcheck) or discard it explicitly with a reason.
- **Shape:** early returns instead of `else` after `return`; small functions; accept interfaces, return concrete types; make the zero
  value useful; `ctx context.Context` is the first parameter and is never stored in a struct; no `init()` side effects, no
  package-level mutable state.
- **Struct data:** plain value fields, **no pointers and no `omitempty`** so every field has a zero default (rows, JSON models,
  config); use pointers only for large mutable receivers and for types that must be shared.
- **Readable layout:** one statement per line, at most 100 columns (`lll`; `gofmt` never wraps), a condition has at most two operands, a function fits one screen
  (`funlen`, `nestif`), SQL constants are multi-line. `gofmt` is the minimum, not the goal: see [readable-code](readable-code.md) for bad/good examples.
- **Tests:** table-driven, named cases, `t.Helper()` in helpers, no `testify` required; `-race` always.

## Fast JSON and performance

- Default `encoding/json`; switch a path to `sonic` (Fiber config, or `sonic.Unmarshal` on a known hot decode)
  only after a benchmark. Sonic supports amd64/arm64; keep the stdlib fallback for other targets.
- Do not decode payloads you only forward (Kafka frames, webhooks): carry `[]byte`, hash it, publish it.
- To read a few fields from a large document use `tidwall/gjson` (or `valyala/fastjson`) instead of a full struct.
- Reuse buffers (`sync.Pool`) and preallocate (`make([]T, 0, n)`) in hot loops; no per-iteration logging.
- Parse timestamps once at the edge with `time.Parse(time.RFC3339Nano, s)` and store UTC; avoid reflection-heavy
  per-row conversions. Use integers (ns/ms) on the wire when both ends are yours.
- Profile before tuning: `go test -bench . -benchmem`, `pprof`.

## Adding or replacing a library

Standard library first. A new dependency needs a reason (what it replaces, maintenance status, license, cgo or
platform limits), goes behind a port when it touches I/O, and is recorded in the project's docs. Never add two
HTTP frameworks, two loggers or two Postgres drivers to one service. Pin or review Go minor upgrades together
(`go.mod` `go` line, Dockerfile `GO_IMAGE`, CI image).

## Related skills

[readable-code](readable-code.md) · [scaffold](scaffold.md) (new service) · [s3](s3.md) · [feature](feature.md) (add a feature) ·
[test](test.md) · [refactor](refactor.md) · `deployment-setup` (Dockerfile, Compose,
CI; set `CGO_ENABLED=1` and ship `libstdc++` when Kafka is used) · `service-logging` · `service-tracing`.

## Example usage

- “Which libraries should this new Go service use?”
- “Replace the hand-rolled Redis client with the stack's.”
