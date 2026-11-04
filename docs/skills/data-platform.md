# Data, API and deployment skills

### db-migrations

**What it is.** PostgreSQL schema changes as goose SQL files, the default for every language. **Use it when**
you add or change a column, index or constraint, run a backfill, rename or drop, or wire the migration job.
**Say.** `/swe:db-migrations add a nullable status column to orders and index it`.

**What happens.**
1. Discover `schemas/`, the numbering and how the job runs.
2. Never edit a released file: a change is a new `NNNN_name.sql` with the next number.
3. Pick the change pattern from `safe-changes` first (most mistakes are the pattern, not the syntax).
4. Write the file with `-- +goose Up` first and a working `-- +goose Down` (or `-- irreversible: reason`).
5. Update the model in the same change (row struct, SQL constants, port, tests).
6. Verify: `check_migrations.py schemas`, then goose `up`, `down`, `up` on a disposable PostgreSQL.

**Safe by default.** New columns are `NOT NULL DEFAULT ...` (or nullable, backfilled, then tightened);
indexes on existing tables are `CREATE INDEX CONCURRENTLY` in a `-- +goose NO TRANSACTION` file; a rename or
drop uses expand and contract; destructive steps carry `-- destructive: reason`; one job runs the migrations
once per deploy, never from every replica. **Files.** `scripts/check_migrations.py` (with `--self-test`;
checks naming, contiguity, Up and Down, concurrent indexes, NOT NULL defaults, layout), `references/goose.md`,
`safe-changes.md`, `orm-tools.md`, `assets/templates/` (four tested examples).

### db-orm

**What it is.** The go-pg v10 ORM (Go only; other languages use raw SQL) (`pg.DB.Model`) for Go services, but only when asked or already present. **Use it when**
you say "use the ORM", or the project already uses it. Otherwise raw SQL on the same library stays. **Rules.** The ORM
lives only inside the adapter and implements the same port and table as the raw SQL adapter; `use_zero` on every written
column, no pointers; the schema belongs to goose files (no `orm.CreateTable`); no N+1, every list has a `LIMIT`, one
transaction per business operation, raw SQL stays available for queries the builder makes unreadable.
**References.** `orm-rules`, `go-pg` (go-pg v10.15); a live-tested adapter and zero-value test in `assets/go-pg`.

### data-pathway

**What it is.** Realtime pipelines with Pathway (Python code on a Rust engine): Kafka in, transforms, tumbling windows, joins, Kafka
or database out. **Use it when** you start or change a streaming pipeline that computes over events as they arrive. **Say.**
`/swe:data-pathway a pipeline that reads trades from Kafka and writes one-minute VWAP per symbol`.
**What you get.** A project template (`assets/template`): config from env, pure business logic in plain functions (tested with
pytest alone), thin Pathway wiring, persistence for restarts, a Dockerfile and compose file, and the shared `stream_pipeline_*`
OTel metrics (see **data-realtime-metrics**) with a Grafana dashboard (`assets/grafana-dashboard.json`, uid `pathway-pipelines`).
**References.** `pipeline`, `metrics`, `deploy`. **Honest limit.** The pure-logic tests ran; the Pathway tests need the
`pathway` package, which was not installed when this was written, so run them first.

### data-dagster

**What it is.** Batch and scheduled data pipelines as Dagster assets: daily partitions, asset checks that block bad data, jobs,
schedules, resources and backfills. **Use it when** data is produced on a schedule or on demand rather than per event.
**Say.** `/swe:data-dagster a daily asset of closing prices from Postgres with a row-count check`.
**What you get.** A project template (polars, PostgreSQL source, Docker, compose) whose tests run in process, `dagster_*` OTel
metrics exported by a sensor with bounded labels (job, asset), and a Grafana dashboard (uid `dagster-orchestration`) checked by
`scripts/check_dashboard.py`, which fails when the dashboard queries a metric the code does not emit.
**References.** `assets`, `metrics`, `testing`, `deploy`. **Honest limit.** The compose stack and Dockerfile were not run.

### api-contract

**What it is.** One shape for every HTTP API, so any service, its docs, versions and health can be found
without reading its code. **The seven rules.**

| # | Rule |
|---|---|
| 1 | business routes under `/v1` (later `/v2`); Swagger UI at `/docs`, the spec at `/docs/openapi.json`; at the root only `/docs` and `/healthz` |
| 2 | the Traefik host is `{service_name}.{env_name}.{host}`, built from the same variable as `SERVICE_NAME` |
| 3 | port 3000 everywhere (process, `EXPOSE`, load balancer port) |
| 4 | the env name (`stg`, `prod`, `dev`, `local`) is in the host, the environment and the healthz body |
| 5 | one `/healthz` at the root listing node, status, service, env, `api_versions`, non-secret config and dependency checks |
| 6 | internal calls send `x-internal-service-token` (plain or `Bearer`) plus `x-user-id` and/or `x-username` |
| 7 | `/internal` requires the token and returns the `/healthz` body plus the caller |

**Use it when** creating an API, adding a version, fixing healthz or Swagger, changing the port or host, or
auditing an existing API. **What happens.** For a new API, scaffold with the language skill (its template
already follows the contract) and route it with `deployment-setup`. For an existing API:
`audit_api.py <repo>` (static: source, Dockerfile, compose, env files), fix, then `probe_api.py <url>
--service <name> --env <env> --token ...` against the running service. **Files.** `scripts/audit_api.py`,
`scripts/probe_api.py`, `assets/healthz.schema.json` and `internal.schema.json` with examples, a TypeScript
healthz template, five references (contract, healthz, internal, swagger-docs, refactor).

### deployment-setup

**What it is.** The files that take a service from source to a running Swarm or Compose deployment.
**Use it when** you write or review a Dockerfile, Swarm `docker-compose.yaml`, the local compose file, plane
env files, Traefik labels, secrets or CI callers.

**What happens.**
1. Discover the contract from the repo: planes and triggers, the reusable deploy workflow's current inputs,
   ingress, hosts and placement, Compose vs Swarm, one image or several.
2. Write the files from `assets/templates/` (never another project's values): `Dockerfile.{go,python,node,rust}`,
   `Dockerfile.nextjs`, `Dockerfile.vite` with `nginx.spa.conf`, the Swarm and local compose files,
   `deploy/{stg,prod}.env`, workflows (`validate.yml` has the `verify` job to make required).
3. Verify with `scripts/check_deploy.py` and by rendering each plane (`docker stack config`).

**Rules.** The API contract for every HTTP service; one logical service name used for the Compose service,
`SERVICE_NAME`, `OTEL_SERVICE_NAME`, the network alias, the Traefik router stem and the log, metric and trace
identity; fail closed with `${VAR:?message}`; secrets are external versioned names mounted as `*_FILE`;
non-root images with pinned stages; a health-gate entrypoint that waits for infrastructure. **References.**
`dockerfile`, `swarm-compose`, `traefik-labels`, `ci-workflows`, `compose-and-ci`, `multi-service-pipelines`,
`infra-health`, `secrets`, `hosts-and-services`, `sources`.
