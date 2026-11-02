# Python stack

*Verified with: Python 3.12, Litestar 2.25, msgspec 0.22, psycopg 3.3, redis-py 8, confluent-kafka 2.15, boto3 1.36+ against RustFS, msgspec 0.22, orjson 3.12, ciso8601 2.3, ruff 0.16 and pycodestyle (79 columns); polars/pandas benchmarks in py-data.*

One stack keeps services reviewable and skills small. Use these unless the project already has a working different
choice (then follow the project, and never mix two libraries for one concern in one service). Versions are those
tested, not pins: the project's `uv.lock` decides.

| Concern | Library | Why / rule |
|---|---|---|
| Interpreter | Python 3.12-3.13 (`requires-python = ">=3.12,<3.14"`) | type hints on public functions |
| Packaging | `uv` + `hatchling`, `uv.lock` committed, `uv sync --locked` in CI/Docker | reproducible installs |
| Code style | **PEP 8**: `ruff format` + `ruff check` with `E W F I N UP B SIM ASYNC`, **79 columns**, verified by `pycodestyle` | one tool, no black/isort/flake8 (see "PEP 8 rules") |
| API | `litestar` + `uvicorn[standard]` (uvloop, httptools) | thin routes, one envelope, msgspec models ([litestar-api](litestar-api.md)) |
| Edge validation | `msgspec` (`Struct`, `Meta` constraints, `convert`) | API boundary and messages; **never pydantic** |
| Settings | a keyword-only dataclass loaded from `os.environ` (msgspec converts the text) | `assets/template/src/service/settings/_base.py`; secrets are a `Secret` type |
| Hot-path decode/encode | `msgspec` (typed `Struct`), `orjson` (dict JSON, rarely) | 3-12x faster than stdlib `json` ([data](data.md)) |
| Timestamps | `ciso8601` in hot loops; `datetime.fromisoformat` elsewhere (3.11+) | UTC everywhere; never `strptime` per row |
| DataFrames | `polars` (lazy API, expressions); `pyarrow` for interchange; `numpy` | **not pandas**: no row-wise `apply` |
| PostgreSQL | `psycopg[binary,pool]` (v3), plain parameterised SQL | no ORM unless the repo already has one ([postgres](postgres.md)) |
| Migrations | `goose` SQL files in `schemas/` run as a one-shot job | immutable once released |
| Redis | `redis` (asyncio client) | locks, caches, wake-ups ([redis](redis.md)) |
| Kafka | `confluent-kafka` (librdkafka) | idempotent producer, manual-commit consumer ([kafka](kafka.md)) |
| ClickHouse | `clickhouse-driver` (native) or `clickhouse-connect` (HTTP) | batch inserts |
| Object store (S3/RustFS) | `boto3` (`aioboto3` if async) | `S3_ENDPOINT`, path-style ([s3](s3.md)) |
| Background jobs | `celery[redis]` | tasks carry ids and `traceparent`, not payloads ([worker](worker.md)) |
| HTTP client | `httpx` | timeouts always |
| Logging | `jlogger` via the `service-logging` skill | unified JSON, `trace_id`/`span_id` |
| Tracing / metrics | OpenTelemetry via `service-tracing`, `data-realtime-metrics` | |
| Streaming transforms | `pathway` (pinned) where the project already uses it | stateful pipelines with persistence |
| Tests | `pytest`, `pytest-asyncio`, `TestClient`, `fakeredis`, `moto[s3]`, `freezegun`; `-m integration` | ([test](test.md)) |

## PEP 8 rules (enforced, not advisory)

- **Layout:** 4-space indents, **79 columns** for code, comments and docstrings (`line-length = 79` in `pyproject.toml`), two blank
  lines around top-level definitions, one import per line, imports grouped standard library / third-party / local (ruff `I`).
- **Names:** `snake_case` functions, methods and variables; `CapWords` classes; `UPPER_CASE` constants; `_leading` for internals;
  **exception classes end in `Error`** (`NotFoundError`, `InvalidNameError`: ruff `N818`); modules short and lower-case.
- **Practices:** compare with `is None`, not `== None`; no bare `except:`; no mutable default arguments; no wildcard imports;
  no lambda assigned to a name; `isinstance` over `type() ==`; f-strings for formatting; type hints on public functions.
- **Docstrings (PEP 257):** triple double quotes; a one-line summary ending in a period, imperative mood for functions; wrap at 79.
- **Readable layout:** one statement per line, a condition has at most two operands, a function fits one screen (ruff `C901`, `PLR09xx`), SQL constants are
  multi-line triple-quoted strings. PEP 8 is the minimum, not the goal: see [readable-code](readable-code.md) for bad/good examples.
- **Tooling:** `uv run ruff format src tests`, `uv run ruff check src tests`; CI also runs `pycodestyle --max-line-length=79` (the
  reference PEP 8 checker) so the style never depends on one tool. Vendored files (for example `service_logging.py`) are excluded
  from lint and updated at their source.

## Rules

- **Config** only in `settings.py` (a dataclass loaded from the environment, no pydantic), names from the infrastructure contract (`POSTGRES_*`, `REDIS_*`,
  `KAFKA_*`, `S3_*`), secrets as `Secret` read from `NAME` or `NAME_FILE`; **no defaults for passwords**; every infra
  skill ships its own `.env.example` and settings module.
- **async is a contract:** nothing blocking in `async def` (no `requests`, `time.sleep`, sync DB, pandas on big frames).
  Use async clients, `run_in_executor` / `litestar.concurrency.sync_to_thread`, or a plain `def` route with `sync_to_thread=True`.
- **Typed boundaries:** `msgspec.Struct` at the API edge and for messages (never pydantic), dataclasses (`slots=True, frozen=True`) for
  domain values. No `dict[str, Any]` crossing layers.
- **Time:** timezone-aware UTC datetimes only; parse once at the edge; store `timestamptz`.
- **No per-row Python in data paths:** vectorise with polars expressions or numpy; a Python callback per row is a bug.
- Standard library first. A new dependency needs a reason, a maintained project, and a place behind a port when it does I/O.

## Related skills

[readable-code](readable-code.md) · [scaffold](scaffold.md) · [feature](feature.md) · [data](data.md) ·
[test](test.md) · [refactor](refactor.md) · [worker](worker.md) · `deployment-setup` · `service-logging` ·
`service-tracing` · for Rust-backed packages: [pyrust-scaffold](../../rust-code/references/pyrust-scaffold.md).

## Example usage

- “Which libraries should this new Python API use?”
- “Replace pandas in this job with the stack's choice.”
