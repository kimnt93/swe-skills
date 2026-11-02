---
name: api-contract
description: The HTTP API contract of the platform and how to refactor a service to it. Every API is versioned (/v1, /v2) with Swagger at /docs and one /healthz at the root that shows node, status, service name, env name, the served versions and non-secret config; internal callers send `x-internal-service-token` (plain or `Bearer`) plus `x-user-id` / `x-username`, and `GET /internal` is the token-protected health that shows the caller; it always listens on port 3000; the public host is {service_name}.{env_name}.{host} (account-api.stg.@DOMAIN@) and the Traefik Host rule is labelled with the service name. Use when creating an API, adding a version, adding or fixing healthz or Swagger docs, changing the port or host, or auditing and refactoring an existing API project (Go, Python, Rust, TypeScript) to this contract, with an audit script and a live probe.
metadata:
  group: platform
  version: "1.1"
---

# API contract

One shape for every HTTP API of the platform, so a person or a tool can find any service, its docs, its
versions and its health without reading its code. This skill holds the rules, the healthz template,
a static audit and a live probe. The language skills hold the tested implementations; the
[deployment-setup](../deployment-setup/SKILL.md) skill holds the Dockerfile, Swarm and Traefik files.

## The contract

| # | Rule | Concretely |
|---|---|---|
| 1 | **Versioned, always documented** | Business routes live under `/v1` (later `/v2`, `/v3`). Swagger UI is `/docs`, the spec `/docs/openapi.json`. At the root only `/docs` and `/healthz`. |
| 2 | **Traefik host is labelled with the service name** | `Host(` + `{service_name}.{env_name}.{host}` + `)`, built from the same variable as `SERVICE_NAME`. |
| 3 | **Port 3000, always** | The process listens on `PORT` (default `3000`), the Dockerfile `EXPOSE`s `3000`, Traefik's `loadbalancer.server.port` is `3000`. |
| 4 | **The env name is always present** | `ENV_NAME` (`stg`, `prod`, `dev`, `local`) is in the host, the environment and the healthz body. |
| 5 | **One `/healthz`, at the root** | Not per version: node, status, service name, env name, `api_versions`, non-secret config, dependency checks. |
| 6 | **Internal calls carry a token and a user** | `x-internal-service-token: <token>` or `Bearer <token>`; `x-user-id` and/or `x-username` say who it is for. |
| 7 | **`/internal` checks the internal path** | Token required; the `/healthz` body plus `caller`. `200` = up, token works, identity received. |

```text
account-api.stg.@DOMAIN@/docs               Swagger UI          (spec: /docs/openapi.json)
account-api.stg.@DOMAIN@/healthz            the one public health endpoint (lists v1, v2, ...)
account-api.stg.@DOMAIN@/internal           health + caller, needs x-internal-service-token
account-api.stg.@DOMAIN@/v1                 the v1 API
account-api.stg.@DOMAIN@/v2                 only when v2 exists
```

Details: [URL, port, env and versions](references/contract.md) · [healthz spec and template](references/healthz.md) · [internal calls and `/internal`](references/internal.md) ·
[Swagger docs](references/swagger-docs.md) · [refactor an existing API](references/refactor.md).

## Workflow

1. **New API**: scaffold with the language skill (its template already follows this contract), then
   [deployment-setup](../deployment-setup/SKILL.md) for the files that route it.
2. **Existing API (refactor)**: follow [refactor](references/refactor.md). Start with the audit:

   ```bash
   python3 scripts/audit_api.py path/to/service            # static: source, Dockerfile, compose, env files
   python3 scripts/probe_api.py http://127.0.0.1:3000 --service account-api --env local --token "$INTERNAL_SERVICE_TOKEN"
   python3 scripts/probe_api.py https://account-api.stg.@DOMAIN@ --versions v1
   ```

3. **Add a version**: copy the `/v1` group to `/v2`, add it to the version list (shown in
   `api_versions` by `/healthz`) and to the Swagger spec ([contract](references/contract.md#adding-v2)).
4. **Verify** with both scripts and the language tests; report what each one checked.

## Implementations (copy, do not re-invent)

| Stack | `/healthz`, docs and version wiring |
|---|---|
| Go (Fiber v3) | `go-code/assets/template/internal/interfaces/httpapi/{health.go,docs.go,server.go}`; spec by `make swagger` (swaggo) |
| Python (Litestar) | `py-code/assets/template/src/service/api/{versions.py,routes/health.py,app.py}`; spec built in |
| Rust (axum) | `rust-code/assets/template/crates/svc-api/src/{health.rs,docs.rs,app.rs}`; spec by utoipa |
| TypeScript / JavaScript | `assets/templates/typescript/healthz.ts` (framework neutral, tested by `smoke.ts`) |
| Next.js / Vite frontends | the `ts-code` templates: `app/healthz/route.ts` (Next.js), a static `healthz.json` (Vite, via `deployment-setup`) |

`/internal` and the token and user headers are in [internal calls](references/internal.md#implementations).

The body is fixed by [assets/healthz.schema.json](assets/healthz.schema.json); a full example is
[assets/healthz.example.json](assets/healthz.example.json).

## Do not

- Do not add `/v1/healthz`, `/v2/healthz`, `/readyz`, `/health` or `/livez`: health is the one root `/healthz`.
- Do not put secrets, DSNs, tokens or the raw environment in `config`, or exception text in `checks`.
- Do not require the service token on `/docs`, `/docs/openapi.json` or `/healthz`, and always require it on `/internal` and `/v1`.
- Do not trust `x-user-id` or `x-username` before the token check, and never log or echo the token.
- Do not publish a host port or listen on 8080/8000; Traefik reaches the container on 3000.
- Do not build the host from a different name than `SERVICE_NAME`, and never leave out the env label.

## Example usage

- “Use $api-contract to audit and refactor this Fiber service to the API contract.”
- “Use $api-contract to add /v2 to this Litestar service.”
- “Use $api-contract to check that account-api.stg.@DOMAIN@ follows the contract.”

## Frontends

Frontends (the `ts-code` skill) are callers of this contract: they generate their types from
`/docs/openapi.json`, call versioned `/v1/...` paths, unwrap the envelope in one client, and never
send `x-internal-service-token` from a browser. A frontend served as its own service also listens
on port 3000 behind `{service_name}.{env_name}.{host}` and answers `/healthz`.
