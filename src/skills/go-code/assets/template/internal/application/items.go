package application

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"example.com/service/internal/domain/item"
)

// Items holds the item use cases; every dependency (repository, publisher, id and clock sources) is
// injected.
type Items struct {
	Repo   ItemRepository
	Events EventPublisher
	NewID  func() string
	Now    func() time.Time
}

// Create validates the name, stores the item and publishes items.created.
func (s Items) Create(ctx context.Context, name string) (item.Item, error) {
	it, err := item.New(s.NewID(), name, s.Now())
	if err != nil {
		return item.Item{}, err
	}
	if err := s.Repo.Create(ctx, it); err != nil {
		return item.Item{}, fmt.Errorf("create item: %w", err)
	}
	payload, _ := json.Marshal(map[string]any{"id": it.ID, "name": it.Name})
	if err := s.Events.Publish(ctx, "items.created", it.ID, payload); err != nil {
		return item.Item{}, fmt.Errorf("publish item.created: %w", err)
	}
	return it, nil
}

// Get returns one item or an error wrapping ErrNotFound.
func (s Items) Get(ctx context.Context, id string) (item.Item, error) {
	it, err := s.Repo.Get(ctx, id)
	if err != nil {
		return item.Item{}, fmt.Errorf("get item %s: %w", id, err)
	}
	return it, nil
}
