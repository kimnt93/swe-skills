// Package postgres implements the application ports with go-pg v10 and RAW SQL. SQL and `pg` tags
// live here only.
//
// House rules for rows (see the go-postgres skill):
//   - one plain struct per query shape, fields mapped with `pg:"column"`; helper/computed fields
//     use `pg:"-"`;
//   - NO pointers and NO omitempty: columns are NOT NULL with defaults, so a field is its zero
//     value, never nil;
//   - SQL is a named constant next to the method that runs it; arguments are always `?`
//     placeholders.
package postgres

import (
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"net"
	"strconv"
	"time"

	"github.com/go-pg/pg/v10"

	"example.com/service/internal/application"
	"example.com/service/internal/config"
	"example.com/service/internal/domain/item"
)

var _ application.ItemRepository = (*Store)(nil)

// Store is the PostgreSQL adapter (go-pg v10, raw SQL).
type Store struct {
	db *pg.DB
}

// Open builds the pool. sslmode=disable turns TLS off; any other value verifies the server
// certificate.
func Open(c config.Postgres) *Store {
	opts := &pg.Options{
		Addr:        net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
		User:        c.User,
		Password:    c.Password,
		Database:    c.Database,
		PoolSize:    c.PoolSize,
		DialTimeout: 5 * time.Second,
		ReadTimeout: 10 * time.Second,
	}
	if c.SSLMode != "disable" {
		opts.TLSConfig = &tls.Config{ServerName: c.Host, MinVersion: tls.VersionTLS12}
	}
	return &Store{db: pg.Connect(opts)}
}

// Ping checks that the database answers.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.Ping(ctx)
}

// Close closes the connection pool.
func (s *Store) Close() error {
	return s.db.Close()
}

// itemRow maps the columns of `items`. `use_zero` makes go-pg write a zero value as a real value
// (0, ”, false) instead of NULL, which is what "no pointers, defaults are zero values" requires.
// `Label` is not a column.
type itemRow struct {
	ID        string    `pg:"id,use_zero"`
	Name      string    `pg:"name,use_zero"`
	CreatedAt time.Time `pg:"created_at,use_zero"`
	Label     string    `pg:"-"` // ignored by go-pg: derived in Go after the query
}

func (r itemRow) toDomain() item.Item {
	return item.Item{ID: r.ID, Name: r.Name, CreatedAt: r.CreatedAt.UTC()}
}

func rowOf(it item.Item) itemRow {
	return itemRow{ID: it.ID, Name: it.Name, CreatedAt: it.CreatedAt, Label: it.Name}
}

// SQL is written the way psql would run it: one clause per line, one column per line.
const (
	sqlInsertItem = `
INSERT INTO items (id, name, created_at)
VALUES (?id, ?name, ?created_at)
`

	sqlGetItem = `
SELECT
    id,
    name,
    created_at
FROM items
WHERE id = ?
`

	sqlListItems = `
SELECT
    id,
    name,
    created_at
FROM items
WHERE id IN (?)
ORDER BY created_at DESC
LIMIT 500
`

	sqlUpsertItem = `
INSERT INTO items (id, name, created_at)
VALUES (?id, ?name, ?created_at)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name
`

	sqlRenameAll = `
UPDATE items
SET name = ?
WHERE name = ?
`

	sqlClaimItem = `
SELECT
    id,
    name,
    created_at
FROM items
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
`

	sqlCountItems = `SELECT count(*) FROM items`

	sqlInsertZero = `
INSERT INTO zero_demo (id, name, qty, active, seen, note)
VALUES (?id, ?name, ?qty, ?active, ?seen, ?note)
`

	sqlGetZero = `
SELECT
    id,
    name,
    qty,
    active,
    seen,
    note,
    CASE WHEN name IS NULL THEN 1 ELSE 0 END
        + CASE WHEN note IS NULL THEN 1 ELSE 0 END AS nulls
FROM zero_demo
WHERE id = ?
`
)

// Create inserts the item.
func (s *Store) Create(ctx context.Context, it item.Item) error {
	row := rowOf(it)

	// ?id ?name ?created_at are read from the struct fields.
	_, err := s.db.ExecContext(ctx, sqlInsertItem, &row)
	return err
}

