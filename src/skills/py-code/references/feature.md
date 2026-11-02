# Python feature

Read the code around the change first (one sibling per layer) and write what reads like it. Work inside-out so each
layer is tested before the next depends on it.

## Order of work

1. **Contract.** Inputs, outputs, error cases, idempotency, concurrency (several replicas), money/time/units. Cite external
   rules (market, regulation) in a comment.
2. **Domain** (`domain/`): the rule as pure code (frozen dataclass or function), a typed exception for each business failure (names end in `Error`),
   unit tests with `pytest.mark.parametrize`. No I/O, logging or clock reads (pass `now`).
3. **Application** (`application/`): the use case and, if it needs I/O, a **Protocol port declared where it is used**. Flow and
   validation here, not SQL. Test with hand-written fakes (`FakeRepo`).
4. **Adapter** (`db/`, `messaging/`): implement the port with plain parameterised SQL (psycopg) / redis / confluent-kafka;
   schema change = a new goose file in `schemas/` (never edit a released one). Writes are idempotent (`ON CONFLICT`).
5. **API** ([litestar-api](litestar-api.md)): msgspec schemas, a thin route with an explicit `NamedDependency`, register the
   new domain exception in the handlers, `responses=` for documented errors.
6. **Composition:** wire the adapter in the lifespan/`app.py` only.
7. **Tests** ([test](test.md)): domain parametrised, use case with fakes, `TestClient` for the endpoint, and
   an `integration` test when SQL, locking, Redis or Kafka behaviour is involved. A new safeguard needs a test that fails
   without it.
8. **Data work** ([data](data.md)): messages as `msgspec.Struct`, frames as polars expressions, UTC timestamps.
9. **Observability and docs:** structured log with identity fields only; dependency spans for new outbound calls; settings
   documented in `.env.example` and the deployment variables.

## Cross-cutting checks

- Nothing blocking inside `async def`; DB/Redis/HTTP are async clients, CPU work leaves the loop.
- Errors are typed; no bare `except`; no secrets or payloads in messages; `raise ... from None` only to hide a driver detail.
- Replicas are concurrent: "do once" needs a database/Redis claim, not a module-level flag.
- New dependency? Check [stack](stack.md) first.

## Verify

```bash
uv run ruff format --check src tests && uv run ruff check src tests    # PEP 8, 79 columns
uv run pytest
uv run pytest -m integration -o addopts=""      # when SQL / Redis / Kafka behaviour changed (real infrastructure)
```

## Example usage

- “Add cancel-order: domain rule, use case, Postgres update with SKIP LOCKED, endpoint and tests.”
- “Add a Kafka consumer that upserts ticks and is safe to replay.”
