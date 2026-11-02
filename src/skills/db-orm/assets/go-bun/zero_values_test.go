//go:build integration

package ormstore

import (
	"context"
	"os"
	"strconv"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/uptrace/bun"
)

// zeroModel maps zero_demo (go-code/assets/template/schemas/0002_zero_values.sql): every column is
// NOT NULL DEFAULT, every field a plain value.
type zeroModel struct {
	bun.BaseModel `bun:"table:zero_demo"`

	ID     string    `bun:"id,pk,type:uuid"`
	Name   string    `bun:"name,notnull"`
	Qty    int64     `bun:"qty,notnull"`
	Active bool      `bun:"active,notnull"`
	Seen   time.Time `bun:"seen,notnull"`
	Note   string    `bun:"note,notnull"`
}

// TestZeroValuesAreStoredNotNull proves the "no pointers, no nullzero" rule: a Go zero value is
// written as a real value, so a NOT NULL column accepts it and reads it back unchanged.
func TestZeroValuesAreStoredNotNull(t *testing.T) {
	port, _ := strconv.Atoi(os.Getenv("POSTGRES_PORT"))
	store := Open(Postgres{
		Host:     os.Getenv("POSTGRES_HOST"),
		Port:     port,
		Database: os.Getenv("POSTGRES_DB"),
		User:     os.Getenv("POSTGRES_USER"),
		Password: os.Getenv("POSTGRES_PASSWORD"),
		SSLMode:  "disable",
	})
	defer store.Close()

	ctx := context.Background()
	row := zeroModel{ID: uuid.NewString()}

	if _, err := store.db.NewInsert().Model(&row).Exec(ctx); err != nil {
		t.Fatal(err)
	}

	var back zeroModel
	if err := store.db.NewSelect().Model(&back).Where("id = ?", row.ID).Scan(ctx); err != nil {
		t.Fatal(err)
	}

	isZeroRow := back.Name == "" && back.Qty == 0 && !back.Active && back.Seen.IsZero() &&
		back.Note == ""
	if !isZeroRow {
		t.Fatalf("zero row read back as %+v", back)
	}
}
