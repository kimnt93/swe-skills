# dev-gorouter

A demo project of agents around one upstream repo, `gorouter`, set up for a **developer** (mode dev): the agent reads or
creates the issue, codes, opens the PR and stops. You review and merge; there is no review agent and no merge step.

# Map

```yaml
repos:
  gorouter:
    role: Go HTTP router
    provides: [a Go HTTP router library]
    depends_on: []
    docs: docs/README.md
    verify: make test
external: {}
merge_order: [gorouter]
```

# Repos

- `gorouter/` (upstream: github.com/kimnt93/gorouter, a git submodule here): a multi-user LLM gateway in Go with a Vite UI.

# Dependencies

- Go 1.26, Node (the UI build), PostgreSQL and Redis for the full test suite (`TEST_DATABASE_URL`, `TEST_REDIS_URL`).

# Commands

- `make build` builds the UI and the binaries; `make test` runs `npm test` and `go test ./...` (needs Postgres and Redis).
- Without services: `go build ./...` and `go vet ./...`. The repo's own `AGENTS.md` and `skills/` apply inside it.

# Conventions

- Branch from `main`, Conventional Commits, a linked issue, one PR per task (the `github` skill).

# Gotchas

- `make test` needs the compose services (`make compose-postgres`); the demo task is a file-only change and needs neither.

# Decisions

- 2026-11-04: dev mode: the human reviews and merges every PR.
