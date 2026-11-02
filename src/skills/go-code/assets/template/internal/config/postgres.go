package config

// Postgres is loaded from POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER,
// POSTGRES_PASSWORD[_FILE], POSTGRES_SSLMODE and POSTGRES_POOL_SIZE (see postgres.env.example in
// the go-postgres skill).
type Postgres struct {
	Host, Database, User, Password, SSLMode string
	Port, PoolSize                          int
}

// LoadPostgres reads the POSTGRES_* variables.
func LoadPostgres(l *Loader) Postgres {
	return Postgres{
		Host:     l.Req("POSTGRES_HOST"),
		Port:     l.Int("POSTGRES_PORT", 5432),
		Database: l.Req("POSTGRES_DB"),
		User:     l.Req("POSTGRES_USER"),
		Password: l.Secret("POSTGRES_PASSWORD"),
		SSLMode:  l.Str("POSTGRES_SSLMODE", "require"),
		PoolSize: l.Int("POSTGRES_POOL_SIZE", 20),
	}
}
