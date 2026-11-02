//! Swagger UI at `/docs` and the OpenAPI document at `/docs/openapi.json`. Both are public. The
//! document is generated from the `#[utoipa::path]` annotations listed in `ApiDoc`.

use axum::{
    http::header,
    response::{Html, IntoResponse},
    routing::get,
    Router,
};
use utoipa::{
    openapi::security::{ApiKey, ApiKeyValue, SecurityScheme},
    Modify, OpenApi,
};

use crate::{
    health::{CheckResult, Healthz, InternalHealthz},
    internal::Caller,
};

/// List every handler here, in `paths(...)`: a route that is not listed is not documented.
#[derive(OpenApi)]
#[openapi(
    info(title = "Example service API", version = "1.0"),
    paths(
        crate::app::create_item,
        crate::app::get_item,
        crate::app::healthz,
        crate::app::internal_health
    ),
    components(schemas(crate::app::CreateItem, Healthz, InternalHealthz, CheckResult, Caller)),
    modifiers(&InternalServiceAuth)
)]
pub struct ApiDoc;

struct InternalServiceAuth;

impl Modify for InternalServiceAuth {
    fn modify(&self, openapi: &mut utoipa::openapi::OpenApi) {
        let components = openapi.components.get_or_insert_with(Default::default);
        components.add_security_scheme(
            "InternalServiceAuth",
            SecurityScheme::ApiKey(ApiKey::Header(ApiKeyValue::new("x-internal-service-token"))),
        );
    }
}

/// Pinned Swagger UI from a CDN, pointed at the document below.
const SWAGGER_UI: &str = r##"<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API docs</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>
window.ui = SwaggerUIBundle({url: "/docs/openapi.json", dom_id: "#swagger-ui"});
</script>
</body>
</html>"##;

pub fn routes() -> Router {
    let spec = ApiDoc::openapi().to_json().unwrap_or_default();
    Router::new()
        .route("/docs", get(|| async { Html(SWAGGER_UI) }))
        .route(
            "/docs/openapi.json",
            get(move || async move {
                ([(header::CONTENT_TYPE, "application/json")], spec).into_response()
            }),
        )
}
