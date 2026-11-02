# Testing

| Level | Tool | What it proves |
|---|---|---|
| logic (API client, formatters, reducers) | Vitest | inputs → outputs, error mapping |
| components | Vitest + Testing Library (jsdom) | what the user sees for loading, data, empty and error states |
| the app | Playwright against the production build | real routing, rendering and network |

- Query by role and accessible name (`getByRole("button", { name: "Cancel" })`), never by CSS class.
- Mock the network at the edge: a fake `fetch` or client in unit tests; `page.route` in Playwright for
  SPA calls. Next.js server-side fetches can't be intercepted in the browser: point `API_BASE_URL` at a
  stub server, or test the degraded path as the template does.
- One behaviour per test; assert what the user sees (the **test-behavior-not-implementation** principle).
- A bug fix starts with a failing test at the cheapest level that shows it (the **tdd** skill).
- `npm run typecheck && npm run lint && npm test && npm run build && npm run e2e` is the frontend's
  `make verify`.
