---
name: ts-code
description: "Write, change or review frontend TypeScript in this stack: Next.js (App Router) for server-rendered web apps, Vite + React + TypeScript for dashboards and internal SPAs; a typed API client from the Go service's OpenAPI with the response envelope, React Query for server state, strict tsconfig, ESLint, Vitest + Testing Library, Playwright end to end, and Docker images for both. Use for any frontend task: scaffold an app, add a page or component, call an API, fix a UI bug, write UI tests, or set up the frontend build and deploy."
metadata:
  group: language
---

# TypeScript frontends

One entry point for frontend work. Read this page, then the references that match the request.

## Which framework

| The app | Use | Template |
|---|---|---|
| public or SEO pages, server-side data fetching, a backend-for-frontend, auth on the server | **Next.js** (App Router) | `assets/nextjs` |
| a dashboard, an internal tool, a trading UI behind login, anything that is a single page app | **Vite + React** | `assets/vite-react` |

The backend is a Go/Fiber API (`go-code`); the frontend never talks to a database or Kafka directly.

## How to work

1. **Discover first:** `package.json`, the lockfile (npm or pnpm: keep the one the repo has),
   `tsconfig.json`, the router (`app/` or the React Router tree), the API client.
2. **Pick the topic** from the table below and read its reference.
3. **Types from the API:** generate them from the service's `/docs/openapi.json`
   (`npm run api:types`); never hand-write a response type the OpenAPI file already defines.
4. **Build inside out:** API types → the client call → a data hook or a server function → components
   → the page or route.
5. **Verify:** `npm run typecheck && npm run lint && npm test && npm run build`, then
   `npm run e2e` (Playwright) for anything a user can see. Report what ran.

## Which reference to read

| The request mentions | Read |
|---|---|
| new app, scaffold, versions, package manager, pins, tsconfig, ESLint | [stack](references/stack.md) |
| Next.js, App Router, server or client component, route handler, middleware, SSR, `NEXT_PUBLIC_` | [nextjs](references/nextjs.md) |
| Vite, SPA, React Router, React Query, client state, `VITE_` | [vite-react](references/vite-react.md) |
| calling the API, OpenAPI types, the envelope, errors, auth headers, CORS | [api-client](references/api-client.md) |
| tests, Vitest, Testing Library, Playwright, e2e, mocking the API | [testing](references/testing.md) |
| readability, components, hooks, naming, formatting, review | [readable-code](references/readable-code.md) |
| Dockerfile, deploy, `/healthz`, static hosting, env at build vs run time | [deploy](references/deploy.md) |
| logging, errors to Sentry, tracing in the browser | the `service-errors`, `service-logging`, `service-tracing` skills |

## Rules that always apply

- **Strict TypeScript:** `strict`, `noUncheckedIndexedAccess`; no `any`, no `@ts-ignore`
  (`@ts-expect-error` only with a reason); no non-null `!` on API data.
- **Server state lives in one place:** React Query (Vite) or server components and route handlers
  (Next.js). No copying API data into global client state.
- **The envelope is handled once,** in the API client: components get `data` or a typed `ApiError`
  with `code` and `retryable`, and render a real error state for it.
- **Money and quantities from the API are strings or integers;** never do arithmetic on prices in
  floating point in the browser. Format with `Intl.NumberFormat`.
- **Secrets never reach the browser:** only `NEXT_PUBLIC_*` / `VITE_*` values are public, and they
  are compiled in; anything secret stays on the server (route handlers, server components) or in the API.
- **Accessible by default:** semantic elements, labels on inputs, `getByRole` in tests.
- **Tested templates:** start from `assets/` instead of writing config from scratch; both pass
  typecheck, lint, unit tests, the production build and Playwright.
