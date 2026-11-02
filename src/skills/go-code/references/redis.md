# Go + Redis (go-redis v9)

*Verified with: go-redis v9.23 on live Redis 8 (scaffold e2e lock test).*

Reference: `assets/template/internal/infrastructure/redisx/client.go`, `assets/template/internal/config/` (env loader), `assets/env/redis.env.example` (the same code is
compiled and tested in the scaffold template).

## Environment (load from env)

```bash
# assets/env/redis.env.example
REDIS_HOST=127.0.0.1   REDIS_PORT=6379   REDIS_DB=0   REDIS_POOL_SIZE=20
REDIS_PASSWORD=        # SECRET: required, no default, never committed; Swarm: REDIS_PASSWORD_FILE
```

```go
l := config.NewLoader(nil)            // assets/template/internal/config/loader.go
rcfg := config.LoadRedis(l)           // assets/template/internal/config/redis.go
if err := l.Err(); err != nil { return err }   // names every missing variable, never a value
rc := redisx.Open(rcfg)
```
 Redis is a coordination and cache
layer: **PostgreSQL stays the source of truth** unless the project says otherwise.

## Rules

1. **Client once, timeouts always.** One `redis.Client` per process from `config.Redis` (`REDIS_HOST/PORT/DB`,
   password from `REDIS_PASSWORD[_FILE]`, `REDIS_POOL_SIZE`); set `DialTimeout`, `ReadTimeout`, `WriteTimeout`, `PoolSize`.
   Close on shutdown. Never hard-code an address or password.
2. **Every call takes `ctx`** and uses a deadline (`context.WithTimeout`) when it sits on a request path.
3. **Keys:** `<service>:<entity>:<id>[:<facet>]`, lower-case, no user-controlled raw strings without a length limit.
   **Every key has a TTL** unless it is documented as permanent; set it atomically (`SET key v EX 60`, `SetNX`).
4. **Missing is not an error:** `errors.Is(err, redis.Nil)` -> cache miss. Any other error is an outage: degrade
   (skip the cache) or fail the request, but never treat it as "not found" in the database sense.
5. **Locks are token-owned.** `SetNX(key, token, ttl)` to acquire; release with the Lua compare-and-delete script
   (`redisx.Client.Lock`). Release with a fresh short context (the request context may already be cancelled). A lock is
   an optimisation guard, not a correctness guarantee: money/state transitions need database row locks and idempotency
   keys. Keep TTL longer than the critical section and never extend by guesswork.
6. **Multi-step = Lua or `TxPipeline`.** Use `redis.NewScript` (cached by SHA) for read-modify-write; use pipelines
   (`rdb.Pipeline()`, `TxPipeline()`) to batch commands. Never `GET` then `SET` for a counter (`INCR`/`HINCRBY`).
7. **No `KEYS`.** Use `SCAN` with a count, or maintain an index set. No unbounded `SMEMBERS`/`LRANGE 0 -1` on big keys.
8. **Serialisation:** compact JSON (`sonic`/stdlib) or a hash; version the payload when it outlives a deploy. Cached structs follow
   the house rules: plain values, no pointers, no `omitempty` (a zero value is a value).
9. **Pub/sub is fire-and-forget** (wake-ups, cache invalidation). Anything that must not be lost uses a Kafka topic or a
   database row, with the Redis message only nudging the consumer.
10. **Health:** `Ping(ctx)` is the `redis` check of `/healthz`.

## Testing

Unit tests use a fake behind your own interface. Concurrency and TTL behaviour need a real Redis
(`-tags integration`, `docker-compose.infra.local.yaml`): assert exclusivity (a second `Lock` fails), release, and expiry.

## Tracing

`redisotel.InstrumentTracing(rdb)` (go-redis extra) or `PeerSpan(ctx, "redis", "get")` from `service-tracing`.

## Example usage

- “Add a per-account lock around the settlement job.”
- “Cache the instrument list for 60 seconds and invalidate it on change.”
