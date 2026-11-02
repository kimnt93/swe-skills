# Readable Rust

*Verified with: rustfmt 1.10 and clippy 0.1.99 (Rust 1.99); the "good" function below compiles and is `cargo fmt --check` and clippy clean; the template passes `cargo clippy -D warnings` with the limits in `clippy.toml`.*

Code is read many more times than it is written, by people and by the next agent. Write it so that one glance shows the
steps, and so that a diff shows exactly what changed. **Never compress code to save lines.** One idea per line, spaces
around everything, a blank line between steps. A formatter fixes spacing; it does **not** fix a 6-way `||`, a 5-call chain,
a 60-line function or an unreadable SQL string. Those are your job.

## Bad and good

The same function twice. Bad: crammed on one line, no spaces, one-line blocks, short names:

```rust
// BAD
pub fn average_latency_ms(samples:&[Sample])->Option<f64>{let v:Vec<f64>=samples.iter().filter(|s|s.ok&&s.latency_ms>=0.0).map(|s|s.latency_ms).collect();if v.is_empty(){return None;}Some(v.iter().sum::<f64>()/v.len() as f64)}
```

Good: spaces, one step per line, a named intermediate value, a guard clause, a blank line between steps:

```rust
// GOOD
pub fn average_latency_ms(samples: &[Sample]) -> Option<f64> {
    let valid: Vec<f64> = samples
        .iter()
        .filter(|sample| sample.ok && sample.latency_ms >= 0.0)
        .map(|sample| sample.latency_ms)
        .collect();

    if valid.is_empty() {
        return None;
    }

    Some(valid.iter().sum::<f64>() / valid.len() as f64)
}
```

## The rules

| # | Rule | Instead of |
|---|---|---|
| 1 | **One statement per line.** Every block has its braces on their own lines. | `if x {return Err(e);}`, several statements after `;` |
| 2 | **Spaces everywhere**: around `=`, `==`, `\|\|`, `&&`, `->`, `=>`, `<`, `>`; after `,` and `:`. | `a=b`, `f(a,b)`, `x:Type`, `->Result` |
| 3 | **At most 100 columns** (`rustfmt.toml: max_width = 100`), code and comments. Wrap after the opening bracket, one item per line, trailing comma. | one 160-column call |
| 4 | **A condition has at most two operands.** More: one `if` per rule, each with its own error, or a named predicate (`fn is_valid_identity(..) -> bool`). | `a \|\| b \|\| c \|\| d \|\| e \|\| f` |
| 5 | **A method chain has at most three calls on one line.** Longer: one call per line (rustfmt does this), or name the intermediate value with `let`. | `a.b().c().d().e().f()` squeezed into one statement |
| 6 | **A function does one job and fits one screen** (about 40 lines; clippy `too_many_lines` at 60). At most five parameters, then take a struct. | a 150-line `new` that validates, builds and connects |
| 7 | **Nesting at most three levels.** Use guard clauses, `?`, `let ... else`, `continue`, and extract the inner body. | pyramid of `if let` / `match` / `for` |
| 8 | **Blank lines separate steps**: validate, build, return. Not inside a three-line block, not two in a row. | a wall of text, or a blank after every line |
| 9 | **Names say what a thing is.** No `cfg`, `tmp`, `res`, `e`, `v`; one-letter names only for a closure over a tiny scope (`\|x\| x.id`). | `let r = f(c, b)` |
| 10 | **No magic values.** A number or string with a meaning is a named `const` (`MAX_IDENTITY_LEN`), declared once. | `.len() > 256` in three places |
| 11 | **One failure, one error message.** Never one message for several checks. | `"token, identity and bindings are required"` |
| 12 | **Comments explain why**, never excuse dense code. If a line needs a comment to be understood, split it. | `// checks everything` above a 6-way `\|\|` |
| 13 | **SQL is multi-line** (see below). | a 200-column query string |

Rules 1-3 are mostly the formatter's job: run `cargo fmt --all` on every file you touched, and never write code you would
not want to review. Rules 4-13 are yours; `rustfmt` will not enforce them.

## Idioms that keep Rust readable

