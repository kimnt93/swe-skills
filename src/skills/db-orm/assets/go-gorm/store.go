// Package ormstore is the optional GORM adapter. Use it when the project asks for an ORM or already
// has one; the default adapter is raw SQL (go-code/references/postgres.md). Both implement the same
// port, so one replaces the other. GORM speaks PostgreSQL, MySQL, SQLite and SQL Server: the only
// database-specific line is the Dialector you pass to New.
package ormstore

import (
	"context"
	"errors"
	"fmt"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// ErrNotFound is returned when a row does not exist.
var ErrNotFound = errors.New("not found")

// itemModel maps the items table. Plain value fields, no pointers: the columns are NOT NULL, so a
// field is always a value. Every column is named in its tag; nothing relies on naming conventions.
type itemModel struct {
	ID        string    `gorm:"column:id;primaryKey"`
	Name      string    `gorm:"column:name"`
	CreatedAt time.Time `gorm:"column:created_at"`
}

// TableName pins the table so a rename of the type never changes the SQL.
func (itemModel) TableName() string {
	return "items"
}

// Item is the domain view of a row.
type Item struct {
	ID        string
	Name      string
	CreatedAt time.Time
}

// Store is the GORM adapter.
type Store struct {
	db *gorm.DB
}

// New wraps a connection the caller opened with its dialector, for example
// gorm.Open(postgres.Open(dsn), &gorm.Config{}) with gorm.io/driver/postgres.
func New(db *gorm.DB) *Store {
	return &Store{db: db}
}

// Close closes the pool.
func (s *Store) Close() error {
	sqlDB, err := s.db.DB()
	if err != nil {
		return err
	}

	return sqlDB.Close()
}

// Ping is the database check of /healthz.
func (s *Store) Ping(ctx context.Context) error {
	sqlDB, err := s.db.DB()
	if err != nil {
		return err
	}

	return sqlDB.PingContext(ctx)
}

// Create inserts one item. A struct Create writes every field, zero values included.
func (s *Store) Create(ctx context.Context, it Item) error {
	row := rowOf(it)

	return s.db.WithContext(ctx).Create(&row).Error
}

// Get loads one item; a missing row is ErrNotFound.
func (s *Store) Get(ctx context.Context, id string) (Item, error) {
	var row itemModel

	err := s.db.WithContext(ctx).Where("id = ?", id).Take(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
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

	err := s.db.WithContext(ctx).
		Where("id IN ?", ids).
		Order("created_at DESC").
		Limit(500).
		Find(&rows).Error
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

	return s.db.WithContext(ctx).
		Clauses(clause.OnConflict{
			Columns:   []clause.Column{{Name: "id"}},
			DoUpdates: clause.AssignmentColumns([]string{"name"}),
		}).
		Create(&row).Error
}

// RenameAll shows a transaction: one per business operation, rolled back when the function errors.
// It updates with a map: a struct Updates skips zero values, a map writes what it names.
func (s *Store) RenameAll(ctx context.Context, from, to string) (int64, error) {
	var affected int64

	err := s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		res := tx.Model(&itemModel{}).
			Where("name = ?", from).
			Updates(map[string]any{"name": to})
		if res.Error != nil {
			return fmt.Errorf("rename items: %w", res.Error)
		}

		affected = res.RowsAffected

		return nil
	})

	return affected, err
}

// CountByName is the raw SQL escape hatch: keep it for queries the builder makes unreadable.
func (s *Store) CountByName(ctx context.Context, name string) (int64, error) {
	const query = `
SELECT count(*)
FROM items
WHERE name = ?
`
	var count int64

	err := s.db.WithContext(ctx).Raw(query, name).Scan(&count).Error

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
