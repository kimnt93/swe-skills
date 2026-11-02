# Python refactor

Behaviour does not change. Each step passes the tests and could be committed alone.

## Procedure

1. **Pin behaviour.** `uv run pytest` first. No test around the code? Write a characterization test (inputs -> current outputs,
   including errors and edge cases) before touching it ([test](test.md)).
2. **One smell, one commit.** State the target in the commit message. Do not mix a refactor with a bug fix or a library swap.
3. **Move in small steps;** keep the old import path as a re-export only until the last caller moves.
4. **Verify after each step:** `ruff format --check`, `ruff check` (PEP 8, 79 columns), `pytest`, and the dependency rules below.

## Common refactors

| Smell | Target |
|---|---|
| Route holds SQL, rules or formatting | route -> use case -> port; rule into `domain`; SQL into `db/` |
| `psycopg`/`redis`/`confluent_kafka`/`litestar` imported in domain or application | Protocol port in `application/ports.py`, adapter in `db/`/`messaging/`, wire in the lifespan |
| Module-level clients, `os.environ` all over | `settings.py` only; adapters take settings or a client in the constructor |
| `datetime.now()`, `uuid4()`, `random` inside logic | inject `now`/`new_id`; domain becomes deterministic |
| Blocking calls inside `async def` | async client, `run_in_threadpool`, or a plain `def` route |
| `pandas` loops, `apply(axis=1)`, `iterrows` | polars expressions and lazy scan ([data](data.md)) |
| `json`/`dateutil` per message | `msgspec.Struct` decoder, `orjson`, `ciso8601` / `fromisoformat` |
| `dict[str, Any]` crossing layers | `msgspec.Struct` or a frozen dataclass at the right boundary |
| Broad `except Exception: pass`, string-matched errors | typed exceptions, specific handlers, log the cause once |
| Module over ~400 lines or `utils.py` | small modules named for the noun; one reason to change |
| N+1 queries, unbounded lists | `= ANY(%s)`, `LIMIT`, an index, batch inserts (`executemany`/COPY) |
| Mutable default args, global caches | explicit state, `lru_cache` only for pure lookups |

## Guard rails

```bash
! grep -rEn "^(from|import) (psycopg|redis|confluent_kafka|litestar)" src/*/domain src/*/application
! grep -rEni "pydantic|fastapi" src pyproject.toml
! grep -rEn "^(from|import) .*(\.db|\.messaging|\.api)" src/*/domain src/*/application
```

Stop and ask when a refactor needs a public API change, a schema change or touches a released migration. Do not delete data,
virtualenvs or build artifacts.

## Example usage

- “Split this 800-line module and move the SQL behind a repository port.”
- “Replace the pandas row loop with a polars expression and prove the output is unchanged.”
