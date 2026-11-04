//go:build integration

package ormstore

import (
	"context"
	"testing"
	"time"

	"github.com/google/uuid"
)

// zeroModel maps zero_demo (go-code/assets/template/schemas/0002_zero_values.sql): every column is
// NOT NULL DEFAULT, every field a plain value, every written column tagged use_zero.
type zeroModel struct {
	tableName struct{} `pg:"zero_demo"`

	ID     string    `pg:"id,pk,type:uuid,use_zero"`
	Name   string    `pg:"name,use_zero"`
	Qty    int64     `pg:"qty,use_zero"`
	Active bool      `pg:"active,use_zero"`
	Seen   time.Time `pg:"seen,use_zero"`
	Note   string    `pg:"note,use_zero"`
}

// TestZeroValuesAreStoredNotNull proves the "use_zero on every written column" rule: a Go zero
// value is written as a real value, so a NOT NULL column accepts it and reads it back unchanged.
func TestZeroValuesAreStoredNotNull(t *testing.T) {
	store := openFromEnv()
	defer store.Close()

	ctx := context.Background()
	row := zeroModel{ID: uuid.NewString()}

	if _, err := store.db.ModelContext(ctx, &row).Insert(); err != nil {
		t.Fatal(err)
	}

	back := zeroModel{ID: row.ID}
	if err := store.db.ModelContext(ctx, &back).WherePK().Select(); err != nil {
		t.Fatal(err)
	}

	isZeroRow := back.Name == "" && back.Qty == 0 && !back.Active && back.Seen.IsZero() &&
		back.Note == ""
	if !isZeroRow {
		t.Fatalf("zero row read back as %+v", back)
	}
}
