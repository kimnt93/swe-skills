#![allow(clippy::unwrap_used, clippy::expect_used)]
use std::{collections::HashMap, sync::Mutex};

use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use svc_core::{item::Item, ports::*, Error, Result};
use time::macros::datetime;
use tower::ServiceExt;

use super::{app, *};

#[derive(Default)]
struct FakeRepo(Mutex<HashMap<String, Item>>);
impl ItemRepository for FakeRepo {
    async fn create(&self, item: &Item) -> Result<()> {
        self.0.lock().unwrap().insert(item.id.clone(), item.clone());
        Ok(())
    }
    async fn get(&self, id: &str) -> Result<Item> {
        self.0
            .lock()
            .unwrap()
            .get(id)
            .cloned()
            .ok_or(Error::NotFound)
    }
}

#[derive(Default)]
struct FakeEvents(Mutex<Vec<String>>);
impl EventPublisher for FakeEvents {
    async fn publish(&self, topic: &str, key: &str, _value: &[u8]) -> Result<()> {
        self.0.lock().unwrap().push(format!("{topic}/{key}"));
        Ok(())
    }
}

fn identity() -> health::Identity {
    let mut config = serde_json::Map::new();
    config.insert("port".into(), 3000.into());
    health::Identity {
        service_name: "svc".into(),
        env_name: "stg".into(),
        node_name: "node-1".into(),
        service_version: "1.2.3".into(),
        started_at: time::OffsetDateTime::now_utc() - time::Duration::seconds(90),
        config,
    }
}

fn router() -> axum::Router {
    router_with(Vec::new())
}

fn router_with(checks: Vec<health::Check>) -> axum::Router {
    let state = Arc::new(app::AppState {
        items: Items {
            repo: FakeRepo::default(),
            events: FakeEvents::default(),
            new_id: || "id-1".into(),
            now: || datetime!(2026-01-02 03:04:05 UTC),
        },
        token: "tok".into(),
        identity: identity(),
        checks,
    });
    app::router(state)
}

async fn call(
    method: &str,
    path: &str,
    body: &str,
    token: Option<&str>,
) -> (u16, serde_json::Value) {
    let mut req = Request::builder()
        .method(method)
        .uri(path)
        .header("content-type", "application/json");
    if let Some(t) = token {
        req = req.header("x-internal-service-token", t);
    }
    let res = router()
        .oneshot(req.body(Body::from(body.to_string())).unwrap())
        .await
        .unwrap();
    let status = res.status().as_u16();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null),
    )
}

struct Case {
    name: &'static str,
    method: &'static str,
    path: &'static str,
    body: &'static str,
    token: Option<&'static str>,
    status: u16,
    code: &'static str, // "" on success: the envelope always carries `error.code`
}

fn cases() -> [Case; 6] {
    let json = r#"{"name":"pen"}"#;

    [
        Case {
            name: "no token",
            method: "POST",
            path: "/v1/items",
            body: json,
            token: None,
            status: 401,
            code: "unauthorized",
        },
        Case {
            name: "wrong token",
            method: "POST",
            path: "/v1/items",
            body: json,
            token: Some("x"),
            status: 401,
            code: "unauthorized",
        },
        Case {
            name: "created",
            method: "POST",
            path: "/v1/items",
            body: json,
            token: Some("tok"),
            status: 201,
            code: "",
        },
        Case {
            name: "blank name",
            method: "POST",
            path: "/v1/items",
            body: r#"{"name":"  "}"#,
            token: Some("tok"),
            status: 422,
            code: "validation_error",
        },
        Case {
            name: "bad json",
            method: "POST",
            path: "/v1/items",
            body: "{",
            token: Some("tok"),
            status: 400,
            code: "invalid_json",
        },
        Case {
            name: "missing",
            method: "GET",
            path: "/v1/items/nope",
            body: "",
            token: Some("tok"),
            status: 404,
            code: "not_found",
        },
    ]
}

#[tokio::test]
async fn items_api_table() {
    for c in cases() {
        let (got, body) = call(c.method, c.path, c.body, c.token).await;
        assert_eq!(got, c.status, "{}: {body}", c.name);
        assert_eq!(body["error"]["code"], c.code, "{}", c.name);
        assert!(
            body.get("data").is_some() && body.get("message").is_some(),
            "{}: every envelope field is present",
            c.name
        );
    }
}

async fn get(router: axum::Router, path: &str) -> (u16, axum::http::HeaderMap, Vec<u8>) {
    let res = router
        .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = res.status().as_u16();
    let headers = res.headers().clone();
    let body = res.into_body().collect().await.unwrap().to_bytes().to_vec();
    (status, headers, body)
}

