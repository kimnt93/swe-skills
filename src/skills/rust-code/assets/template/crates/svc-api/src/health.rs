//! `GET /healthz`, the one health endpoint; it lists every API version (api-contract skill).
//!
//! Always public (no token), never cached, every field always present. `config` is an allowlist
//! of non-secret values (`Config::public()`): add a key on purpose, never dump the environment, a
//! DSN or a secret. `checks` holds one entry per dependency the service cannot work without; an
//! optional dependency is not a check. Any failed check makes the status "down" and the response
//! 503. A check reports a short code ("timeout", "unavailable"), never the error text: the cause is
//! logged.

use std::{future::Future, pin::Pin, time::Duration};

use axum::{
    http::{header, HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    Json,
};
use serde::Serialize;
use time::{format_description::well_known::Rfc3339, OffsetDateTime};
use utoipa::ToSchema;

use crate::internal::Caller;

const CHECK_TIMEOUT: Duration = Duration::from_secs(2);

/// The API versions this service serves, listed by `/healthz`. Add "v2" with its router nest.
pub const API_VERSIONS: [&str; 1] = ["v1"];

type Probe =
    Box<dyn Fn() -> Pin<Box<dyn Future<Output = svc_core::Result<()>> + Send>> + Send + Sync>;

/// A dependency the service cannot work without: Postgres, Redis, Kafka.
pub struct Check {
    name: &'static str,
    probe: Probe,
}

impl Check {
    pub fn new<F, Fut>(name: &'static str, probe: F) -> Check
    where
        F: Fn() -> Fut + Send + Sync + 'static,
        Fut: Future<Output = svc_core::Result<()>> + Send + 'static,
    {
        Check {
            name,
            probe: Box::new(move || Box::pin(probe())),
        }
    }
}

/// Who this process is. Every field is shown by `/healthz`.
pub struct Identity {
    pub service_name: String,
    pub env_name: String,
    pub node_name: String,
    pub service_version: String,
    pub started_at: OffsetDateTime,
    /// `Config::public()`.
    pub config: serde_json::Map<String, serde_json::Value>,
}

#[derive(Serialize, ToSchema)]
pub struct CheckResult {
    pub name: String,
    pub status: String,
    pub latency_ms: f64,
    pub error: String,
}

#[derive(Serialize, ToSchema)]
pub struct Healthz {
    pub status: String,
    pub service_name: String,
    pub env_name: String,
    pub node_name: String,
    pub api_versions: Vec<String>,
    pub service_version: String,
    pub started_at: String,
    pub checked_at: String,
    pub uptime_seconds: i64,
    #[schema(value_type = Object)]
    pub config: serde_json::Map<String, serde_json::Value>,
    pub checks: Vec<CheckResult>,
}

/// `/internal`: the `/healthz` body plus who the caller says it is.
#[derive(Serialize, ToSchema)]
pub struct InternalHealthz {
    #[serde(flatten)]
    pub health: Healthz,
    pub caller: Caller,
}

/// The response of `/healthz`.
pub async fn respond(id: &Identity, checks: &[Check]) -> Response {
    let (status, body) = snapshot(id, checks).await;
    (status, [(header::CACHE_CONTROL, "no-store")], Json(body)).into_response()
}

/// The response of `/internal`; the service token was already checked by the auth layer.
pub async fn respond_internal(id: &Identity, checks: &[Check], headers: &HeaderMap) -> Response {
    let (status, health) = snapshot(id, checks).await;
    let body = InternalHealthz {
        health,
        caller: Caller::from_headers(headers),
    };
    (status, [(header::CACHE_CONTROL, "no-store")], Json(body)).into_response()
}

async fn snapshot(id: &Identity, checks: &[Check]) -> (StatusCode, Healthz) {
    let results = futures_util::future::join_all(checks.iter().map(run_check)).await;
    let down = results.iter().any(|r| r.status != "ok");
    let now = OffsetDateTime::now_utc();
    let body = Healthz {
        status: if down { "down" } else { "ok" }.into(),
        service_name: id.service_name.clone(),
        env_name: id.env_name.clone(),
        node_name: id.node_name.clone(),
        api_versions: API_VERSIONS.iter().map(|v| (*v).to_string()).collect(),
        service_version: id.service_version.clone(),
        started_at: rfc3339(id.started_at),
        checked_at: rfc3339(now),
        uptime_seconds: (now - id.started_at).whole_seconds(),
        config: id.config.clone(),
        checks: results,
    };
    let status = if down {
        StatusCode::SERVICE_UNAVAILABLE
    } else {
        StatusCode::OK
    };
    (status, body)
}

async fn run_check(check: &Check) -> CheckResult {
    let start = std::time::Instant::now();
    let outcome = tokio::time::timeout(CHECK_TIMEOUT, (check.probe)()).await;
    let (error, cause) = failure_code(outcome);
    if !error.is_empty() {
        tracing::warn!(check = check.name, %cause, "health check failed");
    }
    CheckResult {
        name: check.name.into(),
        status: if error.is_empty() { "ok" } else { "down" }.into(),
        latency_ms: (start.elapsed().as_secs_f64() * 10_000.0).round() / 10.0,
        error: error.into(),
    }
}

/// The short code shown to callers, and the cause for the log only.
fn failure_code(
    outcome: Result<svc_core::Result<()>, tokio::time::error::Elapsed>,
) -> (&'static str, String) {
    match outcome {
        Ok(Ok(())) => ("", String::new()),
        Ok(Err(cause)) => ("unavailable", cause.to_string()),
        Err(_) => ("timeout", "probe timed out".into()),
    }
}

fn rfc3339(at: OffsetDateTime) -> String {
    at.format(&Rfc3339).unwrap_or_default()
}
