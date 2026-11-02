# Swagger docs

Every API serves **Swagger UI at `/docs`** and the **OpenAPI document at `/docs/openapi.json`**. Both
are public, both cover every version (`/v1/...`, `/v2/...`) and `/healthz`, and the
document is generated from the code, never hand written, so it cannot drift.

| Stack | How `/docs` is served | How the document is produced |
|---|---|---|
| Litestar (Python) | `OpenAPIConfig(path="/docs", render_plugins=[SwaggerRenderPlugin()])` (UI at `/docs`, document at `/docs/openapi.json`) | built from the routes and the msgspec `Struct`s at start-up |
| Fiber (Go) | `docs.go`: Swagger UI page from a pinned CDN version + `/docs/openapi.json` from an embedded file | `make swagger` (swaggo `swag init`) writes `internal/interfaces/httpapi/openapi/swagger.json`; commit it. `TestSwaggerListsEveryRoute` fails when a route is missing |
| axum (Rust) | `docs.rs`: the same UI page + the document from `ApiDoc::openapi()` | `utoipa`: a `#[utoipa::path]` on each handler, listed in `ApiDoc` `paths(...)`; a test fails when a documented route does not exist |
| Node | `@fastify/swagger` + `@fastify/swagger-ui` with `routePrefix: "/docs"`, or `swagger-ui-express` mounted at `/docs` with the generated spec at `/docs/openapi.json` | generated from route schemas (Fastify) or `swagger-jsdoc` (Express) |

Rules:

1. **Document every route**, including `/healthz`. Summary, tag, request body,
   response codes (`2xx`, `401`, `404`, `422`, `503` for healthz) and the security scheme.
2. **One security scheme** named after the real mechanism (`InternalServiceAuth`, header
   `x-internal-service-token`), applied to `/v{N}` business routes and `/internal`, and not to `/healthz` or `/docs`.
3. **Tags per resource**, plus `health`.
4. **Pin the Swagger UI assets** (`swagger-ui-dist@5.17.14` from jsdelivr in the templates); do not
   use `latest`. A service that must not reach a CDN vendors the files and serves them under `/docs/`.
5. **Regenerate with every route or model change**; the language test is the guard, review is the backstop.
6. `/docs` is behind the same Traefik router as the API: no strip-prefix middleware, so the UI's
   `url: "/docs/openapi.json"` is correct on `account-api.stg.@DOMAIN@`.

Check a running service: `python3 scripts/probe_api.py <url>` fetches `/docs` and `/docs/openapi.json`,
requires `/healthz` and `/internal` in the document, and flags any path in it that is neither of those nor versioned.