```rust
// Early return with a guard, instead of nesting
let Some(token) = headers.get("authorization") else {
    return Err(Error::Unauthorized);
};

// One struct field per line once a literal has more than two fields or does not fit
let item = Item {
    id: row.get::<_, Uuid>(0).to_string(),
    name: row.get(1),
    created_at: row.get(2),
};

// A chain of more than three calls: one call per line, each line one step
let names: Vec<String> = items
    .iter()
    .filter(|item| item.is_active())
    .map(|item| item.name.trim().to_owned())
    .collect();

// A condition with a meaning gets a name
let is_expired = now > session.expires_at;
let is_revoked = session.revoked_at.is_some();

if is_expired || is_revoked {
    return Err(Error::Unauthorized);
}

// Many arguments: one per line, trailing comma
let order = Order::new(
    account_id,
    symbol,
    side,
    quantity,
    limit_price,
);
```

Avoid: nested `match` inside `match`, closures longer than five lines (make them a function), `.unwrap()` chains to "keep it short"
(use `?`), `if let Some(x) = a { if let Some(y) = b { ... } }` (use `let ... else` or `a.zip(b)`), and boolean parameters that
read as `f(true, false)` (use an enum or a named options struct).

## Readable SQL

SQL is code. Write it the way you would want to read it in `psql` and in a code review: one clause per line, one column per
line, so a changed column is a one-line diff.

```rust
// BAD
const OPEN_ORDERS: &str = "select o.id,o.symbol,sum(f.qty*f.price) as notional,count(*) from orders o join fills f on f.order_id=o.id where o.status='open' and o.created_at>now()-interval '1 day' and f.qty>0 group by o.id,o.symbol having count(*)>1 order by notional desc limit 100";
```

```rust
// GOOD
const OPEN_ORDERS: &str = "
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
";

const UPSERT_ITEM: &str = "
    INSERT INTO items (id, name, created_at)
    VALUES ($1, $2, $3)
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name
";
```

1. **Keywords UPPER CASE, identifiers lower `snake_case`.** Functions too (`COUNT`, `SUM`) except where the project writes them lower.
2. **Each clause starts a new line** at the same indent: `SELECT`, `FROM`, `JOIN`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`,
   `INSERT INTO`, `VALUES`, `ON CONFLICT`, `SET`, `RETURNING`.
3. **One selected column per line**, indented 4, trailing comma between them. Only a trivial statement may stay on one line
   (`SELECT 1`, `SELECT count(*) FROM items`).
4. **`AND` / `OR` start the continuation line**, indented 4 under `WHERE`. Parenthesise mixed `AND`/`OR`.
5. **Always `AS`** for column and table aliases. With a `JOIN`, qualify every column with its alias (`o.id`).
6. **One `JOIN` per line**, with its `ON` condition on that line (or indented below when long).
7. **Subqueries and CTEs are indented blocks**; a CTE has a name that says its purpose (`WITH open_orders AS (` ... `)`).
8. **Constants, not inline strings**: a named `const` next to the function that runs it, one query per constant. Use `$1, $2` parameters;
   never `format!` user input into SQL. Comments (`--`) say why, above the clause.
9. **No `SELECT *`, and no conversions in the select list.** Never `value::float8`, `id::text`, `CAST(...)`, `to_char(...)` just to get a
   different type: select the raw column and convert in the Rust type (`row.get::<_, Uuid>(0)`, a `From` impl, `time::OffsetDateTime`).
10. Migration files in `schemas/` follow the same layout.

## Enforce it

- `rustfmt.toml` in the workspace root (`assets/template/rustfmt.toml`): `max_width = 100`. CI: `cargo fmt --all -- --check`.
- `clippy.toml` and `[workspace.lints.clippy]` in `assets/template/Cargo.toml` turn on `too_many_lines`, `cognitive_complexity`
  and `too_many_arguments`, so a function that grows past a screen fails `clippy -D warnings`.
- Review your own diff before you finish. Fix anything that has: a line over 100 columns, `||` or `&&` more than twice in a
  condition, a chain of more than three calls on one line, a function over about 40 lines, a statement after a `{` on the same
  line, an unnamed number, a SQL string on one line.

## Example usage

- "Add a repository method that lists open orders by symbol." -> multi-line SQL constant, one step per line.
- "This function is hard to read, clean it up." -> split validation into named functions, guard clauses, one error per check.
