package config

import (
	"os"
	"strconv"
)

// Config composes the per-infrastructure sections. A service that does not use one deletes its line
// (and its file).
type Config struct {
	ServiceName, Environment, NodeName, ServiceVersion, LogLevel string
	HTTPPort                                                     int
	InternalServiceToken                                         string
	Postgres                                                     Postgres
	Redis                                                        Redis
	Kafka                                                        Kafka
	S3                                                           S3
}

// DefaultPort is the port every HTTP service listens on, in every environment.
const DefaultPort = 3000

// Load reads and validates the whole environment; the error lists every problem by variable name.
func Load() (Config, error) {
	return LoadWith(NewLoader(nil))
}

// LoadWith reads the whole configuration through l and returns every problem found, by variable
// name.
func LoadWith(l *Loader) (Config, error) {
	cfg := Config{
		ServiceName: l.Req("SERVICE_NAME"),

		// Same order as the log format: DEVELOPMENT_ENVIRONMENT, ENV_NAME, then the deploy RUN_ENV.
		Environment:          l.First("local", "DEVELOPMENT_ENVIRONMENT", "ENV_NAME", "RUN_ENV"),
		NodeName:             l.Str("NODE_NAME", hostname()),
		ServiceVersion:       l.Str("SERVICE_VERSION", ""),
		LogLevel:             l.Str("LOG_LEVEL", "info"),
		HTTPPort:             l.Int("PORT", DefaultPort),
		InternalServiceToken: l.Secret("INTERNAL_SERVICE_TOKEN"),
		Postgres:             LoadPostgres(l),
		Redis:                LoadRedis(l),
		Kafka:                LoadKafka(l),
		S3:                   LoadS3(l),
	}
	return cfg, l.Err()
}

// HTTPAddr is the listen address for HTTPPort.
func (c Config) HTTPAddr() string {
	return ":" + strconv.Itoa(c.HTTPPort)
}

// Public is the non-secret configuration that /healthz shows. Add a key on purpose; never
// copy the environment, a connection string or a secret into it.
func (c Config) Public() map[string]any {
	return map[string]any{
		"port":      c.HTTPPort,
		"log_level": c.LogLevel,
	}
}

func hostname() string {
	name, err := os.Hostname()
	if err != nil {
		return ""
	}

	return name
}
