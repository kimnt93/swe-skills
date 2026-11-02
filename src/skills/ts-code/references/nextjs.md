# Next.js (App Router)

Start from `assets/nextjs`: `app/layout.tsx`, `app/page.tsx` (a server component that calls the
API), `app/healthz/route.ts`, `lib/api.ts` (the envelope client), `lib/healthz.ts`, Vitest and
Playwright set up.

## Rules

- **Server components by default.** Fetch on the server with `serverClient()` (server-only
  `API_BASE_URL`, `cache: "no-store"` unless the data can be stale). Add `"use client"` only to the
  smallest component that needs state, effects or browser APIs.
- **Mark dynamic pages** `export const dynamic = "force-dynamic"` when they read per-request data, so
  `next build` doesn't freeze a request into static HTML.
- **Route handlers** (`app/**/route.ts`) are a backend-for-frontend only: proxying to the Go API with
  a server secret, setting cookies. Business logic stays in the Go service.
- **Errors:** catch `ApiError` where you fetch and render an error state; add `error.tsx` per segment
  for the unexpected; `not-found.tsx` for 404s.
- **Env:** server-only values without a prefix; public values `NEXT_PUBLIC_*` (compiled in at build).
- **`/healthz`** at the root in the api-contract shape (the template's route), on port 3000.
- **Images and fonts** through `next/image` and `next/font`; no layout shift.
- **Mutations:** server actions or a route handler that calls the API; revalidate with
  `revalidatePath` / `revalidateTag` after a successful write.
