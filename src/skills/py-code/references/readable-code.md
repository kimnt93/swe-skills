# Readable Python

*Verified with: ruff 0.16 (`ruff format`, `ruff check`) at 79 columns; the "good" function below is `ruff format` and `ruff check` clean.*

Code is read many more times than it is written, by people and by the next agent. Write it so that one glance shows the
steps, and so that a diff shows exactly what changed. **Never compress code to save lines.** PEP 8 is the floor
([stack](stack.md) lists the enforced rules); this page is what PEP 8 and `ruff format` do not decide for you: a six-way `or`,
a five-call chain, a 60-line function, a SQL string on one line. One idea per line, spaces around everything, a blank line
between steps.

## Bad and good

The same function twice. Bad: crammed together, no spaces, one-line blocks, short names:

```python
# BAD
def average_latency_ms(samples:list[Sample])->float|None:
    v=[s.latency_ms for s in samples if s.ok and s.latency_ms>=0]
    if not v: return None
    return sum(v)/len(v)
```

Good: spaces, one clause per line, a named intermediate value, a guard clause, a blank line between steps:

```python
# GOOD
def average_latency_ms(samples: list[Sample]) -> float | None:
    valid = [
        sample.latency_ms
        for sample in samples
        if sample.ok and sample.latency_ms >= 0
    ]

    if not valid:
        return None

    return sum(valid) / len(valid)
```

## The rules

| # | Rule | Instead of |
|---|---|---|
| 1 | **One statement per line.** Never `;`, never `if x: return y` on one line (pycodestyle E701, E702, E703). | `a = 1; b = 2`, `if x: raise E` |
| 2 | **Spaces everywhere**: around `=`, `==`, `->`, `and`/`or`; after `,` and `:`. No space before `(` of a call. | `def f(a:int)->str`, `x=y`, `f(a,b)` |
| 3 | **At most 79 columns**, code, comments and docstrings. Wrap after the opening bracket, one item per line, **trailing comma** (ruff keeps a list exploded when it ends with one). | one 160-column call |
| 4 | **A condition has at most two operands.** More: one `if` per rule, each with its own error, or a named predicate / bool (`is_valid_identity(config)`). | `a or b or c or d or e or f` |
| 5 | **A method chain has at most three calls on one line.** Longer: wrap in parentheses with one call per line, or name the intermediate value. | `a.b().c().d().e().f()` in one statement |
| 6 | **A function does one job and fits one screen** (about 30 lines; ruff `PLR0915` at 40 statements). At most five parameters; then take a dataclass or use keyword-only arguments. | a 150-line `__init__` that validates, builds and connects |
| 7 | **Nesting at most three levels.** Guard clauses, early `return`/`raise`/`continue`, extract the inner body. | pyramid of `if` / `for` / `try` |
| 8 | **Blank lines separate steps**: validate, build, return. PEP 8 two blank lines around top-level definitions, one between methods. | a wall of text |
| 9 | **Names say what a thing is.** `snake_case`, no `cfg`, `tmp`, `res`, `e`, `d`; never shadow a builtin (`id`, `type`, `list`, `input`). | `for id, b in d.items()` |
| 10 | **No magic values.** A number or string with a meaning is a named `UPPER_CASE` constant, declared once. | `len(x) > 256` in three places |
| 11 | **One failure, one error message.** Never one message for several checks. | `"token, identity and bindings are required"` |
| 12 | **Comprehensions: one `for` and at most one `if`**, one clause per line when it does not fit. Anything more is a loop or a function. A `lambda` is never assigned to a name. | nested comprehension with two `for` |
| 13 | **Comments explain why**, never excuse dense code. If a line needs a comment to be understood, split it. | `# checks everything` above a 6-way `or` |
| 14 | **SQL is multi-line** (see below). | a 200-column query string |

Rules 1-3 are the formatter's job: run `uv run ruff format src tests` on every file you touched. Rules 4-14 are yours.

## Idioms that keep Python readable

```python
# Guard clause instead of nesting
if token is None:
    raise UnauthorizedError("missing token")

# A condition with a meaning gets a name
is_expired = now > session.expires_at
is_revoked = session.revoked_at is not None

if is_expired or is_revoked:
    raise UnauthorizedError("session is not active")

# A call with many arguments: one per line, trailing comma, keywords for clarity
order = Order(
    account_id=account_id,
    symbol=symbol,
    side=side,
    quantity=quantity,
    limit_price=limit_price,
)

# A chain of more than three calls: parentheses, one step per line
names = (
    frame.filter(pl.col("active"))
    .select(pl.col("name").str.strip_chars())
    .unique()
    .to_series()
    .to_list()
)

# A comprehension that fits one thought
active_names = [item.name for item in items if item.is_active]
```

