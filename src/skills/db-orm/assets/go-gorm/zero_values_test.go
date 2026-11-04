package ormstore

import (
	"context"
	"testing"
	"time"

	"github.com/google/uuid"
)

// zeroModel maps zero_demo: every column NOT NULL DEFAULT, every field a plain value.
type zeroModel struct {
	ID     string    `gorm:"column:id;primaryKey"`
	Name   string    `gorm:"column:name"`
	Qty    int64     `gorm:"column:qty"`
	Active bool      `gorm:"column:active"`
	Seen   time.Time `gorm:"column:seen"`
	Note   string    `gorm:"column:note"`
}

func (zeroModel) TableName() string {
	return "zero_demo"
}

// TestZeroValuesAreStored proves two GORM rules: a struct Create writes zero values as
// values (a NOT NULL column accepts them), and a struct Updates skips zero values while a
// map writes them.
func TestZeroValuesAreStored(t *testing.T) {
	store := openForTest(t)
	defer store.Close()

	ctx := context.Background()
	row := zeroModel{ID: uuid.NewString(), Name: "x", Qty: 5, Active: true, Note: "n"}

	if err := store.db.WithContext(ctx).Create(&row).Error; err != nil {
		t.Fatal(err)
	}

	// a struct update silently skips the zero fields: the row keeps Qty 5
	if err := store.db.WithContext(ctx).Model(&zeroModel{}).Where("id = ?", row.ID).
		Updates(zeroModel{Qty: 0, Active: false}).Error; err != nil {
		t.Fatal(err)
	}

	var back zeroModel
	if err := store.db.WithContext(ctx).Where("id = ?", row.ID).Take(&back).Error; err != nil {
		t.Fatal(err)
	}
	if back.Qty != 5 || !back.Active {
		t.Fatalf("struct Updates was expected to skip zero values, got %+v", back)
	}

	// a map update writes them
	if err := store.db.WithContext(ctx).Model(&zeroModel{}).Where("id = ?", row.ID).
		Updates(map[string]any{"qty": 0, "active": false}).Error; err != nil {
		t.Fatal(err)
	}

	if err := store.db.WithContext(ctx).Where("id = ?", row.ID).Take(&back).Error; err != nil {
		t.Fatal(err)
	}
	if back.Qty != 0 || back.Active {
		t.Fatalf("map Updates must write zero values, got %+v", back)
	}

	// a fresh all-zero row is stored as values, not NULL
	empty := zeroModel{ID: uuid.NewString()}
	if err := store.db.WithContext(ctx).Create(&empty).Error; err != nil {
		t.Fatal(err)
	}
}
