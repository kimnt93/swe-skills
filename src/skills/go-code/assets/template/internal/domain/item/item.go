// Package item is pure domain: no I/O, no framework, no logging, no time.Now (inject Now).
package item

import (
	"errors"
	"strings"
	"time"
)

// ErrInvalidName reports a name that is empty or longer than 120 characters.
var ErrInvalidName = errors.New("item name must be 1-120 characters")

// Item is the aggregate: an identified, named record created at a UTC instant.
type Item struct {
	ID        string
	Name      string
	CreatedAt time.Time
}

// New validates and normalises; callers inject the id and the clock.
func New(id, name string, now time.Time) (Item, error) {
	name = strings.TrimSpace(name)
	if name == "" || len(name) > 120 {
		return Item{}, ErrInvalidName
	}
	return Item{ID: id, Name: name, CreatedAt: now.UTC()}, nil
}
