# Infrastructure variables and health gate

A service that uses PostgreSQL, Redis, ClickHouse, Kafka or an S3-compatible store (for example
RustFS) must (1) receive that infrastructure through a fixed set of detailed variables, (2) wait for it
at start-up, and (3) keep checking it. Without the wait, a task starts, fails to connect, exits and is
restarted until the infrastructure happens to be up, which burns restart attempts and can trip
`failure_action: rollback`. Templates: `assets/templates/scripts/health.sh`, the `x-<infra>` blocks in
`docker-compose.yaml`, `docker-compose.local.yaml`, `deploy/*.env`, `.env.example` and
`docker-compose.infra.local.yaml` (a local copy of all five).

## Variable contract

Use these names exactly (the application, Compose, `.env.example` and `health.sh` all read them). Hosts,
users, databases and buckets are **required** (`${VAR:?message}`); ports default to the standard port;
**passwords and keys have no default, ever**: required variables in local files, mounted secrets read through
`*_FILE` in Swarm.

| Infra | Variables | Secrets (never defaulted) |
|---|---|---|
| PostgreSQL | `POSTGRES_HOST`, `POSTGRES_PORT`(5432), `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_SSLMODE` | `POSTGRES_PASSWORD[_FILE]` |
| Redis | `REDIS_HOST`, `REDIS_PORT`(6379), `REDIS_DB`(0), `REDIS_USERNAME` (optional ACL user) | `REDIS_PASSWORD[_FILE]` |
| ClickHouse | `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`(9000 native), `CLICKHOUSE_HTTP_PORT`(8123), `CLICKHOUSE_DB`, `CLICKHOUSE_USER` | `CLICKHOUSE_PASSWORD[_FILE]` |
| Kafka | `KAFKA_BOOTSTRAP_SERVERS` (`host:port,host:port`), `KAFKA_SECURITY_PROTOCOL`(PLAINTEXT), `KAFKA_SASL_MECHANISM`, `KAFKA_SASL_USERNAME`, `KAFKA_CONSUMER_GROUP` | `KAFKA_SASL_PASSWORD[_FILE]` (required for `SASL_*`) |
| S3 / RustFS | `S3_ENDPOINT` (`http[s]://host:port`), `S3_REGION`, `S3_BUCKET`, `S3_FORCE_PATH_STYLE` | `S3_ACCESS_KEY[_FILE]`, `S3_SECRET_KEY[_FILE]` |

Rules:

- Add only the blocks the service uses; keep the application's own configuration names if the project
  already has an established set, and map them in one place.
- Non-secret plane values (`POSTGRES_HOST`, `S3_BUCKET`, ...) live in `deploy/<plane>.env`; a committed env
  file never contains a password, key or token.
- In Swarm each secret is external, versioned and explicitly named (`<purpose>_${RUN_ENV}_v1`), attached
  only to the services that read it, mounted under a stable path and passed as `<VAR>_FILE`. The application
  (or its wrapper) must implement `_FILE`; a variable ending in `_FILE` does not read itself.
- Local Compose uses the plain variable (`POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?...}`) and `.env.example`
  lists secrets with **blank** values and a comment saying they are required.
- Each service lists the infrastructure it uses in `HEALTH_DEPS` (`postgres,redis,s3`); the checker flags a
  service that uses an infra variable but does not list it, and the reverse.

Each language skill implements this contract with a tested adapter and its own env example: Go [postgres](../../go-code/references/postgres.md) ·
[redis](../../go-code/references/redis.md) · [kafka](../../go-code/references/kafka.md) · [s3](../../go-code/references/s3.md); Python
[postgres](../../py-code/references/postgres.md) · [redis](../../py-code/references/redis.md) · [kafka](../../py-code/references/kafka.md) ·
[s3](../../py-code/references/s3.md); Rust [env-config](../../rust-code/references/env-config.md). All read the variables above from the environment,
take secrets from `NAME` or `NAME_FILE`, and have no default for a password or key.

## `health.sh`

```bash
health.sh postgres,clickhouse,kafka     # one-shot: exit 0 only if every dependency answers
health.sh                               # dependencies from $HEALTH_DEPS
health.sh --app                         # own HTTP endpoint ($PORT, $HEALTH_APP_PATH=/healthz, $PORT=3000) + $HEALTH_DEPS
health.sh --wait -- /app/service serve  # start-up gate: retry until ready (HEALTH_WAIT_SECONDS=120), then exec
```

Dependencies: `postgres`, `redis`, `clickhouse`, `kafka`, `s3` (aliases `rustfs`, `minio`). Exit codes: `0`
healthy, `1` unreachable or wait timed out, `2` configuration error (a required variable, including any
password, is missing or its `_FILE` unreadable; no retry, fails immediately and names the variable, never the value).

What each check proves (reachability and protocol liveness, not authorization):

| Dependency | Probe |
|---|---|
| postgres | TCP + `SSLRequest` answered with `S`/`N` (no credentials sent) |
| redis | `AUTH` (password, optional username) then `PING` → `+PONG`; a rejected password is reported |
| clickhouse | HTTP `GET /ping` on `CLICKHOUSE_HTTP_PORT` → 200 |
| kafka | TCP connect to any host in `KAFKA_BOOTSTRAP_SERVERS` |
| s3 | HTTP `GET $S3_HEALTH_PATH` (default `/health`) → 2xx; `https` endpoints get a TCP check. Set `S3_HEALTH_PATH` for the store in use |

Deeper checks (valid Postgres login, topic exists, bucket exists) belong to the application, which must fail
closed at start-up; `health.sh` only keeps it from starting before the infrastructure can answer.

### Wire it in

- **Image**: copy `scripts/health.sh` (executable) and set
  `ENTRYPOINT ["/app/scripts/health.sh","--wait","--","/app/service"]`, `CMD ["serve"]`. The gate `exec`s the
  application, so it stays PID 1 and receives `SIGTERM`. It is a no-op when `HEALTH_DEPS` is empty. It needs
  `bash` in the runtime image (present in Debian/Python/Node slim; not in distroless: use the application's
  own wait logic or a dedicated init stage there).
- **Compose healthcheck**: HTTP services `["CMD","/app/scripts/health.sh","--app"]`; workers and consumers
  `["CMD","/app/scripts/health.sh"]`. Set `start_period` to at least `HEALTH_WAIT_SECONDS` plus the
  application's start-up so the gate is not killed by its own health check.
- **Policy choice**: infra in the healthcheck means Swarm replaces tasks when a dependency is down. That is
  right for tasks that cannot self-heal reconnects; for applications that reconnect and serve degraded
  traffic, check `--app` only (drop infra from the check, keep it in the entrypoint gate) so a brief
  database outage does not trigger a restart storm. State the choice in the service notes.
- **One-shot jobs** (migrations) use the same gate as entrypoint and `restart_policy: none`.
- **Several services** share one image: the entrypoint gate reads each service's own `HEALTH_DEPS`.

## Verify

Run `scripts/check_deploy.py` (variables complete, no secret defaults, no secret in env files, `HEALTH_DEPS`
consistent). Start the infrastructure (`docker-compose.infra.local.yaml`), run `health.sh <deps>` against it,
then check the failure paths: stop a dependency (exit 1, container waits without restarting), omit a password
(exit 2, immediately), wrong Redis password (reported), unreadable secret file (names the file). Confirm PID 1
is the application and that `docker stop` exits within `stop_grace_period`.

## Example usage

- “Add Postgres, Redis and Kafka variables and the start-up wait to this service.”
- “Why does this service restart before the database is up?”
