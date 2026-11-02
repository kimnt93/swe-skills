// Package ormstore is the optional bun ORM adapter. Use it only when the project asks for an ORM
// or already has one; the default adapter is raw SQL (go-code/references/postgres.md).
package ormstore

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net"
	"net/url"
	"strconv"
	"time"

	"github.com/uptrace/bun"
	"github.com/uptrace/bun/dialect/pgdialect"
	"github.com/uptrace/bun/driver/pgdriver"
)

// ErrNotFound is returned when a row does not exist.
var ErrNotFound = errors.New("not found")

// Postgres holds the POSTGRES_* settings the config package already loads.
type Postgres struct {
	Host     string
	Port     int
	Database string
	User     string
	Password string
	SSLMode  string
}

// itemModel maps the items table. Plain value fields: no pointers, no nullzero or omitempty, so a
// zero value is written as a value.
type itemModel struct {
	bun.BaseModel `bun:"table:items,alias:i"`

	ID        string    `bun:"id,pk,type:uuid"`
	Name      string    `bun:"name,notnull"`
	CreatedAt time.Time `bun:"created_at,notnull"`
}

// Item is the domain view of a row.
type Item struct {
	ID        string
	Name      string
	CreatedAt time.Time
}

// Store is the bun adapter.
type Store struct {
	db *bun.DB
}

// Open connects with the pgdriver and wraps the pool in bun.
func Open(c Postgres) *Store {
	dsn := url.URL{
		Scheme:   "postgres",
		User:     url.UserPassword(c.User, c.Password),
		Host:     net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
		Path:     c.Database,
		RawQuery: "sslmode=" + c.SSLMode,
	}

	sqldb := sql.OpenDB(pgdriver.NewConnector(pgdriver.WithDSN(dsn.String())))

	return &Store{db: bun.NewDB(sqldb, pgdialect.New())}
}

// Close closes the pool.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts one item.
func (s *Store) Create(ctx context.Context, it Item) error {
	row := rowOf(it)

	_, err := s.db.NewInsert().Model(&row).Exec(ctx)

	return err
}

// Get loads one item; a missing row is ErrNotFound.
func (s *Store) Get(ctx context.Context, id string) (Item, error) {
	var row itemModel

	err := s.db.NewSelect().Model(&row).Where("i.id = ?", id).Scan(ctx)
	if errors.Is(err, sql.ErrNoRows) {
		return Item{}, ErrNotFound
	}
	if err != nil {
		return Item{}, fmt.Errorf("get item: %w", err)
	}

	return row.toItem(), nil
}

// ListByIDs loads a set with one query (no N+1) and always bounds it.
func (s *Store) ListByIDs(ctx context.Context, ids []string) ([]Item, error) {
	var rows []itemModel

	err := s.db.NewSelect().
		Model(&rows).
		Where("i.id IN (?)", bun.List(ids)).
		OrderExpr("i.created_at DESC").
		Limit(500).
		Scan(ctx)
	if err != nil {
		return nil, fmt.Errorf("list items: %w", err)
	}

	items := make([]Item, 0, len(rows))
	for _, row := range rows {
		items = append(items, row.toItem())
	}

	return items, nil
}

// Upsert is idempotent: a replay converges on one row.
func (s *Store) Upsert(ctx context.Context, it Item) error {
	row := rowOf(it)

	_, err := s.db.NewInsert().
		Model(&row).
		On("CONFLICT (id) DO UPDATE").
		Set("name = EXCLUDED.name").
		Exec(ctx)

	return err
}

// RenameAll shows a transaction: one per business operation, rolled back on error.
func (s *Store) RenameAll(ctx context.Context, from, to string) (int64, error) {
	var affected int64

	err := s.db.RunInTx(ctx, nil, func(ctx context.Context, tx bun.Tx) error {
		res, err := tx.NewUpdate().
			Model((*itemModel)(nil)).
			Set("name = ?", to).
			Where("name = ?", from).
			Exec(ctx)
		if err != nil {
			return fmt.Errorf("rename items: %w", err)
		}

		affected, err = res.RowsAffected()

		return err
	})

	return affected, err
}

// CountByName is the raw SQL escape hatch: keep it for queries the builder makes unreadable.
func (s *Store) CountByName(ctx context.Context, name string) (int, error) {
	const query = `
SELECT count(*)
FROM items
WHERE name = ?
`
	var count int

	err := s.db.NewRaw(query, name).Scan(ctx, &count)

	return count, err
}

func rowOf(it Item) itemModel {
	return itemModel{
		ID:        it.ID,
		Name:      it.Name,
		CreatedAt: it.CreatedAt,
	}
}

func (m itemModel) toItem() Item {
	return Item{
		ID:        m.ID,
		Name:      m.Name,
		CreatedAt: m.CreatedAt.UTC(),
	}
}
