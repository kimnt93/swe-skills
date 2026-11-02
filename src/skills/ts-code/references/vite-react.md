# Vite + React

Start from `assets/vite-react`: `src/api/client.ts` (the envelope client), `src/App.tsx` (a page
using React Query), Vitest + Testing Library, Playwright against `vite preview` on 127.0.0.1:3000.

## Rules

- **Server state with React Query:** one `useQuery` per resource with a stable `queryKey`; retry only
  `ApiError`s with `retryable: true`; mutations with `useMutation` and `invalidateQueries` on success.
- **Client state** stays local (`useState`, `useReducer`); lift it only as far as needed. A global store
  only for genuinely global UI state (theme, the signed-in user), never for API data.
- **Routing:** React Router with lazy routes for large pages.
- **Components** take typed props, render loading, empty and error states explicitly, and do no
  fetching except through hooks.
- **Env:** `import.meta.env.VITE_*` only, all public; set them at build time.
- **Dev proxy** instead of CORS in development: `server.proxy` in `vite.config.ts` to the Go API.
- Bind the dev and preview servers to `127.0.0.1:3000` (Playwright polls that address).
