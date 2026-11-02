package config

import (
	"fmt"
	"os"
	"strings"
	"testing"
)

func envMap(extra map[string]string) func(string) string {
	m := map[string]string{
		"SERVICE_NAME":            "svc",
		"INTERNAL_SERVICE_TOKEN":  "tok",
		"POSTGRES_HOST":           "pg",
		"POSTGRES_DB":             "db",
		"POSTGRES_USER":           "u",
		"POSTGRES_PASSWORD":       "p",
		"REDIS_HOST":              "r",
		"REDIS_PASSWORD":          "p",
		"KAFKA_BOOTSTRAP_SERVERS": "k:9092",
		"KAFKA_CONSUMER_GROUP":    "g",
		"S3_ENDPOINT":             "http://s3:9000",
		"S3_BUCKET":               "b",
		"S3_ACCESS_KEY":           "a",
		"S3_SECRET_KEY":           "s",
	}
	for k, v := range extra {
		if v == "" {
			delete(m, k)
		} else {
			m[k] = v
		}
	}

	return func(name string) string {
		return m[name]
	}
}

func TestLoadDefaults(t *testing.T) {
	cfg, err := LoadWith(NewLoader(envMap(nil)))
	if err != nil {
		t.Fatal(err)
	}

	if cfg.Postgres.Port != 5432 {
		t.Fatalf("postgres port default: %+v", cfg.Postgres)
	}
	if cfg.Redis.Port != 6379 {
		t.Fatalf("redis port default: %+v", cfg.Redis)
	}
	if cfg.HTTPPort != 3000 || cfg.HTTPAddr() != ":3000" {
		t.Fatalf("http port default: %d %q", cfg.HTTPPort, cfg.HTTPAddr())
	}
	if cfg.Environment != "local" {
		t.Fatalf("environment default: %q", cfg.Environment)
	}
	if !cfg.S3.ForcePathStyle || cfg.S3.Region != "us-east-1" {
		t.Fatalf("s3 defaults: %+v", cfg.S3)
	}
}

func TestEverySecretIsRequiredByName(t *testing.T) {
	secrets := []string{
		"POSTGRES_PASSWORD",
		"REDIS_PASSWORD",
		"S3_ACCESS_KEY",
		"S3_SECRET_KEY",
		"INTERNAL_SERVICE_TOKEN",
	}

	for _, name := range secrets {
		_, err := LoadWith(NewLoader(envMap(map[string]string{name: ""})))
		if err == nil || !strings.Contains(err.Error(), name) {
			t.Fatalf("a missing %s must fail by name, got %v", name, err)
		}
	}
}

func TestOneErrorListsEveryProblemAndNoValues(t *testing.T) {
	broken := map[string]string{
		"POSTGRES_HOST":       "",
		"REDIS_PORT":          "x",
		"S3_FORCE_PATH_STYLE": "maybe",
	}

	_, err := LoadWith(NewLoader(envMap(broken)))
	for _, want := range []string{"POSTGRES_HOST", "REDIS_PORT", "S3_FORCE_PATH_STYLE"} {
		if err == nil || !strings.Contains(err.Error(), want) {
			t.Fatalf("error must mention %s: %v", want, err)
		}
	}
	if strings.Contains(err.Error(), "tok") {
		t.Fatal("errors must never print values")
	}
}

func TestSecretFromFile(t *testing.T) {
	f := t.TempDir() + "/pw"
	_ = os.WriteFile(f, []byte("s3cret\n"), 0o600)

	env := map[string]string{
		"POSTGRES_PASSWORD":      "",
		"POSTGRES_PASSWORD_FILE": f,
	}

	cfg, err := LoadWith(NewLoader(envMap(env)))
	if err != nil || cfg.Postgres.Password != "s3cret" {
		t.Fatalf("pw=%q err=%v", cfg.Postgres.Password, err)
	}
}

func TestKafkaSASLNeedsCredentials(t *testing.T) {
	_, err := LoadWith(NewLoader(envMap(map[string]string{"KAFKA_SECURITY_PROTOCOL": "sasl_ssl"})))
	if err == nil || !strings.Contains(err.Error(), "KAFKA_SASL_USERNAME") {
		t.Fatalf("SASL without credentials must fail: %v", err)
	}

	withCredentials := map[string]string{
		"KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
		"KAFKA_SASL_USERNAME":     "u",
		"KAFKA_SASL_PASSWORD":     "p",
	}

	_, err = LoadWith(NewLoader(envMap(withCredentials)))
	if err != nil {
		t.Fatal(err)
	}
}

// The env example must be loadable: every variable the loaders read is documented, and nothing else
// is required.
func TestEnvExampleIsComplete(t *testing.T) {
	raw, err := os.ReadFile("../../.env.example")
	if err != nil {
		t.Fatal(err)
	}
	vars := map[string]string{}
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		k, v, _ := strings.Cut(line, "=")

		isSecret := strings.HasSuffix(k, "PASSWORD") ||
			strings.HasSuffix(k, "TOKEN") ||
			strings.HasSuffix(k, "KEY")

		if isSecret {
			if v != "" {
				t.Fatalf("%s must be blank in the example: secrets have no default", k)
			}
			v = "dummy-secret"
		}
		vars[k] = v
	}

	lookup := func(name string) string {
		return vars[name]
	}

	if _, err := LoadWith(NewLoader(lookup)); err != nil {
		t.Fatalf(".env.example does not load: %v", err)
	}
}

func TestEnvironmentNameOrder(t *testing.T) {
	for _, tc := range []struct {
		name string
		env  map[string]string
		want string
	}{
		{"all three", map[string]string{
			"DEVELOPMENT_ENVIRONMENT": "dev", "ENV_NAME": "stg", "RUN_ENV": "prod",
		}, "dev"},
		{"env name over run env", map[string]string{"ENV_NAME": "stg", "RUN_ENV": "prod"}, "stg"},
		{"run env only", map[string]string{"RUN_ENV": "prod"}, "prod"},
		{"none", nil, "local"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			cfg, err := LoadWith(NewLoader(envMap(tc.env)))
			if err != nil {
				t.Fatal(err)
			}
			if cfg.Environment != tc.want {
				t.Fatalf("environment = %q, want %q", cfg.Environment, tc.want)
			}
		})
	}
}

func TestPublicConfigHasNoSecrets(t *testing.T) {
	cfg, err := LoadWith(NewLoader(envMap(nil)))
	if err != nil {
		t.Fatal(err)
	}
	for key, value := range cfg.Public() {
		text := key + fmt.Sprint(value)
		for _, secret := range []string{"tok", "POSTGRES_PASSWORD"} {
			if strings.Contains(text, secret) {
				t.Fatalf("public config leaks %q in %s", secret, key)
			}
		}
	}
}
