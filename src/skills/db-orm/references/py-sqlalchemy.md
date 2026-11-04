# Python + SQLAlchemy 2 (async)

*Verified with: SQLAlchemy 2.0.57, aiosqlite 0.22, asyncpg 0.32, Python 3.12, PostgreSQL 16. `assets/python-sqlalchemy` passes on in-memory SQLite and on PostgreSQL; `ruff check` and `ruff format` (79 columns) are clean.*

Use it only when an ORM is requested or already in the project ([orm-rules](orm-rules.md)); the default is psycopg 3 with plain SQL
(`py-code/references/postgres.md`).

Reference: `assets/python-sqlalchemy/store.py` (adapter) and `test_store.py` (round trip, upsert twice, rollback; SQLite or PostgreSQL by
environment). Copy `store.py` next to the raw store, change `Item` for the project's domain type, implement the same port.

## Setup

```bash
pip install "sqlalchemy>=2.0,<2.1" asyncpg     # PostgreSQL; aiomysql for MySQL, aiosqlite for SQLite
```

```python
url = URL.create("postgresql+asyncpg", username=..., password=..., host=..., port=..., database=...)
store = Store.open(url.render_as_string(hide_password=False))
```

Build the URL from the `POSTGRES_*` settings the raw adapter uses, with `URL.create` (never f-string the password); never log it. Another
database changes the URL scheme only: `mysql+aiomysql://`, `sqlite+aiosqlite://`. `ping()` is the database check of `/healthz`.

## Model

```python
class ItemRow(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

Typed `Mapped[...]`, no `Optional` for NOT NULL columns, the ORM class stays inside the adapter, the domain gets a frozen dataclass
(or msgspec `Struct`, as the project does).

## Operations

| Need | SQLAlchemy 2 |
|---|---|
| insert | `async with sessions() as s, s.begin(): s.add(row)` |
| one row | `await s.get(ItemRow, id)`; `None` -> `NotFound` |
| a set, one query | `select(ItemRow).where(ItemRow.id.in_(ids)).order_by(...).limit(500)` then `await s.scalars(q)` |
| idempotent upsert | `postgresql.insert(...).on_conflict_do_update(index_elements=[...], set_=...)` (SQLite: `sqlite.insert`; MySQL: `on_duplicate_key_update`) |
| bulk update | `update(ItemRow).where(...).values(...)`, `result.rowcount` |
| transaction | `async with sessions() as s, s.begin():` (commit on exit, rollback on exception) |
| raw SQL | `await conn.execute(text("..."), {"name": name})` with a multi-line string |

## Pitfalls

- **Async only**: use `create_async_engine` and `AsyncSession`; no sync engine in an async service.
- **`expire_on_commit=False`** on the sessionmaker, or attributes expire after commit and a lazy load fails in async code.
- **Children**: `selectinload` / `joinedload` up front; lazy loading raises in async code, which is the point.
- **`metadata.create_all`** is for tests on SQLite only; a real database gets goose files. Never `Alembic autogenerate` into a goose project.
- **Naive datetimes**: SQLite returns naive values; the adapter marks them UTC at the edge (`_item`). PostgreSQL `timestamptz` returns aware ones.
- **Pooling**: `pool_size`/`max_overflow` per process; SQLite in memory takes no pool arguments (the adapter skips them).
- **Echo**: never `echo=True` in production; it logs SQL with values.
