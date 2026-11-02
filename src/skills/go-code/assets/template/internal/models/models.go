// Package models is the JSON contract (also the Swagger source). Data only, no behaviour.
package models

// CreateItemRequest is the body of POST /v1/items.
type CreateItemRequest struct {
	Name string `json:"name" example:"pen"`
}

// ItemResponse is an item as returned by the API.
type ItemResponse struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	CreatedAt string `json:"created_at" example:"2026-01-02T03:04:05Z"`
}
