//! Redis adapter: connection manager with reconnect, token-owned lock (compare-and-delete in Lua),
//! health.

use redis::{aio::ConnectionManager, AsyncCommands, Script};
use svc_core::{config::Redis as Settings, Error, Result};

// Compare-and-delete in Lua: delete the key only if we still own it.
const UNLOCK_SCRIPT: &str = "
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
";

#[derive(Clone)]
pub struct Redis {
    conn: ConnectionManager,
}

fn cache(e: redis::RedisError) -> Error {
    // The kind only: messages can include addresses.
    Error::Storage(format!("redis: {:?}", e.kind()))
}

impl Redis {
    pub async fn open(s: &Settings) -> Result<Redis> {
        let url = format!(
            "redis://:{}@{}:{}/{}",
            urlencode(&s.password),
            s.host,
            s.port,
            s.db
        );
        let client = redis::Client::open(url).map_err(cache)?;
        Ok(Redis {
            conn: ConnectionManager::new(client).await.map_err(cache)?,
        })
    }

    pub async fn ping(&self) -> Result<()> {
        let mut c = self.conn.clone();
        let pong: String = redis::cmd("PING")
            .query_async(&mut c)
            .await
            .map_err(cache)?;
        if pong == "PONG" {
            Ok(())
        } else {
            Err(Error::Storage("redis: unexpected ping reply".into()))
        }
    }

    /// `Some(token)` when acquired, `None` when someone else holds `key`. A lock is an optimisation
    /// guard; state transitions still need database locks and idempotency keys.
    pub async fn lock(&self, key: &str, token: &str, ttl_s: u64) -> Result<bool> {
        let mut c = self.conn.clone();
        let reply: Option<String> = redis::cmd("SET")
            .arg(key)
            .arg(token)
            .arg("NX")
            .arg("EX")
            .arg(ttl_s)
            .query_async(&mut c)
            .await
            .map_err(cache)?;
        Ok(reply.is_some())
    }

    /// Release only if we still own the key (atomic).
    pub async fn unlock(&self, key: &str, token: &str) -> Result<bool> {
        let script = Script::new(UNLOCK_SCRIPT);
        let mut c = self.conn.clone();
        let n: i64 = script
            .key(key)
            .arg(token)
            .invoke_async(&mut c)
            .await
            .map_err(cache)?;
        Ok(n == 1)
    }

    pub async fn get(&self, key: &str) -> Result<Option<String>> {
        let mut c = self.conn.clone();
        c.get(key).await.map_err(cache)
    }
}

fn urlencode(s: &str) -> String {
    s.bytes()
        .map(|b| {
            if b.is_ascii_alphanumeric() || b"-._~".contains(&b) {
                (b as char).to_string()
            } else {
                format!("%{b:02X}")
            }
        })
        .collect()
}
