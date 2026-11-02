use super::Loader;

/// REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD[_FILE] (see redis.env.example in the rust-infra
/// skill).
#[derive(Clone)]
pub struct Redis {
    pub host: String,
    pub port: u16,
    pub db: i64,
    pub password: String,
}

impl Redis {
    pub fn load(l: &mut Loader) -> Redis {
        Redis {
            host: l.req("REDIS_HOST"),
            port: l.num("REDIS_PORT", 6379),
            db: l.num("REDIS_DB", 0),
            password: l.secret("REDIS_PASSWORD"),
        }
    }
}
