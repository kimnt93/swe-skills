# Architecture

<One paragraph: what the system does and for whom.>

## Components

| Component | Language | Responsibility | Owns (data) | Talks to |
|---|---|---|---|---|
| `<name>-api` | Go / Fiber | <the use cases it serves> | tables `<...>`, topic `<...>` | `<...>` |
| `<name>-ml` | Python | <training, inference> | bucket `<...>` | reads topic `<...>` |
| `<name>-core` | Rust | <the hot path> | — | called by `<...>` |
| `<name>-web` | Next.js / Vite + React | <the UI> | — | `<name>-api` `/v1` |

## Layers (inside each service)

`interfaces → application → domain`; adapters in `infrastructure` implement ports declared in
`application`; only the composition root (`bootstrap`, `cmd`, `api/app.py`) wires them. Enforced by
`make verify`: Go `archcheck`, Python `lint-imports`, the TypeScript lint.

## Interfaces

| Interface | Kind | Owner | Consumers | Contract |
|---|---|---|---|---|
| `/v1/<...>` | HTTP | `<name>-api` | `<name>-web` | OpenAPI at `/docs/openapi.json` |
| `<topic>.v1` | Kafka | `<producer>` | `<consumers>` | the message schema in `<path>` |

## Invariants

- <e.g. a fill is applied once, even when redelivered>
- <e.g. only the account service writes balances>

## Decisions

See `docs/adr/`. A change to this file needs an ADR in the same PR.