#[tokio::test]
async fn healthz_is_open_and_names_the_service() {
    let (status, headers, body) = get(router(), "/healthz").await;
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(status, 200);
    assert_eq!(headers["cache-control"], "no-store");
    for key in [
        "status",
        "service_name",
        "env_name",
        "node_name",
        "api_versions",
        "service_version",
        "started_at",
        "checked_at",
        "uptime_seconds",
        "config",
        "checks",
    ] {
        assert!(json.get(key).is_some(), "healthz is missing {key}");
    }
    assert_eq!(json["status"], "ok");
    assert_eq!(json["service_name"], "svc");
    assert_eq!(json["env_name"], "stg");
    assert_eq!(json["api_versions"], serde_json::json!(["v1"]));
    assert_eq!(json["config"]["port"], 3000);
    assert_eq!(json["checks"], serde_json::json!([]));
}

async fn internal(
    headers: &[(&str, &str)],
    checks: Vec<health::Check>,
) -> (u16, serde_json::Value) {
    let mut req = Request::builder().method("GET").uri("/internal");
    for (name, value) in headers {
        req = req.header(*name, *value);
    }
    let res = router_with(checks)
        .oneshot(req.body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = res.status().as_u16();
    let bytes = res.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null),
    )
}

#[tokio::test]
async fn internal_needs_the_token() {
    assert_eq!(internal(&[], vec![]).await.0, 401);
    assert_eq!(
        internal(&[("x-internal-service-token", "wrong")], vec![])
            .await
            .0,
        401
    );
}

#[tokio::test]
async fn internal_shows_health_and_the_caller() {
    let headers = [
        ("x-internal-service-token", "tok"),
        ("x-user-id", "u-7"),
        ("x-username", "linh"),
    ];
    let (status, body) = internal(&headers, vec![]).await;
    assert_eq!(status, 200);
    assert_eq!(body["status"], "ok");
    assert_eq!(body["service_name"], "svc");
    assert_eq!(
        body["caller"],
        serde_json::json!({"user_id": "u-7", "username": "linh"})
    );

    let (_, body) = internal(&[("x-internal-service-token", "tok")], vec![]).await;
    assert_eq!(
        body["caller"],
        serde_json::json!({"user_id": "", "username": ""})
    );
}

#[tokio::test]
async fn token_may_carry_a_bearer_prefix() {
    for value in ["Bearer tok", "bearer tok", "  Bearer   tok "] {
        let (status, _) = internal(&[("x-internal-service-token", value)], vec![]).await;
        assert_eq!(status, 200, "{value}");
    }
    let (status, _) = call("GET", "/v1/items/nope", "", Some("Bearer tok")).await;
    assert_ne!(status, 401, "/v1 accepts the Bearer form too");
}

#[tokio::test]
async fn internal_reports_a_down_dependency_without_leaking() {
    let down = health::Check::new("postgres", || async {
        Err(Error::Storage("dial postgres://u:secret@pg".into()))
    });
    let (status, body) = internal(&[("x-internal-service-token", "tok")], vec![down]).await;
    assert_eq!(status, 503);
    assert_eq!(body["status"], "down");
    assert!(!body.to_string().contains("secret"));
}

#[tokio::test]
async fn healthz_reports_a_down_dependency_without_leaking() {
    let down = health::Check::new("postgres", || async {
        Err(Error::Storage("dial postgres://u:secret@pg".into()))
    });
    let up = health::Check::new("redis", || async { Ok(()) });
    let (status, _, body) = get(router_with(vec![down, up]), "/healthz").await;
    let text = String::from_utf8(body).unwrap();
    let json: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert_eq!(status, 503);
    assert_eq!(json["status"], "down");
    assert_eq!(json["checks"][0]["error"], "unavailable");
    assert_eq!(json["checks"][1]["status"], "ok");
    assert!(!text.contains("secret"));
}

#[tokio::test]
async fn health_is_one_unversioned_endpoint() {
    // /v1 needs the token, so an unknown path there answers 401 before it could answer 404.
    assert_ne!(get(router(), "/v1/healthz").await.0, 200);
    assert_eq!(get(router(), "/readyz").await.0, 404);
}

#[tokio::test]
async fn docs_are_public_and_cover_every_documented_route() {
    let (status, _, page) = get(router(), "/docs").await;
    assert_eq!(status, 200);
    assert!(String::from_utf8(page).unwrap().contains("swagger-ui"));

    let (status, _, spec) = get(router(), "/docs/openapi.json").await;
    let spec: serde_json::Value = serde_json::from_slice(&spec).unwrap();
    assert_eq!(status, 200);
    for (path, method) in [
        ("/v1/items", "post"),
        ("/v1/items/{id}", "get"),
        ("/healthz", "get"),
        ("/internal", "get"),
    ] {
        assert!(spec["paths"][path][method].is_object(), "{method} {path}");
    }
}

/// A documented route that the router does not serve is a stale spec.
#[tokio::test]
async fn every_documented_get_route_exists() {
    use utoipa::OpenApi;
    let spec = serde_json::to_value(docs::ApiDoc::openapi()).unwrap();
    for (path, methods) in spec["paths"].as_object().unwrap() {
        if methods.get("get").is_none() {
            continue;
        }
        let concrete = path.replace("{id}", "some-id");
        let (status, _, _) = get(router(), &concrete).await;
        let known = status == 200 || status == 401 || status == 404 && concrete.contains("some-id");
        assert!(known, "GET {path} is documented but answered {status}");
    }
}
