// Package apperr is the business-error type: HTTP status, stable machine code, safe message.
// Infrastructure errors stay plain and become a generic 500 at the HTTP edge.
package apperr

import "errors"

// Error is a business error: an HTTP status, a stable machine code and a message that is safe to
// show.
type Error struct {
	Status    int
	Code      string // stable API contract: add codes, never rename
	Message   string
	Retryable bool
}

func (e *Error) Error() string {
	return e.Code + ": " + e.Message
}

// New builds an Error.
func New(status int, code, message string) *Error {
	return &Error{Status: status, Code: code, Message: message}
}

// As reports whether err is, or wraps, an *Error.
func As(err error) (*Error, bool) {
	var e *Error
	return e, errors.As(err, &e)
}
