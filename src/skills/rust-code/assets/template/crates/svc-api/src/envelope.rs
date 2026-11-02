//! Response envelope and error mapping: the same JSON contract as the Go and Python services. Every
//! field is always present with a zero value when unused (`data: null`, `error: {code: "",
//! retryable: false}`): no skipped fields, so clients and tests never branch on absence.

use axum::{http::StatusCode, response::IntoResponse, Json};
use serde::Serialize;
use svc_core::Error;

#[derive(Serialize, Default)]
pub struct ErrorBody {
    pub code: &'static str,
    pub retryable: bool,
}

#[derive(Serialize)]
pub struct Envelope<T: Serialize> {
    pub success: bool,
    pub status_code: u16,
    pub message: String,
    pub data: Option<T>,
    pub error: ErrorBody,
}

pub fn ok<T: Serialize>(status: StatusCode, data: T, message: &str) -> axum::response::Response {
    let body = Envelope {
        success: true,
        status_code: status.as_u16(),
        message: message.into(),
        data: Some(data),
        error: ErrorBody::default(),
    };
    (status, Json(body)).into_response()
}

pub fn failure(status: StatusCode, code: &'static str, message: &str) -> axum::response::Response {
    let body: Envelope<()> = Envelope {
        success: false,
        status_code: status.as_u16(),
        message: message.into(),
        data: None,
        error: ErrorBody {
            code,
            retryable: false,
        },
    };
    (status, Json(body)).into_response()
}

/// The HTTP edge's error type (small, so `Result<_, ApiError>` stays cheap): a core error or a
/// malformed body.
pub enum ApiError {
    Core(Error),
    InvalidJson,
}

impl From<Error> for ApiError {
    fn from(e: Error) -> Self {
        ApiError::Core(e)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> axum::response::Response {
        match self {
            ApiError::InvalidJson => failure(
                StatusCode::BAD_REQUEST,
                "invalid_json",
                "request body is not valid JSON",
            ),
            ApiError::Core(Error::InvalidName) => failure(
                StatusCode::UNPROCESSABLE_ENTITY,
                "validation_error",
                &Error::InvalidName.to_string(),
            ),
            ApiError::Core(Error::NotFound) => {
                failure(StatusCode::NOT_FOUND, "not_found", "resource not found")
            }
            ApiError::Core(other) => {
                // Log the cause; return nothing about it: infrastructure errors can carry hosts,
                // SQL or payloads.
                tracing::error!(error = %other, code = other.code(), "unhandled error");
                failure(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "internal_error",
                    "internal error",
                )
            }
        }
    }
}
