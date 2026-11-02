# Python tests

*Verified with: assets/template pass on Python 3.12 with pytest 9 against live infrastructure.*

Test behaviour at the lowest layer that can show it. Reference: `assets/template/tests`.

## Unit tests (default `pytest`, no infrastructure)

- **Parametrise** (`@pytest.mark.parametrize`) with readable ids; assert the observable result, not calls.
- **Fakes, not mock soup.** Ports are small Protocols; write a 10-line `FakeRepo`/`FakeEvents` in `conftest.py`. Use
  `unittest.mock` only for things you do not own.
- **Inject time, ids, randomness** (`now=lambda: ...`, `new_id=lambda: "id-1"`); use `freezegun` only where injection is not possible.
- **API tests** with `TestClient(create_app(settings, items_service=fakes))`: table of (request -> status, error `code`); also assert
  the generic 500 leaks nothing (`TestClient(app, raise_server_exceptions=False)`) and that auth runs before handlers.
- **Settings tests:** every secret is required by name (parametrise over them); `NAME_FILE` is read; secrets never appear in `repr`/`model_dump`;
  `.env.example` loads with dummy secrets and keeps them blank; SASL needs credentials. Clear variables the shell may set (`monkeypatch.delenv`).
- **Async:** `asyncio_mode = "auto"` (pytest-asyncio); `async def test_...`; never `asyncio.sleep` to wait for a result, await the
  event/queue with a timeout.
- **Data tests:** build tiny polars frames inline and compare with `polars.testing.assert_frame_equal`; test determinism (same input,
  same output), null handling and time zone, not just the happy path.
- A new safeguard needs a test that fails when the safeguard is removed.

## Integration tests (`-m integration`, excluded by default)

Real PostgreSQL, Redis and Kafka (never mocks) for SQL, locking, TTLs and consumers. They skip themselves when the
environment is not configured.

```bash
docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka rustfs   # deployment-setup template
scripts/health.sh --wait postgres,redis,kafka,s3                                    # same readiness gate as production
set -a; . ./.env; set +a
uv run pytest -m integration -o addopts="" -q
docker compose -f docker-compose.infra.local.yaml down -v
```

| Adapter | Assert |
|---|---|
| Postgres | goose Up applies; round trip; missing row raises the domain `NotFoundError`; `ON CONFLICT` upsert is idempotent; `SKIP LOCKED` claim |
| S3 / RustFS | put/get/list/delete round trip; a missing key raises `ObjectNotFoundError`; bucket health check |
| Redis | a second lock holder is refused; release frees it; TTL expires |
| Kafka | create/seed the topic first, then publish until the consumer receives it; key/value intact; commit after the handler |

Use unique names per run (`uuid` topics, keys, groups). A fresh single-node broker needs seconds: gate with `health.sh --wait`.
In-memory substitutes (`fakeredis`, `moto[s3]`) are fine for unit tests but never replace the integration run for
locking, TTL and delivery semantics.

## CI

`ruff format --check`, `ruff check` (PEP 8, 79 columns), `pycodestyle --max-line-length=79`, `pytest`, then the integration job on a runner with Docker; run in the same image the
Dockerfile builds (`uv sync --locked`). Coverage is a signal, not a goal: cover every rule and error path.

## Example usage

- “Add parametrised tests for the order validation rules.”
- “Write an integration test for the at-least-once Kafka consumer.”
