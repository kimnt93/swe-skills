# Python + Redis (redis-py asyncio)

*Verified with: redis-py 8 and Redis 8 in the scaffold template (live integration test, ruff and pycodestyle clean).*

Reference: `assets/template/src/service/db/redis.py`, `assets/template/src/service/settings/`, `assets/env/redis.env.example` (tested in the scaffold template). PEP 8 style (79
columns). Redis is a coordination and cache layer: **PostgreSQL stays the source of truth.**

## Environment (load from env)

```bash
# assets/env/redis.env.example
REDIS_HOST=127.0.0.1  REDIS_PORT=6379  REDIS_DB=0
REDIS_PASSWORD=       # SECRET: required, no default, never committed; Swarm: REDIS_PASSWORD_FILE
```

```python
from service.settings import RedisSettings         # assets/template/src/service/settings/redis.py (+ _base.py)

redis = RedisClient(RedisSettings())               # fails by variable name, never prints a value
```

## Rules

1. **One client per process** (`redis.asyncio.Redis`) with `socket_timeout`, `socket_connect_timeout`; close with `aclose()` in the
   lifespan. Never hard-code a host or password.
2. **Keys:** `<service>:<entity>:<id>[:<facet>]`, lower-case, bounded length. **Every key has a TTL** unless documented permanent;
   set it atomically (`set(key, v, ex=60)`, `nx=True` for locks).
3. **A miss is `None`, an outage is an exception:** degrade (skip the cache) or fail, never treat a connection error as "not found".
4. **Locks are token-owned:** `SET key token NX EX ttl`, release with the Lua compare-and-delete script (`RedisClient.lock`). A lock is an
   optimisation guard; money and state transitions need database row locks and idempotency keys.
5. **Atomic multi-step = Lua or `pipeline(transaction=True)`**; counters use `INCR`/`HINCRBY`, never GET-then-SET.
6. **No `KEYS`;** use `scan_iter(match=..., count=...)`. No unbounded `SMEMBERS`/`LRANGE 0 -1`.
7. **Serialisation:** `orjson`/`msgspec` bytes or hashes; version payloads that outlive a deploy; `decode_responses` only where values are
   text.
8. **Pub/sub is fire-and-forget:** anything that must not be lost goes through Kafka or a database row.
9. **Health:** `await r.ping()` is the `redis` check of `/healthz`.
10. Tests: `fakeredis` for unit tests; the integration run (`-m integration`) proves lock exclusivity, release and expiry on a real server.

## Example usage

- “Add a per-account lock around the settlement job.”
- “Cache the instrument list for 60 seconds and invalidate it on change.”