Avoid: `try` blocks that wrap a whole function (wrap only the call that can fail), `except Exception: pass`, nested ternaries, boolean
parameters that read as `f(True, False)` (use keyword-only arguments or an `Enum`), and `dict[str, Any]` passed between layers
(use a dataclass or `msgspec.Struct`).

## Readable SQL

SQL is code. Write it the way you would want to read it in `psql` and in a code review: one clause per line, one column per
line, so a changed column is a one-line diff.

```python
# BAD
OPEN_ORDERS_SQL = "select o.id,o.symbol,sum(f.qty*f.price) as notional,count(*) from orders o join fills f on f.order_id=o.id where o.status='open' and o.created_at>now()-interval '1 day' and f.qty>0 group by o.id,o.symbol having count(*)>1 order by notional desc limit 100"
```

```python
# GOOD: a module-level constant, a triple-quoted string, the SQL at column 0
OPEN_ORDERS_SQL = """
SELECT
    o.id,
    o.symbol,
    SUM(f.qty * f.price) AS notional,
    COUNT(*) AS fill_count
FROM orders AS o
JOIN fills AS f ON f.order_id = o.id
WHERE o.status = 'open'
    AND o.created_at > now() - INTERVAL '1 day'
    AND f.qty > 0
GROUP BY o.id, o.symbol
HAVING COUNT(*) > 1
ORDER BY notional DESC
LIMIT 100
"""

UPSERT_ITEM_SQL = """
INSERT INTO items (id, name, created_at)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name
"""
```

1. **Keywords UPPER CASE, identifiers lower `snake_case`.**
2. **Each clause starts a new line** at the same indent: `SELECT`, `FROM`, `JOIN`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`,
   `INSERT INTO`, `VALUES`, `ON CONFLICT`, `SET`, `RETURNING`.
3. **One selected column per line**, indented 4, comma at the end of the line. Only a trivial statement may stay on one line
   (`SELECT 1`, `SELECT count(*) FROM items`).
4. **`AND` / `OR` start the continuation line**, indented 4 under `WHERE`. Parenthesise mixed `AND`/`OR`.
5. **Always `AS`** for column and table aliases. With a `JOIN`, qualify every column with its alias (`o.id`).
6. **One `JOIN` per line**, with its `ON` condition on that line (or indented below when long).
7. **Subqueries and CTEs are indented blocks**; a CTE has a name that says its purpose (`WITH open_orders AS (` ... `)`).
8. **Named module-level constants** next to the repository that uses them, one query per constant, parameters as `%s` (psycopg), never
   an f-string or `%` with user input. Do not build SQL by implicit string concatenation across lines; the triple-quoted block is
   the query exactly as `psql` would run it. Comments (`--`) say why, above the clause.
9. **No `SELECT *`, and no conversions in the select list.** Never `value::float8`, `id::text`, `CAST(...)`, `to_char(...)` just to get a
   different type: select the raw column and convert in the row mapping (`str(row["id"])`, `Decimal`, a dataclass or `msgspec.Struct`).
10. Migration files in `schemas/` follow the same layout.

## Enforce it

- `pyproject.toml` (`assets/template/pyproject.toml`): `line-length = 79`, ruff `E W F I N UP B SIM ASYNC` plus `C901` (complexity 10)
  and `PLR0911 PLR0912 PLR0913 PLR0915` (returns, branches, arguments, statements), so a function that grows past a screen fails
  `ruff check`. `E701 E702 E703` (compound statements) are part of `E`.
- CI: `ruff format --check`, `ruff check`, `pycodestyle --max-line-length=79`.
- Review your own diff before you finish. Fix anything that has: a line over 79 columns, `or`/`and` more than twice in a condition,
  a chain of more than three calls on one line, a function over about 30 lines, a statement after a `:` on the same line, an
  unnamed number, a SQL string on one line.

## Example usage

- "Add a repository method that lists open orders by symbol." -> a multi-line SQL constant, one step per line.
- "This function is hard to read, clean it up." -> split validation into named functions, guard clauses, one error per check.
