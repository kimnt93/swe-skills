//go:build integration

package ormstore

import (
	"context"
	"errors"
	"os"
	"strconv"
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestRoundTrip(t *testing.T) {
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
	id := uuid.NewString()

	item := Item{ID: id, Name: "pen", CreatedAt: time.Now().UTC()}
	if err := store.Create(ctx, item); err != nil {
		t.Fatal(err)
	}

	got, err := store.Get(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	if got.Name != "pen" || got.CreatedAt.Location() != time.UTC {
		t.Fatalf("round trip: %+v", got)
	}

	if _, err := store.Get(ctx, uuid.NewString()); !errors.Is(err, ErrNotFound) {
		t.Fatalf("missing row: %v", err)
	}

	item.Name = "pencil"
	if err := store.Upsert(ctx, item); err != nil {
		t.Fatal(err)
	}

	list, err := store.ListByIDs(ctx, []string{id})
	if err != nil || len(list) != 1 || list[0].Name != "pencil" {
		t.Fatalf("list after upsert: %+v %v", list, err)
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
