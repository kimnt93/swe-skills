//! The only reader of environment variables. Names follow the deployment contract (POSTGRES_*,
//! REDIS_*, KAFKA_*, S3_*). A secret comes from NAME or from the file named by NAME_FILE (a mounted
//! Swarm secret) and has NO default. Errors name the variable and never print a value; `Debug` on
//! every settings struct hides secrets.

mod kafka;
mod loader;
mod postgres;
mod redis;
mod s3;

pub use kafka::Kafka;
pub use loader::Loader;
pub use postgres::Postgres;
pub use redis::Redis;
pub use s3::S3;

use crate::Result;

/// Composes the per-infrastructure sections. A service that does not use one deletes its module and
/// its line here.
#[derive(Clone)]
pub struct Config {
    pub service_name: String,
    /// DEVELOPMENT_ENVIRONMENT, else ENV_NAME, else RUN_ENV (the log format's order); the middle
    /// label of the public host.
    pub env_name: String,
    pub node_name: String,
    pub service_version: String,
    pub log_level: String,
    /// Every HTTP service listens on 3000.
    pub port: u16,
    pub internal_service_token: String,
    pub postgres: Postgres,
    pub redis: Redis,
    pub kafka: Kafka,
    pub s3: S3,
}

impl std::fmt::Debug for Config {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Config")
            .field("service_name", &self.service_name)
            .field("port", &self.port)
            .finish_non_exhaustive()
    }
}

pub const DEFAULT_PORT: u16 = 3000;

impl Config {
    /// The listen address for `port`.
    pub fn http_addr(&self) -> String {
        format!("0.0.0.0:{}", self.port)
    }

    /// The non-secret configuration that `/healthz` shows. Add a key on purpose; never
    /// copy the environment, a connection string or a secret into it.
    pub fn public(&self) -> serde_json::Map<String, serde_json::Value> {
        let mut map = serde_json::Map::new();
        map.insert("port".into(), self.port.into());
        map.insert("log_level".into(), self.log_level.clone().into());
        map
    }
}

/// Reads the whole configuration through `get` (tests pass a map; production passes the process
/// environment).
pub fn load_with(get: impl Fn(&str) -> Option<String>) -> Result<Config> {
    let mut l = Loader::new(&get);
    let cfg = Config {
        service_name: l.req("SERVICE_NAME"),
        env_name: l.first(&["DEVELOPMENT_ENVIRONMENT", "ENV_NAME", "RUN_ENV"], "local"),
        node_name: l.str("NODE_NAME", ""),
        service_version: l.str("SERVICE_VERSION", ""),
        log_level: l.str("LOG_LEVEL", "info"),
        port: l.num("PORT", DEFAULT_PORT),
        internal_service_token: l.secret("INTERNAL_SERVICE_TOKEN"),
        postgres: Postgres::load(&mut l),
        redis: Redis::load(&mut l),
        kafka: Kafka::load(&mut l),
        s3: S3::load(&mut l),
    };
    l.finish()?;
    Ok(cfg)
}

/// Reads the process environment.
pub fn load() -> Result<Config> {
    load_with(|name| std::env::var(name).ok())
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used)]
mod tests;
