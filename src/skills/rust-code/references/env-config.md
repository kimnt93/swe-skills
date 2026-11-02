# Rust environment config (all infrastructure)

```bash
# assets/env/postgres.env.example
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 POSTGRES_DB=example POSTGRES_USER=example POSTGRES_POOL_SIZE=10
POSTGRES_PASSWORD=          # SECRET: required, no default, never committed; Swarm: POSTGRES_PASSWORD_FILE
# assets/env/redis.env.example
REDIS_HOST=127.0.0.1 REDIS_PORT=6379 REDIS_DB=0   REDIS_PASSWORD=   # SECRET, REDIS_PASSWORD_FILE
# assets/env/kafka.env.example
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092 KAFKA_SECURITY_PROTOCOL=PLAINTEXT KAFKA_CONSUMER_GROUP=example-service-local
KAFKA_SASL_MECHANISM=SCRAM-SHA-256 KAFKA_SASL_USERNAME= KAFKA_SASL_PASSWORD=   # SASL_* only; SECRET, KAFKA_SASL_PASSWORD_FILE
# assets/env/s3.env.example
S3_ENDPOINT=http://127.0.0.1:9000 S3_REGION=us-east-1 S3_BUCKET=example-local S3_FORCE_PATH_STYLE=true
S3_ACCESS_KEY= S3_SECRET_KEY=   # SECRETS, S3_ACCESS_KEY_FILE / S3_SECRET_KEY_FILE
```

```rust
let mut l = Loader::new(&|n| std::env::var(n).ok());      // assets/template/crates/svc-core/src/config/loader.rs
let pg = Postgres::load(&mut l);  let s3 = S3::load(&mut l);   // one `load` per infrastructure
l.finish()?;   // Err lists every missing/invalid variable by name, never a value
```

Rules for the config: a required variable is `req`, a defaulted one `str`/`num`/`flag`, a secret is `secret` (required, no default) or
`opt_secret` (SASL only, enforced with `fail`). Structs hold secrets as `String` but **`Debug` is manual** (derive would print them).
`.env.example` keeps every secret blank and is tested to load (`env_example_is_complete`).


## Checks

```bash
cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace
docker compose -f docker-compose.infra.local.yaml up -d postgres redis kafka rustfs && scripts/health.sh --wait postgres,redis,kafka,s3
set -a; . ./.env; set +a; cargo test -p svc-infra --features kafka -- --ignored --test-threads=1
```


