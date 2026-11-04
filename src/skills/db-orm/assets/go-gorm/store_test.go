package ormstore

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

func TestRoundTrip(t *testing.T) {
	store := openForTest(t)
	defer store.Close()

	ctx := context.Background()
	id := uuid.NewString()

	if err := store.Ping(ctx); err != nil {
		t.Fatal(err)
	}

	item := Item{ID: id, Name: "pen", CreatedAt: time.Now().UTC().Truncate(time.Microsecond)}
	if err := store.Create(ctx, item); err != nil {
		t.Fatal(err)
	}

	got, err := store.Get(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	sameTime := got.CreatedAt.Equal(item.CreatedAt)
	if got.Name != "pen" || got.CreatedAt.Location() != time.UTC || !sameTime {
		t.Fatalf("round trip: %+v want %+v", got, item)
	}

	if _, err := store.Get(ctx, uuid.NewString()); !errors.Is(err, ErrNotFound) {
		t.Fatalf("missing row: %v", err)
	}

	item.Name = "pencil"
	if err := store.Upsert(ctx, item); err != nil {
		t.Fatal(err)
	}
	if err := store.Upsert(ctx, item); err != nil {
		t.Fatal(err)
	}

	list, err := store.ListByIDs(ctx, []string{id})
	if err != nil || len(list) != 1 || list[0].Name != "pencil" {
		t.Fatalf("list after two upserts: %+v %v", list, err)
	}

	renamed, err := store.RenameAll(ctx, "pencil", "marker")
	if err != nil || renamed < 1 {
		t.Fatalf("rename: %d %v", renamed, err)
	}

	count, err := store.CountByName(ctx, "marker")
	if err != nil || count < 1 {
		t.Fatalf("raw count: %d %v", count, err)
	}
}

func TestTransactionRollsBack(t *testing.T) {
	store := openForTest(t)
	defer store.Close()

	ctx := context.Background()
	id := uuid.NewString()

	item := Item{ID: id, Name: "before-rollback", CreatedAt: time.Now().UTC()}
	if err := store.Create(ctx, item); err != nil {
		t.Fatal(err)
	}

	boom := errors.New("boom")

	err := store.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		err := tx.Model(&itemModel{}).
			Where("id = ?", id).
			Updates(map[string]any{"name": "inside"}).Error
		if err != nil {
			return err
		}

		return boom
	})
	if !errors.Is(err, boom) {
		t.Fatalf("transaction error: %v", err)
	}

	got, err := store.Get(ctx, id)
	if err != nil || got.Name != "before-rollback" {
		t.Fatalf("rollback did not undo the update: %+v %v", got, err)
	}
}
