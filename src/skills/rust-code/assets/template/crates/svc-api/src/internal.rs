//! What an internal caller sends (api-contract skill, "Internal calls"): the shared service token in
//! `x-internal-service-token` (with or without a `Bearer ` prefix) and, after it passed, who the
//! call is for in `x-user-id` / `x-username`.

use axum::http::HeaderMap;
use serde::Serialize;
use utoipa::ToSchema;

const MAX_LEN: usize = 128;

/// The token without an optional case-insensitive `Bearer ` prefix: both header forms are valid.
pub fn bare_token(raw: &str) -> &str {
    let raw = raw.trim();
    match raw.get(..7) {
        Some(prefix) if prefix.eq_ignore_ascii_case("bearer ") => raw[7..].trim(),
        _ => raw,
    }
}

/// Who the calling service says it acts for. Trust it only after the token check; both fields are
/// "" when the header is absent.
#[derive(Serialize, ToSchema, Debug, PartialEq, Eq)]
pub struct Caller {
    pub user_id: String,
    pub username: String,
}

impl Caller {
    /// Reads `x-user-id` and `x-username`, trimmed and capped at 128 characters.
    pub fn from_headers(headers: &HeaderMap) -> Caller {
        let read = |name: &str| {
            let value = headers
                .get(name)
                .and_then(|v| v.to_str().ok())
                .unwrap_or("");
            value.trim().chars().take(MAX_LEN).collect::<String>()
        };
        Caller {
            user_id: read("x-user-id"),
            username: read("x-username"),
        }
    }
}
