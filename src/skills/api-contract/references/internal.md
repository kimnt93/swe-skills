# Internal calls and `/internal`

Services call each other with a shared service token and say which user they act for. Every API
reads the same headers and answers the same `/internal` check.

## Headers

| Header | Meaning | Rules |
|---|---|---|
| `x-internal-service-token` | the shared service secret | `<token>` **or** `Bearer <token>` (prefix case-insensitive, optional). Compared in constant time after the prefix is removed. Never logged, never echoed. |
| `x-user-id` | the user the call is made for | optional; trimmed, at most 128 characters |
| `x-username` | the same user's name | optional; trimmed, at most 128 characters |

- **Authenticate first.** `x-user-id` and `x-username` are read only after the token check passed; without
  a valid token they are ignored and the answer is `401` in the envelope
  (`{"success": false, "status_code": 401, "error": {"code": "unauthorized", ...}}`).
- A caller that has no user (a scheduler, a migration job) sends the token alone; the service sees `""`.
- The headers are identity as the calling service reports it, not proof of the user. Authorize with the
  id, never trust a username for access decisions, and log the id, not the token.
- `/v1/...` accepts the same token forms. The token comes from `INTERNAL_SERVICE_TOKEN` (or
  `INTERNAL_SERVICE_TOKEN_FILE`), never a default.

## `GET /internal`

At the root next to `/docs` and `/healthz`, not under `/v1`. It is the service health **for an internal
caller**: the `/healthz` body (same fields, same `200`/`503`, same checks, `Cache-Control: no-store`)
plus `caller`. A `200` proves three things at once: the service is up, the token works, and this is the
identity the service received.

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
  "config": {"port": 3000, "log_level": "info", "docs_url": "/docs"},
  "checks": [{"name": "postgres", "status": "ok", "latency_ms": 2.4, "error": ""}],
  "caller": {"user_id": "u-7", "username": "linh"}
}
```

Full example: [assets/internal.example.json](../assets/internal.example.json); schema:
[assets/internal.schema.json](../assets/internal.schema.json).

| Request | Answer |
|---|---|
| no token, or a wrong one | `401` envelope (never a body that hints at the expected value) |
| valid token, healthy | `200` body above |
| valid token, a required dependency down | `503`, `status: "down"`, short error codes only |
| valid token, no identity headers | `200`, `caller` is `{"user_id": "", "username": ""}` |

`/healthz` stays public and is what Swarm and load balancers probe. `/internal` is for services,
dashboards and operators holding the token (smoke test after a deploy, a client library checking its
configuration at start-up). It is documented in `/docs` with the `InternalServiceAuth` scheme.

Calling it:

```bash
curl -s https://account-api.stg.@DOMAIN@/internal \
  -H "x-internal-service-token: $INTERNAL_SERVICE_TOKEN" \
  -H "x-user-id: u-7" -H "x-username: linh"
python3 scripts/probe_api.py https://account-api.stg.@DOMAIN@ --token "$INTERNAL_SERVICE_TOKEN"
```

## Implementations

| Stack | Where |
|---|---|
| Go | `middleware/auth.go` (`InternalAuth`, `Caller`, `CallerFrom`), `health.go` (`InternalHealth`, `internalHandler`), route in `server.go` |
| Python | `api/deps.py` (`bare_token`, `require_internal_token`, `caller`, `CallerDep`), `routes/health.py` (`internal_router`) |
| Rust | `svc-api/src/internal.rs` (`bare_token`, `Caller`), `health.rs` (`respond_internal`), `app.rs` (`internal_health`, `auth`) |
| TypeScript / JS | `assets/templates/typescript/healthz.ts` (`bareToken`, `isInternalToken`, `callerFromHeaders`, `buildInternal`) |

Each template ships tests for: `401` without or with a wrong token, `200` with the caller echoed, an
empty caller without the headers, the `Bearer` forms, and `503` without leaked error text.
