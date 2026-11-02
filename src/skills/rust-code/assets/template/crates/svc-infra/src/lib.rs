//! Adapters implementing `svc-core` ports. SQL and driver types live here only.
#[cfg(feature = "kafka")]
pub mod kafka;
pub mod postgres;
pub mod redis_lock;
pub mod s3;
