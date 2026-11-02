# API client

The Go services publish OpenAPI at `/docs/openapi.json` and answer every call with the envelope
`{success, status_code, message, data, error: {code, retryable}}` (the `api-contract` skill).

1. **Types:** `API_OPENAPI_URL=http://127.0.0.1:8080/docs/openapi.json npm run api:types` writes
   `schema.d.ts`. Commit it; regenerate when the API changes (a CI check can diff it).
2. **One client** per app (`createClient` in the templates): it sets `accept`, sends JSON, unwraps
   `data`, and turns `success: false`, a non-JSON body, or a network failure into `ApiError` with
   `status`, `code` and `retryable`. Components never parse the envelope.
3. **Paths are versioned:** call `/v1/...`; a breaking change is `/v2`, never a silent change.
4. **Auth:** browser → Next.js route handler or the API's public auth; the
   `x-internal-service-token` header is server-to-server only and must never reach the browser.
5. **Errors in the UI:** map `code` to a message the user can act on; show `retryable` errors with a
   retry action; log the rest to Sentry (`service-errors`).
6. **Money:** prices and amounts arrive as strings; display with `Intl.NumberFormat`; send them back
   unchanged.
