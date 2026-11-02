// Package redisx wraps go-redis v9: client construction, health and a token-owned lock.
package redisx

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"net"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"

	"example.com/service/internal/config"
)

// Client wraps go-redis with the service configuration.
type Client struct {
	rdb *redis.Client
}

// Open builds the client; it connects lazily on first use.
func Open(c config.Redis) *Client {
	return &Client{rdb: redis.NewClient(&redis.Options{
		Addr:         net.JoinHostPort(c.Host, strconv.Itoa(c.Port)),
		Password:     c.Password,
		DB:           c.DB,
		DialTimeout:  5 * time.Second,
		ReadTimeout:  3 * time.Second,
		WriteTimeout: 3 * time.Second,
		PoolSize:     c.PoolSize,
	})}
}

// Ping checks that Redis answers.
func (c *Client) Ping(ctx context.Context) error {
	return c.rdb.Ping(ctx).Err()
}

// Close closes the connection pool.
func (c *Client) Close() error {
	return c.rdb.Close()
}

// releaseScript deletes the key only if we still own it (compare-and-delete is atomic in Lua).
var releaseScript = redis.NewScript(`
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
`)

// ReleaseFunc releases a lock taken with Lock.
type ReleaseFunc func(ctx context.Context) error

// Lock takes `key` for ttl. ok=false means someone else holds it. Always call release (defer), with
// a context that survives cancellation of the request.
func (c *Client) Lock(
	ctx context.Context,
	key string,
	ttl time.Duration,
) (release ReleaseFunc, ok bool, err error) {
	buf := make([]byte, 16)
	if _, err = rand.Read(buf); err != nil {
		return nil, false, err
	}
	token := hex.EncodeToString(buf)

	ok, err = c.rdb.SetNX(ctx, key, token, ttl).Result()
	if err != nil || !ok {
		return nil, false, err
	}

	release = func(releaseCtx context.Context) error {
		return releaseScript.Run(releaseCtx, c.rdb, []string{key}, token).Err()
	}

	return release, true, nil
}
