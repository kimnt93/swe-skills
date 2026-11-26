Lane: backend
Wave: 1
Difficulty: medium (a middleware, its deployment settings and a load test; the limits need a decision)
Priority: medium

## Goal
An API client that sends too many requests gets a clear `429` answer that says when to retry, and the service stays
fast for everyone else.

## Read first
- `AGENTS.md`
- `ARCHITECTURE.md`
- `src/api/app.py`
- `deploy/compose.yaml`

## Scope (high-level)
- A limit per API key, set per environment.
- The answer when the limit is reached, and what a client can rely on.
- A test that shows the limit under load.
- Out of scope: limits per user or per route, and a dashboard.

## Depends on
- nothing strictly

## Done when
- `make verify`
- `make load-test`

## Notes
The architect's plan comment on this issue holds the approach, the package breakdown and the safety rules.

Created: CEO (example)
