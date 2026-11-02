//! One error enum, one variant per failure class; messages name the parameter, never data.

#[derive(Debug, thiserror::Error, PartialEq)]
pub enum Error {
    #[error("period must be at least 1, got {0}")]
    InvalidPeriod(usize),
}

pub type Result<T> = std::result::Result<T, Error>;
