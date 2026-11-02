// Package handlers is thin: bind, call one use case, answer through the envelope. No rules, no SQL.
package handlers

import (
	"time"

	"github.com/gofiber/fiber/v3"

	"example.com/service/internal/application"
	"example.com/service/internal/domain/item"
	"example.com/service/internal/interfaces/httpapi/api"
	"example.com/service/internal/models"
)

// Items are the HTTP handlers for the items resource.
type Items struct {
	Svc application.Items
}

// Create godoc
// @Summary  Create an item
// @Tags     items
// @Security InternalServiceAuth
// @Param    body body models.CreateItemRequest true "item"
// @Success  201 {object} api.Envelope
// @Failure  422 {object} api.Envelope
// @Router   /v1/items [post]
func (h Items) Create(c fiber.Ctx) error {
	var req models.CreateItemRequest
	if err := c.Bind().Body(&req); err != nil {
		return api.InvalidJSON(c, err)
	}

	// c.Context() is the request context.Context.
	it, err := h.Svc.Create(c.Context(), req.Name)
	if err != nil {
		return api.SendResponse(c, 0, nil, err, "")
	}

	return api.SendResponse(c, fiber.StatusCreated, itemResponse(it), nil, "item created")
}

// Get godoc
// @Summary  Get an item
// @Tags     items
// @Security InternalServiceAuth
// @Param    id path string true "item id"
// @Success  200 {object} api.Envelope
// @Failure  404 {object} api.Envelope
// @Router   /v1/items/{id} [get]
func (h Items) Get(c fiber.Ctx) error {
	// Valid only during the request: copy (strings.Clone) before keeping it.
	id := c.Params("id")

	it, err := h.Svc.Get(c.Context(), id)
	if err != nil {
		return api.SendResponse(c, 0, nil, err, "")
	}

	return api.SendResponse(c, fiber.StatusOK, itemResponse(it), nil, "")
}

func itemResponse(it item.Item) models.ItemResponse {
	return models.ItemResponse{
		ID:        it.ID,
		Name:      it.Name,
		CreatedAt: it.CreatedAt.Format(time.RFC3339),
	}
}
