# healthz

`GET /healthz` is the one health endpoint of a service, at the root next to `/docs`. It is not
versioned: it lists every API version in `api_versions`. It tells a person, a probe or a dashboard
which process answered, whether it is healthy, and how it is configured.

## Template (response body)

```json
{
  "status": "ok",
  "service_name": "account-api",
  "env_name": "stg",
  "node_name": "swarm-worker-1",
  "api_versions": ["v1"],
  "service_version": "1.4.2",
  "started_at": "2026-10-19T08:00:00Z",
  "checked_at": "2026-10-19T09:00:00Z",
  "uptime_seconds": 3600,
  "config": {
    "port": 3000,
    "log_level": "info",
    "docs_url": "/docs"
  },
  "checks": [
    {"name": "postgres", "status": "ok", "latency_ms": 2.4, "error": ""},
    {"name": "redis", "status": "ok", "latency_ms": 0.8, "error": ""}
  ]
}
```

The same file is [assets/healthz.example.json](../assets/healthz.example.json); the JSON Schema is
[assets/healthz.schema.json](../assets/healthz.schema.json) and `scripts/probe_api.py` enforces it.

## Fields

| Field | Meaning | Source |
|---|---|---|
| `status` | `ok` or `down` | `down` when any registered check fails |
| `service_name` | who this is; first label of the host | `SERVICE_NAME` |
| `env_name` | `stg`, `prod`, ...; second label of the host | `DEVELOPMENT_ENVIRONMENT`, `ENV_NAME`, `RUN_ENV`, else `local` |
| `node_name` | the Docker **host** running the task | `NODE_NAME` (Swarm `{{.Node.Hostname}}`), else the hostname |
| `api_versions` | every API version this process serves, never empty | the version list in code (`["v1"]`, `["v1", "v2"]`) |
| `service_version` | image tag or git sha, `""` when unknown | `SERVICE_VERSION` |
| `started_at`, `checked_at` | RFC 3339 UTC | process start, now |
| `uptime_seconds` | integer, never negative | now minus start |
| `config` | non-secret settings (see below) | an explicit allowlist in code |
| `checks` | one entry per required dependency, `[]` when none | the service's adapters |

## Rules

- **Status code**: `200` when `status` is `ok`, `503` when `down`. Nothing else.
- **Every field always present** (no omitted keys, no `null`): `checks` is `[]`, `service_version` is `""`.
  Same rule as the response envelope.
- **Not the envelope.** Probes and dashboards read this body directly, so healthz is the one
  documented exception to `{success, status_code, message, data, error}`.
- **Public and uncached**: no token, `Cache-Control: no-store`. Register it before the auth layer.
- **`config` is an allowlist.** It always has `port`, `log_level` and `docs_url` (`/docs`);
  add other non-secret keys on purpose (`postgres_host`, `kafka_consumer_group`, `tracing_detail`).
  Never a password, token, key, DSN, URL with credentials, or `os.environ` / `process.env`. The probe
  fails on a key that looks like a secret.
- **`checks` hold required dependencies only** (Postgres, Redis, Kafka a handler cannot work without).
  Each has a 2 second timeout and runs concurrently. `error` is `""`, `"timeout"` or `"unavailable"`
  and never the exception text; the cause goes to the log with the check name.
- **Cheap**: a check is a ping, not a query over data. Swarm calls it every 30 seconds per task.
- **One endpoint**: adding `/v2` adds `"v2"` to `api_versions`, not a second health route. Fields are
  only ever added, never removed.

## Internal variant

`GET /internal` returns this body plus `caller` behind the service token: [internal calls](internal.md).

## Implementations

| Stack | Where |
|---|---|
| Go | `go-code/assets/template/internal/interfaces/httpapi/health.go` (`Identity`, `Health`, `healthHandler`), wired in `server.go` (`app.Get("/healthz", ...)`, outside the `/v1` group), identity built in `cmd/api/main.go`, config in `internal/config/config.go` (`Public()`) |
| Python | `py-code/assets/template/src/service/api/routes/health.py` (`router()`), versions in `api/versions.py`, settings in `settings/__init__.py` |
| Rust | `rust-code/assets/template/crates/svc-api/src/health.rs` (`Check`, `Identity`, `API_VERSIONS`, `respond`), `Config::public()` in `svc-core` |
| TypeScript / JS | `assets/templates/typescript/healthz.ts`: `buildHealthz`, `identityFromEnv`; framework glue in its header |

Each template ships tests for: all fields present, `200` with no checks, `503` with a failing check
and no leaked error text, no `/v1/healthz` or `/readyz`, and (Go, Rust) every documented route exists.

## Container health check

`scripts/health.sh --app` (deployment-setup) probes `http://127.0.0.1:$PORT/healthz` and the
infrastructure in `HEALTH_DEPS`. Because healthz already checks dependencies, a `503` from it fails
the Swarm health check, which is the intent: an instance that cannot reach its database leaves the
load balancer.
