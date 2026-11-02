// Package httpapi assembles the Fiber app: engine config, middleware order, docs, health and the
// only route table.
package httpapi

import (
	"context"
	"time"

	"github.com/bytedance/sonic"
	"github.com/gofiber/fiber/v3"

	"example.com/service/internal/application"
	"example.com/service/internal/interfaces/httpapi/api"
	"example.com/service/internal/interfaces/httpapi/handlers"
	"example.com/service/internal/interfaces/httpapi/middleware"
)

// Checker is a health probe for one dependency (Postgres, Redis, Kafka) that the service cannot
// work without.
type Checker struct {
	Name string
	Ping func(context.Context) error
}

// Options configures the HTTP app.
type Options struct {
	InternalServiceToken string
	Identity             Identity
	Checks               []Checker
}

// apiVersions are the versions this service serves, listed by /healthz. Add "v2" here and
// register its routes in registerV2 (health is one endpoint, /healthz, not one per version).
var apiVersions = []string{"v1"}

// NewApp assembles the Fiber app: engine settings, middleware order, docs, health and the route
// table.
func NewApp(o Options, items application.Items) *fiber.App {
	app := fiber.New(fiber.Config{
		ErrorHandler: api.ErrorHandler,

		// Fast JSON on the hot path; stdlib is the default if you drop these two lines.
		JSONEncoder: sonic.Marshal,
		JSONDecoder: sonic.Unmarshal,

		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		BodyLimit:    1 << 20,
	})

	// RequestLog wraps everything after it, so it sees the final status.
	app.Use(middleware.RequestLog())

	registerDocs(app)

	// Public and unversioned, like /docs: registered before any auth middleware.
	identity := o.Identity
	identity.Config = withDocs(identity.Config)
	app.Get("/healthz", healthHandler(identity, o.Checks))

	// Same body behind the service token, plus the caller: proves internal auth works.
	auth := middleware.InternalAuth(o.InternalServiceToken)
	app.Get("/internal", auth, internalHandler(identity, o.Checks))

	registerV1(app, o, items)

	return app
}

// registerV1 mounts /v1. Everything in it needs the service token; /docs and /healthz are
// registered outside the group and stay public, /internal outside it with its own token check.
func registerV1(app *fiber.App, o Options, items application.Items) {
	v1 := app.Group("/v1")
	v1.Use(middleware.InternalAuth(o.InternalServiceToken))

	h := handlers.Items{Svc: items}
	v1.Post("/items", h.Create)
	v1.Get("/items/:id", h.Get)
}

func withDocs(config map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range config {
		out[key] = value
	}
	out["docs_url"] = "/docs"

	return out
}
