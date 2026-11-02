//! One error enum per crate boundary, one variant per failure class, a stable `code()` for the API
//! contract. Messages name what failed (and the variable), never a DSN, SQL or secret.

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("item name must be 1-120 characters")]
    InvalidName,
    #[error("resource not found")]
    NotFound,
    #[error("configuration: {0}")]
    Config(String),
    #[error("storage: {0}")]
    Storage(String),
    #[error("messaging: {0}")]
    Messaging(String),
}

impl Error {
    /// Stable machine code: add codes, never rename them.
    pub fn code(&self) -> &'static str {
        match self {
            Error::InvalidName => "validation_error",
            Error::NotFound => "not_found",
            Error::Config(_) => "config_error",
            Error::Storage(_) => "storage_error",
            Error::Messaging(_) => "messaging_error",
        }
    }
}

pub type Result<T, E = Error> = std::result::Result<T, E>;
