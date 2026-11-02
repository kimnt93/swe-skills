// Package application holds use cases and the ports they need. It never imports infrastructure or
// interfaces.
package application

import (
	"context"
	"errors"

	"example.com/service/internal/domain/item"
)

// ErrNotFound reports a missing resource; repositories return it so the HTTP edge can map it to
// 404.
var ErrNotFound = errors.New("not found")

// ItemRepository is declared where it is used and kept as small as the caller needs.
type ItemRepository interface {
	Create(ctx context.Context, it item.Item) error
	Get(ctx context.Context, id string) (item.Item, error)
}

// EventPublisher publishes domain events (Kafka in production).
type EventPublisher interface {
	Publish(ctx context.Context, topic string, key string, value []byte) error
}
