//! Composition root: config -> logging -> adapters -> router -> graceful shutdown.
mod app;
mod docs;
mod envelope;
mod health;
mod internal;

use std::sync::Arc;

use health::{Check, Identity};
use svc_core::{config, ports::EventPublisher, service::Items, Result};
use svc_infra::postgres::PgItems;
use time::OffsetDateTime;
use tracing_subscriber::EnvFilter;

/// Stand-in publisher: replace with a Kafka adapter (rdkafka) in a real service.
struct LogEvents;
impl EventPublisher for LogEvents {
    async fn publish(&self, topic: &str, key: &str, value: &[u8]) -> Result<()> {
        tracing::info!(topic, key, bytes = value.len(), "event published");
        Ok(())
    }
}

#[tokio::main]
async fn main() {
    if let Err(e) = run().await {
        eprintln!("api: {e}");
        std::process::exit(1);
    }
}

async fn run() -> std::result::Result<(), Box<dyn std::error::Error>> {
    let cfg = config::load()?;
    // RUST_LOG wins; LOG_LEVEL is the default directive.
    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(&cfg.log_level));
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(filter)
        .with_current_span(false)
        .init();
    let pg = PgItems::open(&cfg.postgres, cfg.postgres.pool_size)?;
    pg.ping().await?; // fail fast; the container health gate normally waits for the database first
    let state = Arc::new(app::AppState {
        items: Items {
            repo: pg.clone(),
            events: LogEvents,
            new_id: || uuid::Uuid::new_v4().to_string(),
            now: OffsetDateTime::now_utc,
        },
        token: cfg.internal_service_token.clone(),
        identity: Identity {
            service_name: cfg.service_name.clone(),
            env_name: cfg.env_name.clone(),
            node_name: node_name(&cfg),
            service_version: cfg.service_version.clone(),
            started_at: OffsetDateTime::now_utc(),
            config: cfg.public(),
        },
        checks: vec![Check::new("postgres", move || {
            let pg = pg.clone();
            async move { pg.ping().await }
        })],
    });
    let addr = cfg.http_addr();
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    tracing::info!(%addr, service = %cfg.service_name, "api listening");
    axum::serve(listener, app::router(state))
        .with_graceful_shutdown(shutdown_signal())
        .await?;
    Ok(())
}

/// NODE_NAME is the Docker host; without it the container hostname is the best available.
fn node_name(cfg: &config::Config) -> String {
    if !cfg.node_name.is_empty() {
        return cfg.node_name.clone();
    }
    std::env::var("HOSTNAME").unwrap_or_default()
}

async fn shutdown_signal() {
    let ctrl_c = async {
        let _ = tokio::signal::ctrl_c().await;
    };
    #[cfg(unix)]
    let term = async {
        if let Ok(mut s) = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
        {
            s.recv().await;
        }
    };
    #[cfg(not(unix))]
    let term = std::future::pending::<()>();
    tokio::select! { _ = ctrl_c => {}, _ = term => {} }
}

#[cfg(test)]
mod tests;