// Get loads one item; a missing row returns application.ErrNotFound.
func (s *Store) Get(ctx context.Context, id string) (item.Item, error) {
	var row itemRow
	if _, err := s.db.QueryOneContext(ctx, &row, sqlGetItem, id); err != nil {
		if errors.Is(err, pg.ErrNoRows) {
			return item.Item{}, application.ErrNotFound
		}
		return item.Item{}, err
	}
	return row.toDomain(), nil
}

// ListByIDs loads a set with one query (no N+1) and always bounds it.
func (s *Store) ListByIDs(ctx context.Context, ids []string) ([]item.Item, error) {
	if len(ids) == 0 {
		return nil, nil
	}
	var rows []itemRow
	if _, err := s.db.QueryContext(ctx, &rows, sqlListItems, pg.In(ids)); err != nil {
		return nil, fmt.Errorf("list items by id: %w", err)
	}
	out := make([]item.Item, 0, len(rows))
	for _, r := range rows {
		out = append(out, r.toDomain())
	}
	return out, nil
}

// Upsert is idempotent: replaying the same message or request converges on one row.
func (s *Store) Upsert(ctx context.Context, it item.Item) error {
	row := rowOf(it)
	_, err := s.db.ExecContext(ctx, sqlUpsertItem, &row)
	return err
}

// RenameAll shows the transaction shape: one transaction per business operation, no other
// repository mid-way.
func (s *Store) RenameAll(ctx context.Context, from, to string) (int, error) {
	var n int
	err := s.db.RunInTransaction(ctx, func(tx *pg.Tx) error {
		res, err := tx.ExecContext(ctx, sqlRenameAll, to, from)
		if err != nil {
			return fmt.Errorf("rename items: %w", err)
		}
		n = res.RowsAffected()
		return nil
	})
	return n, err
}

// ClaimOldest locks the oldest row for this transaction only (FOR UPDATE SKIP LOCKED), so several
// replicas can work a queue-like table without blocking each other. fn runs inside the transaction.
func (s *Store) ClaimOldest(ctx context.Context, fn func(item.Item) error) (bool, error) {
	claimed := false
	err := s.db.RunInTransaction(ctx, func(tx *pg.Tx) error {
		var row itemRow
		if _, err := tx.QueryOneContext(ctx, &row, sqlClaimItem); err != nil {
			if errors.Is(err, pg.ErrNoRows) {
				return nil
			}
			return err
		}
		claimed = true
		return fn(row.toDomain())
	})
	return claimed, err
}

// Count shows scanning a scalar.
func (s *Store) Count(ctx context.Context) (int, error) {
	var n int
	_, err := s.db.QueryOneContext(ctx, pg.Scan(&n), sqlCountItems)
	return n, err
}

// zeroRow demonstrates the struct rules on a table with several column types: all `use_zero`, no
// pointers, one ignored helper field. NullsInDB is computed by the query (it is not a column), so
// it carries `pg:"-"`-style intent via an alias instead: the query aliases a column count into it.
type zeroRow struct {
	ID        string    `pg:"id,use_zero"`
	Name      string    `pg:"name,use_zero"`
	Qty       int64     `pg:"qty,use_zero"`
	Active    bool      `pg:"active,use_zero"`
	Seen      time.Time `pg:"seen,use_zero"`
	Note      string    `pg:"note,use_zero"`
	NullsInDB int       `pg:"nulls"`
	Scratch   string    `pg:"-"`
}

// Zero is the exported view used by tests and examples.
type Zero struct {
	Name      string
	Qty       int64
	Active    bool
	Seen      time.Time
	Note      string
	NullsInDB int
}

// CreateZero inserts a row whose every value is the Go zero value, through struct parameters.
func (s *Store) CreateZero(ctx context.Context, id string) error {
	row := zeroRow{ID: id}
	_, err := s.db.ExecContext(ctx, sqlInsertZero, &row)

	return err
}

// GetZero reads a zero_demo row back, including how many of its columns are NULL (always 0).
func (s *Store) GetZero(ctx context.Context, id string) (Zero, error) {
	var row zeroRow
	_, err := s.db.QueryOneContext(ctx, &row, sqlGetZero, id)
	if err != nil {
		return Zero{}, err
	}

	return Zero{
		Name:      row.Name,
		Qty:       row.Qty,
		Active:    row.Active,
		Seen:      row.Seen,
		Note:      row.Note,
		NullsInDB: row.NullsInDB,
	}, nil
}
