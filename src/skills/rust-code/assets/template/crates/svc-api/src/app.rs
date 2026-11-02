//! Router assembly: docs, health, routes, shared state, auth middleware. Handlers are thin: extract,
//! call one use case, answer. Every handler carries a `#[utoipa::path]` and is listed in
//! `docs::ApiDoc`.

use std::sync::Arc;

use axum::{
    extract::{Path, Request, State},
    http::{HeaderMap, StatusCode},
    middleware::{self, Next},
    response::Response,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use subtle::ConstantTimeEq;
use svc_core::{
    ports::{EventPublisher, ItemRepository},
    service::Items,
};
use utoipa::ToSchema;

use crate::{
    docs,
    envelope::{failure, ok, ApiError},
    health::{self, Check, Identity},
    internal::bare_token,
};

pub struct AppState<R, E> {
    pub items: Items<R, E>,
    pub token: String,
    pub identity: Identity,
    pub checks: Vec<Check>,
}

#[derive(Deserialize, ToSchema)]
pub struct CreateItem {
    name: String,
}

pub fn router<R, E>(state: Arc<AppState<R, E>>) -> Router
where
    R: ItemRepository + 'static,
    E: EventPublisher + 'static,
{
    let v1 = Router::new()
        .route("/items", post(create_item::<R, E>))
        .route("/items/{id}", get(get_item::<R, E>))
        .layer(middleware::from_fn_with_state(state.clone(), auth::<R, E>));
    // `/internal` is the same health body behind the service token, plus the caller.
    let internal = Router::new()
        .route("/internal", get(internal_health::<R, E>))
        .layer(middleware::from_fn_with_state(state.clone(), auth::<R, E>));
    // `/healthz` is the one health endpoint: public, unversioned, next to `/docs`. For /v2 add a
    // `nest("/v2", ...)` and put "v2" in `health::API_VERSIONS`.
    Router::new()
        .route("/healthz", get(healthz::<R, E>))
        .merge(internal)
        .nest("/v1", v1)
        .with_state(state)
        .merge(docs::routes())
}

/// Health of the service, for every API version.
#[utoipa::path(
    get,
    path = "/healthz",
    tag = "health",
    operation_id = "healthz",
    responses(
        (status = 200, description = "ok", body = health::Healthz),
        (status = 503, description = "a dependency is down", body = health::Healthz)
    )
)]
pub async fn healthz<R: ItemRepository, E: EventPublisher>(
    State(s): State<Arc<AppState<R, E>>>,
) -> Response {
    health::respond(&s.identity, &s.checks).await
}

/// Health for an internal caller: needs the service token, shows the caller.
#[utoipa::path(
    get,
    path = "/internal",
    tag = "internal",
    operation_id = "internal_health",
    security(("InternalServiceAuth" = [])),
    responses(
        (status = 200, description = "ok", body = health::InternalHealthz),
        (status = 401, description = "missing or invalid service token"),
        (status = 503, description = "a dependency is down", body = health::InternalHealthz)
    )
)]
pub async fn internal_health<R: ItemRepository, E: EventPublisher>(
    State(s): State<Arc<AppState<R, E>>>,
    headers: HeaderMap,
) -> Response {
    health::respond_internal(&s.identity, &s.checks, &headers).await
}

/// Create an item.
#[utoipa::path(
    post,
    path = "/v1/items",
    tag = "items",
    security(("InternalServiceAuth" = [])),
    request_body = CreateItem,
    responses((status = 201, description = "item created"), (status = 422, description = "invalid"))
)]
pub async fn create_item<R: ItemRepository, E: EventPublisher>(
    State(s): State<Arc<AppState<R, E>>>,
    body: Result<Json<CreateItem>, axum::extract::rejection::JsonRejection>,
) -> Result<Response, ApiError> {
    let Json(req) = body.map_err(|_| ApiError::InvalidJson)?;
    let item = s.items.create(&req.name).await?;
    Ok(ok(StatusCode::CREATED, item, "item created"))
}

/// Get an item.
#[utoipa::path(
    get,
    path = "/v1/items/{id}",
    tag = "items",
    security(("InternalServiceAuth" = [])),
    params(("id" = String, Path, description = "item id")),
    responses((status = 200, description = "the item"), (status = 404, description = "not found"))
)]
pub async fn get_item<R: ItemRepository, E: EventPublisher>(
    State(s): State<Arc<AppState<R, E>>>,
    Path(id): Path<String>,
) -> Result<Response, ApiError> {
    let item = s.items.get(&id).await?;
    Ok(ok(StatusCode::OK, item, ""))
}

/// Constant-time token check (`Bearer ` prefix optional); authenticate before trusting anything
/// else, `x-user-id` included. Never log the token.
async fn auth<R: ItemRepository, E: EventPublisher>(
    State(s): State<Arc<AppState<R, E>>>,
    req: Request,
    next: Next,
) -> Response {
    let got = req
        .headers()
        .get("x-internal-service-token")
        .and_then(|v| v.to_str().ok())
        .map(|v| bare_token(v).as_bytes())
        .unwrap_or_default();
    let ok_token = !s.token.is_empty() && bool::from(got.ct_eq(s.token.as_bytes()));
    if ok_token {
        next.run(req).await
    } else {
        failure(
            StatusCode::UNAUTHORIZED,
            "unauthorized",
            "missing or invalid service token",
        )
    }
}
