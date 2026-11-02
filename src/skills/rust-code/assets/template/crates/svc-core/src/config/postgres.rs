use super::Loader;

/// POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD[_FILE],
/// POSTGRES_POOL_SIZE (see postgres.env.example in the rust-infra skill).
#[derive(Clone)]
pub struct Postgres {
    pub host: String,
    pub port: u16,
    pub db: String,
    pub user: String,
    pub password: String,
    pub pool_size: usize,
}

impl Postgres {
    pub fn load(l: &mut Loader) -> Postgres {
        Postgres {
            host: l.req("POSTGRES_HOST"),
            port: l.num("POSTGRES_PORT", 5432),
            db: l.req("POSTGRES_DB"),
            user: l.req("POSTGRES_USER"),
            password: l.secret("POSTGRES_PASSWORD"),
            pool_size: l.num("POSTGRES_POOL_SIZE", 10),
        }
    }
}
