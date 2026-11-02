# Frontends (Next.js, Vite + React)

The same six rules apply in the browser, with the browser SDK.

| App | SDK | Where |
|---|---|---|
| Next.js | `@sentry/nextjs` | `instrumentation.ts` (server) and `instrumentation-client.ts` (browser) |
| Vite + React | `@sentry/react` | `src/main.tsx`, before `createRoot` |

- **The DSN is the only switch:** `NEXT_PUBLIC_SENTRY_DSN` / `VITE_SENTRY_DSN` (public by nature);
  empty means nothing is sent.
- **Identity:** `environment` = the env name, `release` = `<service_name>@<version>` (a build arg),
  tag `service_name`.
- **Nothing private:** `sendDefaultPii: false`; drop breadcrumbs and request bodies in `beforeSend`;
  no user objects beyond an opaque id; no session replay.
- **Errors only:** report the React error boundary and unhandled rejections; an `ApiError` the UI
  already handles (shown to the user) is not an event; an unexpected one is, with its `code`.
- **Telemetry stays separate:** `tracesSampleRate: 0` unless browser tracing is set up through the
  `service-tracing` skill.
- Upload source maps in the release build so stack traces map to source; never serve them publicly.
