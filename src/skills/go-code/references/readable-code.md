# Readable Go

*Verified with: Go 1.27 (`gofmt -s`, `go vet`); the "good" function below is `gofmt` clean and within 100 columns; the template passes `golangci-lint` with `lll`, `funlen` and `nestif`.*

Code is read many more times than it is written, by people and by the next agent. Write it so that one glance shows the
steps, and so that a diff shows exactly what changed. **Never compress code to save lines.** One idea per line, spaces
around everything, a blank line between steps. `gofmt` fixes spacing and braces but it **never wraps a long line** and does
not judge a six-way `||`, a 5-call chain, a 60-line function or a SQL string on one line. Those are your job.

## Bad and good

The same function twice. Bad: crammed together, no spaces, one-line blocks, short names:

```go
// BAD
func AverageLatencyMS(samples []Sample)(float64,bool){var t float64;var n int
for _,s:=range samples{if !s.OK||s.LatencyMS<0{continue};t+=s.LatencyMS;n++}
if n==0{return 0,false};return t/float64(n),true}
```

Good: spaces, one statement per line, a guard clause, a blank line between steps:

```go
// GOOD
func AverageLatencyMS(samples []Sample) (float64, bool) {
	var total float64
	var count int

	for _, sample := range samples {
		if !sample.OK || sample.LatencyMS < 0 {
			continue
		}

		total += sample.LatencyMS
		count++
	}

	if count == 0 {
		return 0, false
	}

	return total / float64(count), true
}
```

## The rules

| # | Rule | Instead of |
|---|---|---|
| 1 | **One statement per line.** Never `;` to join statements, never `if x { return y }` on one line. | `a:=1;b:=2`, `if err!=nil{return err}` |
| 2 | **Spaces everywhere** (`gofmt` enforces it: run it): around `:=`, `=`, `==`, `\|\|`, `&&`; after `,` and `:`. | `a:=b`, `f(a,b)` |
| 3 | **At most 100 columns** (`lll`, tabs count as 4), code and comments. `gofmt` does not wrap: you do. Break after the opening bracket, one item per line, trailing comma. | one 160-column call |
| 4 | **A condition has at most two operands.** More: one `if` per rule, each with its own error, or a named predicate (`isValidIdentity(c) bool`). | `a \|\| b \|\| c \|\| d \|\| e \|\| f` |
| 5 | **A method chain has at most three calls on one line.** Longer: one call per line (the dot ends the line), or name the intermediate value. | `a.B().C().D().E().F()` in one statement |
| 6 | **A function does one job and fits one screen** (about 40 lines; `funlen` at 60 lines / 40 statements). At most four parameters besides `ctx`; then take a struct. | a 150-line `NewClient` that validates, builds and connects |
| 7 | **Nesting at most three levels** (`nestif`). Early return, `continue`, extract the inner body. No `else` after `return`. | pyramid of `if` / `for` / `switch` |
| 8 | **Blank lines separate steps**: validate, build, return. Not inside a three-line block, never two in a row. | a wall of text |
| 9 | **Names say what a thing is.** `MixedCaps`, initialisms keep their case (`userID`); no `cfg`, `tmp`, `res`, `d`; a one-letter name only for a loop index or a tiny closure. | `r, e := f(c, b)` |
| 10 | **No magic values.** A number or string with a meaning is a named `const` (`maxIdentityLen`), declared once. | `len(x) > 256` in three places |
| 11 | **One failure, one error message.** Never one message for several checks; wrap with `%w`. | `"token, identity and bindings are required"` |
| 12 | **Comments explain why**, never excuse dense code. If a line needs a comment to be understood, split it. | `// checks everything` above a 6-way `\|\|` |
| 13 | **SQL is multi-line** (see below). | a 200-column query string |

## Idioms that keep Go readable

```go
// Struct literal: one field per line once it has more than two fields or does not fit
row := itemRow{
	ID:        it.ID,
	Name:      it.Name,
	CreatedAt: it.CreatedAt,
}

// A signature that does not fit: one parameter per line, trailing comma
func (s *Store) ListOpenOrders(
	ctx context.Context,
	accountID string,
	symbol string,
	limit int,
) ([]order.Order, error) {

// A condition with a meaning gets a name
isExpired := now.After(session.ExpiresAt)
isRevoked := !session.RevokedAt.IsZero()

if isExpired || isRevoked {
	return ErrUnauthorized
}

// Classify with switch, not an else-if ladder
switch {
case order.Quantity <= 0:
	return ErrInvalidQuantity
case order.Price <= 0:
	return ErrInvalidPrice
default:
	return nil
}

// A call with many arguments: one per line, trailing comma
client := newClient(
	cfg.BaseURL,
	cfg.Token,
	cfg.Timeout,
	logger,
)
```

`if err := f(); err != nil {` on one line is fine (it is the idiom) as long as the body is on the next lines. Avoid:
`else` after `return`, a closure longer than ten lines (make it a method), `interface{}`/`any` passing data between layers,
naked boolean parameters (`f(true, false)`: use a typed option), and deeply nested `if err == nil {` chains.

## Readable SQL

SQL is code. Write it the way you would want to read it in `psql` and in a code review: one clause per line, one column per
line, so a changed column is a one-line diff.

```go
// BAD
const sqlOpenOrders = `select o.id,o.symbol,sum(f.qty*f.price) as notional,count(*) from orders o join fills f on f.order_id=o.id where o.status='open' and o.created_at>now()-interval '1 day' and f.qty>0 group by o.id,o.symbol having count(*)>1 order by notional desc limit 100`
```

```go
// GOOD: a named const, a raw string, the SQL at column 0 inside the backticks
const sqlOpenOrders = `
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
`

const sqlUpsertItem = `
INSERT INTO items (id, name, created_at)
VALUES (?id, ?name, ?created_at)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name
`
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
8. **One named `const` per query**, next to the method that runs it, with `?` / `?field` placeholders (go-pg); never concatenate
   user input, never an inline literal inside the call. Comments (`--`) say why, above the clause.
9. **No `SELECT *`, and no conversions in the select list.** Never `value::float8`, `id::text`, `CAST(...)`, `to_char(...)` just to get a
   different type: select the raw column and let the `pg`-tagged row struct convert it (go-pg scans `uuid` into `string`, `numeric` into a decimal type).
10. Migration files in `schemas/` follow the same layout.

## Enforce it

- `golangci-lint fmt --diff ./...` (gofmt `-s` + goimports) and `golangci-lint run ./...` with `assets/template/.golangci.yml`, which
  adds `lll` (100 columns), `funlen` (60 lines, 40 statements) and `nestif` (complexity 4) to the standard linters.
  CI fails on any finding.
- Review your own diff before you finish. Fix anything that has: a line over 100 columns, `||` or `&&` more than twice in a
  condition, a chain of more than three calls on one line, a function over about 40 lines, a statement after a `{` on the same
  line, an unnamed number, a SQL string on one line.

## Example usage

- "Add a repository method that lists open orders by symbol." -> a multi-line SQL const, one step per line.
- "This function is hard to read, clean it up." -> split validation into named functions, early returns, one error per check.
