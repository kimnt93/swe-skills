# URL, port, env and versions

## Host: `{service_name}.{env_name}.{host}`

| Part | Source | Example |
|---|---|---|
| `service_name` | `SERVICE_NAME` (lower case, hyphens; the stack's service name, usually ending `-api`) | `account-api` |
| `env_name` | `ENV_NAME`; set in Compose from the plane variable `RUN_ENV` (`stg`, `prod`, `dev`, `local`) | `stg` |
| `host` | `PUBLIC_DOMAIN` in `deploy/<plane>.env` (`@DOMAIN@`; `localhost` for local) | `@DOMAIN@` |

Good: `account-api.stg.@DOMAIN@`, `account-api.prod.@DOMAIN@`,
`account-api.local.localhost`. Bad: `account-api.@DOMAIN@` (no env), `api.stg.@DOMAIN@`
(not the service name), `stg-account-api.@DOMAIN@` (wrong order).

One router per service serves every path (`/docs`, `/v1`, `/v2`), so the Traefik rule is one `Host()`:

```yaml
deploy:
  labels:
    - traefik.enable=true
    - traefik.swarm.network=ingress-${RUN_ENV:?RUN_ENV is required}
    - traefik.http.routers.account_api_${RUN_ENV}.rule=Host(`${API_SERVICE_NAME:-account-api}.${RUN_ENV}.${PUBLIC_DOMAIN:?PUBLIC_DOMAIN is required}`)
    - traefik.http.routers.account_api_${RUN_ENV}.entrypoints=web
    - traefik.http.routers.account_api_${RUN_ENV}.service=account_api_${RUN_ENV}
    - traefik.http.services.account_api_${RUN_ENV}.loadbalancer.server.port=3000
```

The service-name variable is the same one that fills `SERVICE_NAME` and `OTEL_SERVICE_NAME`, so the
host, the logs, the traces and the healthz body name the service identically. Router and Traefik
service names are the service name with underscores, then the env (`account_api_stg`), written
literally because label names cannot hold hyphens by convention (see
[Traefik labels](../../deployment-setup/references/traefik-labels.md)).

## Port 3000

| Where | Value |
|---|---|
| process | listens on `0.0.0.0:${PORT:-3000}` (Go `PORT`, Python `PORT`, Rust `PORT`, Node `PORT`) |
| Dockerfile | `EXPOSE 3000` |
| Compose / Swarm | `PORT: "3000"`, `loadbalancer.server.port=3000`, no `ports:` on a routed service |
| `scripts/health.sh --app` | probes `http://127.0.0.1:${PORT:-3000}/healthz` |
| local compose | may publish `127.0.0.1:3000:3000` |

`PORT` exists for a local clash only; deployed services never override it.

## Env name

`ENV_NAME` is the one name used in the host, the environment, logs (`development_environment`) and
the healthz `env_name`. Resolution order in code, the same as the log format: `DEVELOPMENT_ENVIRONMENT`,
else `ENV_NAME`, else `RUN_ENV`, else `local`. Compose sets `ENV_NAME: ${RUN_ENV}` for every service.

## Paths

| Path | What | Auth |
|---|---|---|
| `/docs` | Swagger UI | none |
| `/docs/openapi.json` | OpenAPI document with every version | none |
| `/healthz` | health of the service, listing every version in `api_versions` | none |
| `/internal` | the same health plus the `caller`; see [internal](internal.md) | `x-internal-service-token` |
| `/v1/...` | the v1 API | the service's own (for example the internal token) |
| `/v2/...` | only when v2 exists | as v1 |

There is nothing else at the root: unversioned business routes, `/v1/healthz`, `/readyz`, `/swagger`,
`/api-docs` and `/redoc` do not exist. An unknown path answers the framework's 404 in the usual envelope.

## Versions

- A version is a URL prefix with its own routes, models and tests. Add `/v2` for a breaking change;
  keep `/v1` until its callers have moved, then remove the group and its spec paths together.
- Non-breaking additions (a new optional field, a new route) stay in the current version.
- Health is not versioned: the one `/healthz` lists every version in service in `api_versions`.
- The OpenAPI document covers all versions (paths are `/v1/...`, `/v2/...`); there is one `/docs`.

## Adding v2

1. Register a `/v2` group with its routes, below the same middleware order as `/v1`.
2. Add `"v2"` to the version list so `/healthz` shows it (`API_VERSIONS` in Python and TypeScript, `apiVersions` in Go, `health::API_VERSIONS` in Rust).
3. Annotate the new handlers so the spec lists them (Go: `@Router /v2/... ` lines, then `make swagger`; Rust: add to `ApiDoc` paths).
4. `python3 scripts/probe_api.py <url> --versions v1,v2`.
