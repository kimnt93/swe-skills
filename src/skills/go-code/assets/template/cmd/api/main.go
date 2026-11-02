// Command api serves the HTTP API: config -> logger -> adapters -> app -> graceful shutdown.
//
// The service listens on port 3000. Swagger UI is at /docs, the API at /v1 (and /v2 when it
// exists), and /healthz is the one health endpoint.
//
//	api            serve the API
//	api migrate    apply the goose files in schemas/ and exit (the one-shot migration job)
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v3"
	"github.com/rs/zerolog/log"

	"example.com/service/internal/bootstrap"
	"example.com/service/internal/config"
	"example.com/service/internal/infrastructure/postgres"
	"example.com/service/internal/interfaces/httpapi"
	"example.com/service/internal/logger"
)

// @title                      Example service API
// @version                    1.0
// @description                Versioned HTTP API: docs at /docs, health at /healthz.
// @BasePath                   /
// @securityDefinitions.apikey InternalServiceAuth
// @in                         header
// @name                       x-internal-service-token
func main() {
	command := run
	if len(os.Args) > 1 && os.Args[1] == "migrate" {
		command = migrate
	}

	if err := command(); err != nil {
		fmt.Fprintln(os.Stderr, "api:", err)
		os.Exit(1)
	}
}

// migrate applies the goose files once. It reads only the POSTGRES_* variables, so the job needs
// no Redis, Kafka or S3 settings.
func migrate() error {
	loader := config.NewLoader(nil)
	settings := config.LoadPostgres(loader)
	if err := loader.Err(); err != nil {
		return err
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	return postgres.Migrate(ctx, settings, "schemas")
}

func run() error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}
	if cfg.InternalServiceToken == "" {
		return fmt.Errorf("INTERNAL_SERVICE_TOKEN or INTERNAL_SERVICE_TOKEN_FILE is required")
	}

	// Reads SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME and LOG_LEVEL.
	if _, err := logger.ConfigureFromEnv(); err != nil {
		return err
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	rt, err := bootstrap.Open(cfg)
	if err != nil {
		return err
	}
	defer rt.Close()

	options := httpapi.Options{
		InternalServiceToken: cfg.InternalServiceToken,
		Identity: httpapi.Identity{
			ServiceName:    cfg.ServiceName,
			EnvName:        cfg.Environment,
			NodeName:       cfg.NodeName,
			ServiceVersion: cfg.ServiceVersion,
			StartedAt:      time.Now(),
			Config:         cfg.Public(),
		},
		Checks: rt.Checks(),
	}
	app := httpapi.NewApp(options, rt.Items)

	go func() {
		<-ctx.Done()

		// Finish in-flight requests, then Listen returns.
		_ = app.ShutdownWithTimeout(15 * time.Second)
	}()

	log.Info().Str("addr", cfg.HTTPAddr()).Msg("api listening")

	return app.Listen(cfg.HTTPAddr(), fiber.ListenConfig{DisableStartupMessage: true})
}
