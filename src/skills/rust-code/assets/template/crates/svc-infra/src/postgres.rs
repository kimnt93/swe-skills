//! PostgreSQL adapter: tokio-postgres + deadpool pool, plain parameterised SQL, rows mapped to
//! domain types here.

use deadpool_postgres::{Config as PoolConfig, ManagerConfig, Pool, RecyclingMethod, Runtime};
use svc_core::{config::Postgres as Settings, item::Item, ports::ItemRepository, Error, Result};
use tokio_postgres::NoTls;
use uuid::Uuid;

// One query per constant, written the way psql would run it: one clause per line, one column per
// line. No casts in the select list: rows are converted in Rust.
const INSERT_ITEM: &str = "
    INSERT INTO items (id, name, created_at)
    VALUES ($1, $2, $3)
";

const UPSERT_ITEM: &str = "
    INSERT INTO items (id, name, created_at)
    VALUES ($1, $2, $3)
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name
";

const GET_ITEM: &str = "
    SELECT
        id,
        name,
        created_at
    FROM items
    WHERE id = $1
";

#[derive(Clone)]
pub struct PgItems {
    pool: Pool,
}

fn storage(e: impl std::fmt::Display) -> Error {
    // The driver's message can include host and user names; keep it generic and log the cause where
    // it is handled.
    let _ = e;
    Error::Storage("database operation failed".into())
}

impl PgItems {
    /// TLS: swap `NoTls` for `tokio-postgres-rustls` / `postgres-native-tls` outside local
    /// development.
    pub fn open(s: &Settings, max_size: usize) -> Result<PgItems> {
        let mut cfg = PoolConfig::new();
        cfg.host = Some(s.host.clone());
        cfg.port = Some(s.port);
        cfg.dbname = Some(s.db.clone());
        cfg.user = Some(s.user.clone());
        cfg.password = Some(s.password.clone());
        cfg.manager = Some(ManagerConfig {
            recycling_method: RecyclingMethod::Fast,
        });
        cfg.pool = Some(deadpool_postgres::PoolConfig::new(max_size));
        let pool = cfg
            .create_pool(Some(Runtime::Tokio1), NoTls)
            .map_err(storage)?;
        Ok(PgItems { pool })
    }

    pub async fn ping(&self) -> Result<()> {
        let client = self.pool.get().await.map_err(storage)?;
        client.simple_query("SELECT 1").await.map_err(storage)?;
        Ok(())
    }

    /// Idempotent write: a replay converges on one row.
    pub async fn upsert(&self, item: &Item) -> Result<()> {
        let id = Uuid::parse_str(&item.id).map_err(storage)?;
        let client = self.pool.get().await.map_err(storage)?;
        client
            .execute(UPSERT_ITEM, &[&id, &item.name, &item.created_at])
            .await
            .map_err(storage)?;
        Ok(())
    }
}

impl ItemRepository for PgItems {
    async fn create(&self, item: &Item) -> Result<()> {
        let id = Uuid::parse_str(&item.id).map_err(storage)?;
        let client = self.pool.get().await.map_err(storage)?;
        client
            .execute(INSERT_ITEM, &[&id, &item.name, &item.created_at])
            .await
            .map_err(storage)?;
        Ok(())
    }

    async fn get(&self, id: &str) -> Result<Item> {
        let Ok(uuid) = Uuid::parse_str(id) else {
            return Err(Error::NotFound);
        };
        let client = self.pool.get().await.map_err(storage)?;
        let row = client
            .query_opt(GET_ITEM, &[&uuid])
            .await
            .map_err(storage)?
            .ok_or(Error::NotFound)?;
        Ok(Item {
            id: row.get::<_, Uuid>(0).to_string(),
            name: row.get(1),
            created_at: row.get(2),
        })
    }
}
