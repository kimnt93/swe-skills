# Rust + Redis (redis-rs ConnectionManager)

Adapter: `assets/template/crates/svc-infra/src/redis_lock.rs`; settings: `.../config/redis.rs`; env: `assets/env/redis.env.example` ([env-config](env-config.md)). Tested live in the scaffold.

`ConnectionManager` (auto-reconnect) cloned per task; password URL-encoded into the connection URL (never logged); lock = `SET key token NX
EX ttl`, release = Lua compare-and-delete; every key has a TTL; no `KEYS` (use `SCAN`); errors map to the kind only.


## Example usage

- “Add a per-account lock around the settlement job.”
