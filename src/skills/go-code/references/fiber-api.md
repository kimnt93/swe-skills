# Fiber API

*Verified with: fiber v3.5 with sonic 1.15 (see assets/template).*

Reference implementation: `assets/template/internal/interfaces/httpapi`. Handlers are thin: parse,
call one use case, answer. Business rules live in `internal/domain` and `internal/application`.

## Where things live

| Piece | Path |
|---|---|
| App assembly: middleware order, docs, versions, routes (the only route table) | `httpapi/server.go` |
| `/healthz` | `httpapi/health.go` |
| Swagger UI `/docs` and `/docs/openapi.json` (embedded spec) | `httpapi/docs.go`, `httpapi/openapi/swagger.json` |
| Envelope, error mapping, ErrorHandler | `httpapi/api/response.go` |
| Handlers + Swagger comments | `httpapi/handlers/` |
| Middleware | `httpapi/middleware/` |
| JSON contract types | `internal/models/` |

## Rules

1. **Thin handlers.** Bind -> `h.Svc.X(c.Context(), ...)` -> `api.SendResponse(c, status, data, err, msg)`. No SQL, no
   rule checks, no `time.Now()`. `c.Context()` is the request `context.Context`; never pass the fasthttp
   `c.RequestCtx()` to services.
2. **One envelope** `{success, status_code, message, data, error:{code, retryable}}` with every field always present (no
   `omitempty`, no pointers: `data` is `null` and `error` is `{"code":"","retryable":false}` when unused). Business errors are
   `*apperr.Error` (status + stable `code` + safe message); sentinels map in `api.Map`; anything else is logged and
   returned as a generic 500. Error codes are an API contract: add, never rename.
3. **Request values die with the request.** `c.Params`, `c.Get`, `c.Query`, `c.Body` alias recycled buffers: `strings.Clone`
   before storing in `Locals` or passing to a goroutine. Prefer no goroutines in handlers.
4. **Middleware order** (set in `server.go`): request log (wraps everything, sees the final status) -> CORS/tracing ->
   auth (shared token, constant-time compare) -> identity -> ownership (foreign resources are 404, never 403) -> handler.
   Authenticate before trusting any identity header; never log tokens.
5. **Binding and validation.** Bind into a concrete type from `models`; unknown fields are not an error, so validate
   in the domain/use case and normalise there (trim, upper-case). Query params: parse, range-check, 400 on bad input.
6. **Status codes.** 400 malformed/invalid field, 401 auth, 404 missing or not yours, 409 state conflict, 422 business
   rejection, 429/502/503/504 retryable (`retryable: true`), 500 unexpected.
7. **JSON structs are plain values** without `omitempty` or pointers: a zero value is serialised, so clients never branch on
   absence. Fiber's `JSONEncoder`/`JSONDecoder` are set to `sonic` in the template; remove both lines to fall back to
   the standard library. Keep response structs flat and typed; never return `map[string]any` from domain code.
8. **Swagger at `/docs`.** Every handler has swaggo annotations (`@Summary @Tags @Security @Param @Success @Failure @Router`);
   regenerate with `make swagger` after any route or model change and commit `openapi/swagger.json`;
   `TestSwaggerListsEveryRoute` fails when a route is missing. Port, versions, healthz and host: the
   [api-contract](../../api-contract/SKILL.md) skill (`/v1/...` behind the auth middleware, `/healthz` and `/docs` at the root outside it, port 3000).
9. **Timeouts and shutdown.** Read/Write timeouts and `BodyLimit` in `fiber.Config`; `app.ShutdownWithTimeout(15*time.Second)`
   on SIGTERM; long work does not belong in a request (enqueue it).
10. **Observability.** Log one line per request with the route template (`/v1/items/:id`), not the raw path; add the
    OpenTelemetry middleware from `service-tracing` after CORS; propagate `c.Context()`.

## Testing

```go
res, err := app.Test(httptest.NewRequest("POST", "/v1/items", body),
    fiber.TestConfig{Timeout: 5 * time.Second, FailOnTimeout: true})
```

Table-test every status and error code through `app.Test` with fakes for the ports (`server_test.go` in the template).
Use the integration suite only for SQL, locking and cross-process behaviour ([test](test.md)).

## Example usage

- “Add a PATCH /v1/items/:id endpoint with validation and Swagger docs.”
- “Why does this handler return a corrupted id after the request?” (buffer lifetime)
