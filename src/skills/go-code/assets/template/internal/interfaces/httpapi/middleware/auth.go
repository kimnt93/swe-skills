// Package middleware holds request-scoped concerns. Order is fixed in server.go: logging -> auth ->
// handler.
package middleware

import (
	"crypto/subtle"
	"strings"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/rs/zerolog/log"

	"example.com/service/internal/domain/apperr"
	"example.com/service/internal/interfaces/httpapi/api"
)

// Caller is who the calling service says it acts for (x-user-id, x-username). Trust it only after
// InternalAuth passed; both are "" when the caller sent nothing.
type Caller struct {
	UserID   string `json:"user_id"`
	Username string `json:"username"`
}

const maxCallerLen = 128

// CallerFrom reads the identity headers, trimmed and capped at 128 characters.
func CallerFrom(c fiber.Ctx) Caller {
	return Caller{
		UserID:   clip(c.Get("x-user-id")),
		Username: clip(c.Get("x-username")),
	}
}

func clip(value string) string {
	value = strings.TrimSpace(value)
	if len(value) > maxCallerLen {
		value = value[:maxCallerLen]
	}

	return value
}

// bareToken drops an optional "Bearer " prefix: both header forms are valid.
func bareToken(value string) string {
	value = strings.TrimSpace(value)
	if len(value) >= 7 && strings.EqualFold(value[:7], "bearer ") {
		value = strings.TrimSpace(value[7:])
	}

	return value
}

// InternalAuth checks the shared service token in constant time. It accepts the token alone or with
// a Bearer prefix. Never log it.
func InternalAuth(token string) fiber.Handler {
	want := []byte(token)

	return func(c fiber.Ctx) error {
		got := []byte(bareToken(c.Get("x-internal-service-token")))

		if len(want) == 0 || subtle.ConstantTimeCompare(got, want) != 1 {
			denied := apperr.New(401, "unauthorized", "missing or invalid service token")

			return api.SendResponse(c, 401, nil, denied, "")
		}

		return c.Next()
	}
}

// RequestLog writes one line per request after the handler (it needs the final status).
func RequestLog() fiber.Handler {
	return func(c fiber.Ctx) error {
		start := time.Now()
		err := c.Next()

		status := c.Response().StatusCode()

		event := log.Info()
		if status >= 500 {
			event = log.Error()
		} else if status >= 400 {
			event = log.Warn()
		}

		event.
			Str("method", c.Method()).
			Str("path", routePath(c)).
			Int("status_code", status).
			Dur("duration", time.Since(start)).
			Msg("request completed")

		return err
	}
}

// routePath logs the route template (/v1/items/:id), not the raw URL: bounded cardinality, no ids
// in logs.
func routePath(c fiber.Ctx) string {
	if r := c.Route(); r != nil && r.Path != "" {
		return strings.TrimSpace(r.Path)
	}
	return "unmatched"
}
