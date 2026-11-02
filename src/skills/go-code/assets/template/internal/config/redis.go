package config

// Redis is loaded from REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD[_FILE], REDIS_POOL_SIZE
// (see redis.env.example in the go-redis skill).
type Redis struct {
	Host, Password     string
	Port, DB, PoolSize int
}

// LoadRedis reads the REDIS_* variables.
func LoadRedis(l *Loader) Redis {
	return Redis{
		Host:     l.Req("REDIS_HOST"),
		Port:     l.Int("REDIS_PORT", 6379),
		DB:       l.Int("REDIS_DB", 0),
		Password: l.Secret("REDIS_PASSWORD"),
		PoolSize: l.Int("REDIS_POOL_SIZE", 20),
	}
}
