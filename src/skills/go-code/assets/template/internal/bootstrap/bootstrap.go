// Package bootstrap is the composition root: the only place where concrete adapters meet use cases.
package bootstrap

import (
	"time"

	"github.com/google/uuid"

	"example.com/service/internal/application"
	"example.com/service/internal/config"
	"example.com/service/internal/infrastructure/kafkax"
	"example.com/service/internal/infrastructure/postgres"
	"example.com/service/internal/infrastructure/redisx"
	"example.com/service/internal/infrastructure/s3x"
	"example.com/service/internal/interfaces/httpapi"
)

// Runtime owns every concrete adapter and the use cases built on them.
type Runtime struct {
	DB       *postgres.Store
	Redis    *redisx.Client
	Producer *kafkax.Producer
	Objects  *s3x.Client
	Items    application.Items
}

// Open builds the adapters from configuration; call Close when done.
func Open(cfg config.Config) (*Runtime, error) {
	producer, err := kafkax.NewProducer(cfg.Kafka)
	if err != nil {
		return nil, err
	}
	db := postgres.Open(cfg.Postgres)
	return &Runtime{
		DB: db, Redis: redisx.Open(cfg.Redis), Producer: producer, Objects: s3x.Open(cfg.S3),
		Items: application.Items{Repo: db, Events: producer, NewID: uuid.NewString, Now: time.Now},
	}, nil
}

// Checks returns one health probe per dependency, shown by /healthz.
func (r *Runtime) Checks() []httpapi.Checker {
	return []httpapi.Checker{
		{Name: "postgres", Ping: r.DB.Ping}, {Name: "redis", Ping: r.Redis.Ping},
		{Name: "kafka", Ping: r.Producer.Ping}, {Name: "s3", Ping: r.Objects.Ping},
	}
}

// Close releases everything; the producer drains first.
func (r *Runtime) Close() {
	r.Producer.Close()
	_ = r.Redis.Close()
	_ = r.DB.Close()
}
