// Package config is the only place that reads environment variables. Names follow the deployment
// contract (POSTGRES_*, REDIS_*, KAFKA_*, S3_*). A secret comes from NAME or from the file named by
// NAME_FILE (a mounted Swarm secret) and has NO default. Errors name the variable and never print a
// value.
package config

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// Loader reads variables through `get` (os.Getenv by default; a map in tests) and collects every
// problem, so one start-up error lists all missing variables instead of failing one at a time.
type Loader struct {
	get  func(string) string
	errs []error
}

// NewLoader reads variables through get; a nil get uses os.Getenv.
func NewLoader(get func(string) string) *Loader {
	if get == nil {
		get = os.Getenv
	}
	return &Loader{get: get}
}

// Req returns a required, non-empty variable.
func (l *Loader) Req(name string) string {
	v := strings.TrimSpace(l.get(name))
	if v == "" {
		l.errs = append(l.errs, fmt.Errorf("%s is required", name))
	}
	return v
}

// Str returns the variable or def when unset/empty.
func (l *Loader) Str(name, def string) string {
	if v := strings.TrimSpace(l.get(name)); v != "" {
		return v
	}
	return def
}

// First returns the first non-empty variable among names, or def.
func (l *Loader) First(def string, names ...string) string {
	for _, name := range names {
		if v := strings.TrimSpace(l.get(name)); v != "" {
			return v
		}
	}
	return def
}

// Int returns the variable as an integer, or def when unset; a non-integer is recorded as an error.
func (l *Loader) Int(name string, def int) int {
	raw := strings.TrimSpace(l.get(name))
	if raw == "" {
		return def
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		l.errs = append(l.errs, fmt.Errorf("%s must be an integer", name))
		return def
	}
	return n
}

// Bool returns the variable as a boolean (true/false/1/0/yes/no/on/off), or def when unset.
func (l *Loader) Bool(name string, def bool) bool {
	raw := strings.ToLower(strings.TrimSpace(l.get(name)))
	switch raw {
	case "":
		return def
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	}
	l.errs = append(l.errs, fmt.Errorf("%s must be true or false", name))
	return def
}

// Secret is required: NAME, else the contents of the file named by NAME_FILE. No default, ever.
func (l *Loader) Secret(name string) string {
	v, err := l.secret(name)
	if err != nil {
		l.errs = append(l.errs, err)
	} else if v == "" {
		l.errs = append(l.errs, fmt.Errorf("%s or %s_FILE is required", name, name))
	}
	return v
}

// OptSecret is for secrets that are required only in some modes (Kafka SASL); the caller enforces
// the mode.
func (l *Loader) OptSecret(name string) string {
	v, err := l.secret(name)
	if err != nil {
		l.errs = append(l.errs, err)
	}
	return v
}

// Fail records a cross-field validation error.
func (l *Loader) Fail(format string, args ...any) {
	l.errs = append(l.errs, fmt.Errorf(format, args...))
}

// Err returns every recorded problem joined into one error, or nil.
func (l *Loader) Err() error {
	return errors.Join(l.errs...)
}

func (l *Loader) secret(name string) (string, error) {
	if v := strings.TrimSpace(l.get(name)); v != "" {
		return v, nil
	}
	if path := l.get(name + "_FILE"); path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			return "", fmt.Errorf("%s_FILE: %w", name, err)
		}
		return strings.TrimSpace(string(b)), nil
	}
	return "", nil
}
