// Package ormstore is the optional go-pg ORM adapter. Use it only when the project asks for the
// ORM or already has one; the default adapter is raw SQL (go-code/references/postgres.md).
package ormstore

import (
	"context"
	"errors"
	"fmt"
	"net"
	"strconv"
	"time"

	"github.com/go-pg/pg/v10"
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
	PoolSize int
}

// itemModel maps the items table. Plain value fields: no pointers, no omitempty, and use_zero on
// every written column, so a Go zero value is stored as a value and never as NULL.
type itemModel struct {
	tableName struct{} `pg:"items,alias:i"`

	ID        string    `pg:"id,pk,type:uuid,use_zero"`
	Name      string    `pg:"name,use_zero"`
	CreatedAt time.Time `pg:"created_at,use_zero"`
}

// Item is the domain view of a row.
type Item struct {
	ID        string
	Name      string
	CreatedAt time.Time
}

// Store is the go-pg ORM adapter.
type Store struct {
	db *pg.DB
}

// Open builds the pool; connections are made on first use.
func Open(c Postgres) *Store {
	return &Store{db: pg.Connect(&pg.Options{
		Addr:     net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
		User:     c.User,
		Password: c.Password,
		Database: c.Database,
		PoolSize: c.PoolSize,
	})}
}

// Close closes the pool.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping is the postgres check of /healthz.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.Ping(ctx)
}

// Create inserts one item.
func (s *Store) Create(ctx context.Context, it Item) error {
	row := rowOf(it)

	_, err := s.db.ModelContext(ctx, &row).Insert()

	return err
}

// Get loads one item; a missing row is ErrNotFound.
func (s *Store) Get(ctx context.Context, id string) (Item, error) {
	var row itemModel

	err := s.db.ModelContext(ctx, &row).Where("i.id = ?", id).Select()
	if errors.Is(err, pg.ErrNoRows) {
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

	err := s.db.ModelContext(ctx, &rows).
		Where("i.id IN (?)", pg.In(ids)).
		Order("i.created_at DESC").
		Limit(500).
		Select()
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

	_, err := s.db.ModelContext(ctx, &row).
		OnConflict("(id) DO UPDATE").
		Set("name = EXCLUDED.name").
		Insert()

	return err
}

// RenameAll shows a transaction: one per business operation, rolled back on error.
func (s *Store) RenameAll(ctx context.Context, from, to string) (int64, error) {
	var affected int64

	err := s.db.RunInTransaction(ctx, func(tx *pg.Tx) error {
		res, err := tx.ModelContext(ctx, (*itemModel)(nil)).
			Set("name = ?", to).
			Where("name = ?", from).
			Update()
		if err != nil {
			return fmt.Errorf("rename items: %w", err)
		}

		affected = int64(res.RowsAffected())

		return nil
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

	_, err := s.db.WithContext(ctx).QueryOne(pg.Scan(&count), query, name)

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
