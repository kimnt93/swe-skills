# Python + SQLAlchemy 2 (async)

*Verified with: SQLAlchemy 2.1.4 (`sqlalchemy[asyncio]`), psycopg 3.3, Python 3.12, PostgreSQL 17; `assets/python-sqlalchemy/test_postgres_orm.py` passes live and the adapter is `ruff format` and `ruff check` clean under the py-code configuration.*

Use it only when an ORM is requested or already in the project ([orm-rules](orm-rules.md)); the default is psycopg 3 with plain SQL
(`py-code/references/postgres.md`).

Reference: `assets/python-sqlalchemy/postgres_orm.py` (adapter) and `test_postgres_orm.py` (live test). Copy the adapter next to the raw
one as `service/db/postgres_orm.py`; both satisfy `ItemRepository`. Add `sqlalchemy[asyncio]>=2.0` to `pyproject.toml` (`uv add`). The
driver is the `psycopg[binary]` the raw adapter already uses (`postgresql+psycopg`).

## Setup

```python
url = URL.create(
    "postgresql+psycopg",
    username=settings.postgres_user,
    password=settings.postgres_password.get_secret_value(),
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_db,
    query={"sslmode": settings.postgres_sslmode},
)
engine = create_async_engine(url, pool_size=10, pool_pre_ping=True)
sessions = async_sessionmaker(engine, expire_on_commit=False)
```

- Build the URL with `URL.create` (a password with `@` or `/` would break a string URL) and read it from `PostgresSettings`
  (`POSTGRES_*`). Never log the URL.
- `expire_on_commit=False`: rows stay readable after commit and no lazy refresh can fire in async code.
- `await engine.dispose()` on shutdown; `SELECT 1` through `engine.connect()` is the `postgres` check of `/healthz`.

## Model rules

```python
class ItemRow(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

- `Mapped[...]` annotations (typed 2.0 style), no legacy `Column` declarations in new code. `Uuid(as_uuid=False)` keeps the domain ID a `str`.
  `DateTime(timezone=True)` in and out as aware UTC datetimes. Use `Numeric` + `Decimal` for money, never `Float`.
- The row class is not a domain type: convert to a frozen dataclass at the edge (`_to_item`). The domain never imports SQLAlchemy.

## Queries

```python
# One row by primary key.
row = await session.get(ItemRow, id)

# A set in one query, bounded.
statement = (
    select(ItemRow)
    .where(ItemRow.id.in_(ids))
    .order_by(ItemRow.created_at.desc())
    .limit(500)
)
rows = (await session.scalars(statement)).all()

# One transaction per operation: begin() commits on success, rolls back on error.
async with sessions() as session, session.begin():
    session.add(row)
```

- Chains longer than three calls go in parentheses, one call per line (`readable-code`). Raw SQL escape hatch: `text("""...""")` as a
  module-level constant in the multi-line layout, with `:name` bind parameters.
- Relationships: load explicitly (`selectinload`, `joinedload`) in the statement. Lazy loading raises `MissingGreenlet` in async code and
  hides N+1, so set `lazy="raise"` on relationships.
- `result.rowcount` for updates; `insert(...).on_conflict_do_update(...)` (`sqlalchemy.dialects.postgresql`) for idempotent writes.

## Do not

- `Base.metadata.create_all()` outside tests; the schema is a goose file (`db-migrations`). If the project already runs Alembic, keep
  Alembic as the only migration system and write the revisions as plain SQL (`op.execute`) so they read like the goose files.
- Share one `AsyncSession` between tasks, or keep one open across requests (one session per operation or per request).
- Return `ItemRow` from a route; return the msgspec Struct.

## Checks

```bash
uv run ruff format --check src tests && uv run ruff check src tests
set -a; . ./.env; set +a; uv run pytest -m integration -o addopts=""
```

## Example usage

- "Use SQLAlchemy for the items repository." · "Add a relationship to orders without N+1."
