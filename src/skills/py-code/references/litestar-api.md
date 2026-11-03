# Litestar API

*Verified with: Litestar 2.25, msgspec 0.22 (see assets/template). **No pydantic, no FastAPI**: FastAPI cannot run without pydantic.*

Code follows PEP 8 (79 columns, `ruff` + `pycodestyle`; see [stack](stack.md)).

Reference: `assets/template/src/service/api/`. Routes are thin: validate, call one use case, answer.
Business rules live in `domain/` and `application/`.

## Rules

1. **App factory + lifespan.** `create_app(settings=None, *, items_service=None, checks=None)`; production builds adapters in
   the `lifespan` and stores them on `app.state`; tests pass fakes. Routes never construct adapters or read env.
   Serve with `uvicorn service.api.app:create_app --factory --proxy-headers`. Do not name a state attribute like a
   `State` method (`items`, `keys`, `get`: use `use_cases`).
2. **Models are `msgspec.Struct`s** (`api/schemas.py`): requests, responses, health, the envelope. Constraints live in the
   type (`Annotated[str, Meta(min_length=1, max_length=64)]`; an optional constrained value is
   `Annotated[str, Meta(...)] | None`, never `Annotated[str | None, Meta(...)]`). A generic `Page[T]` breaks Litestar's schema
   (PEP 695 names); write one small class per list (`ItemsPage`). Rename a keyword field with `rename={"return_": "return"}`.
   A mutable default is a `msgspec.field(default_factory=...)`, a Struct default needs `frozen=True`.
3. **Parameters are explicit:** `FromPath[str]`, `FromQuery[int]`, `JSONBody[Model]`, `NamedDependency[Items]`;
   path templates carry the type (`/v1/items/{item_id:str}`). Auth is a router-level **guard** (`guards=[token_guard]`), so a
   route cannot forget it.
4. **One envelope** `{success, status_code, message, data, error:{code, retryable}}` through `envelope.ok/failure`; every field is
   always present (`data` is `null`, `error` is `{"code": "", "retryable": false}` when unused). Business errors are
   `ApiError(status, code, message)`; **register each domain exception type** in `exception_handlers`, plus
   `HTTPException` (the framework's 400/404/405) and `Exception` (log the cause, generic 500, never its message). Codes are a
   contract: add, never rename. A service that answers RFC 9457 problems does the same with `application/problem+json`.
5. **Edge validation by msgspec**, rules in the domain. Malformed body or wrong type -> 400 `invalid_request` (or the
   service's 422 problem); rule violation -> 422 `validation_error`; missing/foreign resource -> 404; conflict -> 409;
   auth -> 401. Cap sizes (`Meta(max_length=...)`, a body-size middleware). When a route must answer 415, 400 and 422 in a
   fixed order or list every problem at once, read `await request.body()` and validate by hand (`msgspec.convert`).
6. **Async discipline.** Everything in `async def` is non-blocking: async clients (psycopg `AsyncConnectionPool`, redis
   asyncio, httpx.AsyncClient). A blocking route is a plain `def` with `sync_to_thread=True` (it runs in the thread pool);
   blocking work inside an async route goes through `await litestar.concurrency.sync_to_thread(fn, ...)`. A **generator
   dependency runs on the event loop** and is cleaned up after the response: open a database transaction inside the
   route (`with db.session() as s:`) so it commits before the response, and never in a generator dependency.
7. **Fast responses.** Return Structs: Litestar encodes them with msgspec (no dict round trip, no pydantic). Stream big
   results (`litestar.response.Stream`) instead of building them in memory.
8. **API contract.** Routes live under `/v1` (`API_VERSIONS` in `api/versions.py`); Swagger is `/docs` with the document at
   `/docs/openapi.json` (`OpenAPIConfig(path="/docs", render_plugins=[SwaggerRenderPlugin()])`); `routes/health.py` serves the
   one root `/healthz` (all versions) without the token; the port is `PORT` (default 3000). See the
   [api-contract](../../api-contract/SKILL.md) skill.
9. **Auth and identity.** Shared token compared with `hmac.compare_digest`; never log it; authenticate before trusting
   identity headers; foreign resources are 404, never 403.
10. **Middleware** is pure ASGI. One request-log middleware writing the route **template**
    (`scope["path_template"]`: `/v1/items/{item_id}`), status, duration; OpenTelemetry
    (`litestar.plugins.opentelemetry.OpenTelemetryInstrumentationMiddleware`, `service-tracing`) outermost, and the log
    middleware renames the server span to the template. No business logic in middleware.
11. **Lists** are bounded (`Annotated[int, Parameter(ge=1, le=500)] = 100`, `offset`/cursor); sort order is explicit.
12. **OpenAPI** (served at `/docs`) is the contract: return annotations and `responses={404: ResponseSpec(Model, ...)}`
    on every route, tags, `Meta(description=..., examples=[...])` on fields. A body the route reads itself is added to the
    document after the app is built.
13. **Shutdown:** uvicorn `timeout_graceful_shutdown=15`; the lifespan closes pools and drains the producer.

## Testing

`litestar.testing.TestClient(create_app(Settings(), items_service=svc_with_fakes))`; parametrise status + error `code`; assert
the generic 500 leaks nothing (`raise_server_exceptions=False`). Use `-m integration` for real SQL/locking. See [test](test.md).

## Example usage

- “Add `PATCH /v1/items/{id}` with validation, a 409 conflict and tests.”
- “Why does this route return 500 instead of 422 for a domain error?” (unregistered exception type)
