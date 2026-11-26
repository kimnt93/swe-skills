# Injection

## What to look for

Text from outside that becomes **code or structure**: SQL (`WHERE`, `ORDER BY`, table and column names, `LIKE`
patterns), shell commands ([commands](files-commands-urls.md)), query operators from a JSON body, templates built from
input, response and mail headers (newlines), log lines, cache keys. An ORM's raw fragment is raw SQL.

## Bad

```go
q := fmt.Sprintf("SELECT id, total FROM orders WHERE user_id = '%s' ORDER BY %s", userID, sort)
_, err := db.QueryContext(ctx, &out, q)
```

## Good

```go
column, ok := map[string]string{"date": "created_at", "total": "total"}[sort]
if !ok {
    return ErrBadSort
}
q := `
    SELECT id, total
    FROM orders
    WHERE user_id = ?
    ORDER BY ` + column // only a value from the list above
_, err := db.QueryContext(ctx, &out, q, userID)
```

Values are always bound parameters (`?` in go-pg, `%s` with a parameter tuple in psycopg, `$1` in tokio-postgres).
Names cannot be bound: take them from a fixed list.

## Prove it

Against a disposable database or a local instance, with two users' rows: send `' OR '1'='1` and a sort of
`total; SELECT 1`. Expected: no other user's row, no database error text, and a 400 for the sort.
