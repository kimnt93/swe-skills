# Refactor an existing API to the contract

Work one repository at a time. The audit tells you what is wrong; fix by theme, run the tests, run
the probe. Do not rewrite business logic: this is routing, docs, health, port and deploy files.

## 1. Audit

```bash
python3 scripts/audit_api.py path/to/service        # FAIL = contract broken, WARN = look by hand
```

It reports by rule id: `PORT-1/2` (port), `HOST-1/2` (Traefik host and port label), `ENV-1`
(env name), `HEALTH-1/2/3` (health route, probes, body), `INT-1` (`/internal` and the token header), `DOCS-1`, `VER-1` (unversioned routes).
Read the project's own agent notes and deployment docs first; the audit does not know about
hand-written routers or non-Compose deploys.

## 2. Map old to new

| Today | Becomes |
|---|---|
| `GET /healthz` with a short body, `/health`, `/livez`, `/ping` | `GET /healthz` at the root with the full body |
| `GET /readyz`, `GET /v1/healthz` | folded into `/healthz` `checks` (503 when down); delete both |
| routes at `/items`, `/api/items`, `/api/v1/items` | `/v1/items` |
| `/swagger`, `/swagger/index.html`, `/api-docs`, `/redoc`, `/v1/openapi.json` | `/docs` and `/docs/openapi.json` |
| listen `:8080`, `:8000`, `HTTP_ADDR`, `HTTP_PORT` | `PORT` (default 3000) |
| host `orders-api.@DOMAIN@`, `api.stg...` | `orders-api.stg.@DOMAIN@` |
| `RUN_ENV` only | `ENV_NAME` set from it, healthz and host show it |

## 3. Code, in this order

1. **Config**: add `ENV_NAME` (order: `DEVELOPMENT_ENVIRONMENT`, `ENV_NAME`, `RUN_ENV`), `NODE_NAME`,
   `SERVICE_VERSION`, `PORT` default `3000`; a `public config` function returning the allowlist.
2. **Versions**: move every business route under a `/v1` group (keep handlers as they are). Keep the
   auth middleware on the group; `/healthz` and `/docs` stay at the root, outside it and public.
3. **healthz**: copy the stack's implementation ([healthz](healthz.md#implementations)), pass the identity and the
   dependency pings the old `/readyz` used. Delete `/readyz`, `/health`, `/livez` and any `/v1/healthz`, with their tests.
4. **Docs**: wire `/docs` and `/docs/openapi.json` ([swagger docs](swagger-docs.md)); annotate every handler;
   regenerate; add or keep the drift test.
4a. **Internal calls**: accept `x-internal-service-token` with or without `Bearer`, read `x-user-id` / `x-username` only after
   it passed, and add `GET /internal` ([internal](internal.md)). Replace any ad hoc `Authorization` or `x-api-key` service auth.
5. **Tests**: healthz fields and codes, `/internal` 401/200 and caller, the `Bearer` form, auth still enforced on `/v1`, old health paths gone, docs served.

## 4. Deploy files (deployment-setup)

- `Dockerfile`: `EXPOSE 3000`.
- Compose: `PORT: "3000"`, `ENV_NAME: ${RUN_ENV}`, `SERVICE_NAME` from the service-name variable,
  `loadbalancer.server.port=3000`, the `Host()` rule `{service}.{env}.{domain}`, `HEALTH_APP_PATH`
  default `/healthz`.
- `deploy/<plane>.env`: `PUBLIC_DOMAIN=@DOMAIN@` (and the env label comes from `RUN_ENV`).
- `scripts/health.sh`: take the current template (default path `/healthz`, port 3000).
- Re-run `python3 ../deployment-setup/scripts/check_deploy.py docker-compose.yaml --env-file deploy/stg.env --set RUN_ENV=stg ...`.

## 5. Callers and rollout

- **Find callers** of the old paths and old host (other services' env files and clients, Grafana or
  uptime checks, CI smoke tests, docs) and move them to `https://{service}.{env}.{domain}/v1/...`.
- If callers cannot move in the same release, keep the old routes as temporary aliases of `/v1`
  (never a second implementation), note the removal date in the repository, and probe with
  `--allow-legacy-health`. Remove them once the access log shows no traffic.
- Stage first, with the same image digest that will go to production. The image and the compose file
  ship together, so the container health check path and the route change in one rollout; a mixed
  state (new compose, old image) fails the health check and Swarm rolls back, which is the safe outcome.
- After the rollout: `python3 scripts/probe_api.py https://{service}.{env}.{domain}` for each env and
  record the result. Do not claim a rollout you did not verify.

## 6. Done when

- `audit_api.py` prints `0 FAIL` (every WARN reviewed or explained).
- `probe_api.py` prints `0 error(s)` against the local container and, after an authorized rollout, each environment.
- Language tests, lint and `check_deploy.py` pass; no `/readyz`, `/v1/healthz`, `8080` or `8000` is left in the repository.
