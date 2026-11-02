package httpapi

import (
	"context"
	"errors"
	"sync"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/rs/zerolog/log"

	"example.com/service/internal/interfaces/httpapi/middleware"
)

const (
	healthOK           = "ok"
	healthDown         = "down"
	healthCheckTimeout = 2 * time.Second
)

// Identity says who this process is. Every field is shown by /healthz.
type Identity struct {
	ServiceName    string
	EnvName        string
	NodeName       string
	ServiceVersion string
	StartedAt      time.Time

	// Config is the non-secret configuration worth seeing during an incident (config.Public()).
	Config map[string]any
}

// HealthCheck is the result of one dependency probe.
type HealthCheck struct {
	Name      string  `json:"name"`
	Status    string  `json:"status"`
	LatencyMS float64 `json:"latency_ms"`
	Error     string  `json:"error"`
}

// Health is the body of GET /healthz. Every field is always present.
type Health struct {
	Status         string         `json:"status"`
	ServiceName    string         `json:"service_name"`
	EnvName        string         `json:"env_name"`
	NodeName       string         `json:"node_name"`
	APIVersions    []string       `json:"api_versions"`
	ServiceVersion string         `json:"service_version"`
	StartedAt      string         `json:"started_at"`
	CheckedAt      string         `json:"checked_at"`
	UptimeSeconds  int64          `json:"uptime_seconds"`
	Config         map[string]any `json:"config"`
	Checks         []HealthCheck  `json:"checks"`
}

// healthHandler answers GET /healthz, the one health endpoint of the service: it is not
// versioned and lists every API version in api_versions. It is public (no token), never cached,
// and 503 when a registered dependency is down. A dependency the service can run without is not
// a check.
//
// @Summary  Health of the service
// @Tags     health
// @Success  200 {object} Health
// @Failure  503 {object} Health
// @Router   /healthz [get]
func healthHandler(id Identity, checks []Checker) fiber.Handler {
	return func(c fiber.Ctx) error {
		body := buildHealth(c.Context(), id, checks)

		status := fiber.StatusOK
		if body.Status != healthOK {
			status = fiber.StatusServiceUnavailable
		}

		c.Set(fiber.HeaderCacheControl, "no-store")

		return c.Status(status).JSON(body)
	}
}

// InternalHealth is the body of GET /internal: the same fields as Health plus the caller.
type InternalHealth struct {
	Health
	Caller middleware.Caller `json:"caller"`
}

// internalHandler answers GET /internal. The service token is required (InternalAuth runs first):
// 200 proves the token works and shows the identity this service received; 503 when a registered
// dependency is down.
//
// @Summary  Health of the service for an internal caller
// @Tags     internal
// @Security InternalServiceAuth
// @Success  200 {object} InternalHealth
// @Failure  401 {object} api.Envelope
// @Failure  503 {object} InternalHealth
// @Router   /internal [get]
func internalHandler(id Identity, checks []Checker) fiber.Handler {
	return func(c fiber.Ctx) error {
		body := InternalHealth{
			Health: buildHealth(c.Context(), id, checks),
			Caller: middleware.CallerFrom(c),
		}

		status := fiber.StatusOK
		if body.Status != healthOK {
			status = fiber.StatusServiceUnavailable
		}

		c.Set(fiber.HeaderCacheControl, "no-store")

		return c.Status(status).JSON(body)
	}
}

func buildHealth(ctx context.Context, id Identity, checks []Checker) Health {
	now := time.Now().UTC()
	results := runChecks(ctx, checks)

	status := healthOK
	for _, r := range results {
		if r.Status != healthOK {
			status = healthDown
		}
	}

	config := id.Config
	if config == nil {
		config = map[string]any{}
	}

	return Health{
		Status:         status,
		ServiceName:    id.ServiceName,
		EnvName:        id.EnvName,
		NodeName:       id.NodeName,
		APIVersions:    apiVersions,
		ServiceVersion: id.ServiceVersion,
		StartedAt:      id.StartedAt.UTC().Format(time.RFC3339),
		CheckedAt:      now.Format(time.RFC3339),
		UptimeSeconds:  int64(now.Sub(id.StartedAt).Seconds()),
		Config:         config,
		Checks:         results,
	}
}

// runChecks probes every dependency concurrently; the slice keeps the registration order.
func runChecks(ctx context.Context, checks []Checker) []HealthCheck {
	results := make([]HealthCheck, len(checks))

	var wg sync.WaitGroup
	for i, check := range checks {
		wg.Add(1)
		go func() {
			defer wg.Done()
			results[i] = runCheck(ctx, check)
		}()
	}
	wg.Wait()

	return results
}

func runCheck(ctx context.Context, check Checker) HealthCheck {
	ctx, cancel := context.WithTimeout(ctx, healthCheckTimeout)
	defer cancel()

	start := time.Now()
	err := check.Ping(ctx)
	result := HealthCheck{
		Name:      check.Name,
		Status:    healthOK,
		LatencyMS: float64(time.Since(start).Microseconds()) / 1000,
	}

	if err == nil {
		return result
	}

	// The response carries a short code, never the error text (it can hold a host or a DSN).
	log.Warn().Err(err).Str("check", check.Name).Msg("health check failed")
	result.Status = healthDown
	result.Error = "unavailable"
	if errors.Is(err, context.DeadlineExceeded) {
		result.Error = "timeout"
	}

	return result
}
