// Package api is the response envelope, error mapping and request-context getters. Handlers use
// only these.
package api

import (
	"errors"

	"github.com/gofiber/fiber/v3"
	"github.com/rs/zerolog/log"

	"example.com/service/internal/application"
	"example.com/service/internal/domain/apperr"
	"example.com/service/internal/domain/item"
)

// Envelope is the response body. Every field is always present with its zero value (no omitempty,
// no pointers): `data` is null and `error` is {"code":"","retryable":false} when unused, so clients
// never branch on absence.
type Envelope struct {
	Success    bool      `json:"success"`
	StatusCode int       `json:"status_code"`
	Message    string    `json:"message"`
	Data       any       `json:"data"`
	Error      ErrorBody `json:"error"`
}

// ErrorBody is the machine-readable part of an error response.
type ErrorBody struct {
	Code      string `json:"code"`
	Retryable bool   `json:"retryable"`
}

// SendResponse is the only way a handler answers: success data or a mapped error.
func SendResponse(c fiber.Ctx, status int, data any, err error, message string) error {
	if err != nil {
		return sendError(c, err)
	}

	return c.Status(status).JSON(Envelope{
		Success:    true,
		StatusCode: status,
		Message:    message,
		Data:       data,
	})
}

// InvalidJSON answers 400 invalid_json.
func InvalidJSON(c fiber.Ctx, err error) error {
	e := apperr.New(fiber.StatusBadRequest, "invalid_json", "request body is not valid JSON")

	return sendError(c, e)
}

// Map turns domain/application sentinels into API errors; anything unknown becomes a generic 500.
func Map(err error) *apperr.Error {
	if e, ok := apperr.As(err); ok {
		return e
	}
	switch {
	case errors.Is(err, item.ErrInvalidName):
		return apperr.New(fiber.StatusUnprocessableEntity, "validation_error", err.Error())
	case errors.Is(err, application.ErrNotFound):
		return apperr.New(fiber.StatusNotFound, "not_found", "resource not found")
	}
	return nil
}

func sendError(c fiber.Ctx, err error) error {
	e := Map(err)
	if e == nil {
		// Log the cause; never return it: infrastructure errors can carry DSNs, SQL or payloads.
		log.Ctx(c.Context()).Error().Err(err).Msg("unhandled error")
		e = apperr.New(fiber.StatusInternalServerError, "internal_error", "internal error")
	}

	return c.Status(e.Status).JSON(Envelope{
		StatusCode: e.Status,
		Message:    e.Message,
		Error:      ErrorBody{Code: e.Code, Retryable: e.Retryable},
	})
}

// ErrorHandler is fiber.Config.ErrorHandler: framework errors (404, 405, body too large) use the
// same envelope.
func ErrorHandler(c fiber.Ctx, err error) error {
	status := fiber.StatusInternalServerError
	var fe *fiber.Error
	if errors.As(err, &fe) {
		status = fe.Code
	}

	codes := map[int]string{
		fiber.StatusNotFound:              "not_found",
		fiber.StatusMethodNotAllowed:      "method_not_allowed",
		fiber.StatusRequestEntityTooLarge: "payload_too_large",
	}

	code := codes[status]
	if code == "" {
		code = "internal_error"
	}

	return c.Status(status).JSON(Envelope{
		StatusCode: status,
		Message:    "request failed",
		Error:      ErrorBody{Code: code},
	})
}
