//! Pure core: domain rules, use cases and the ports they need. No I/O crates, no framework, no
//! logging macros that need a runtime, no wall clock (the clock is injected). Adapters live in
//! `svc-infra`, the HTTP edge in `svc-api`.

pub mod config;
pub mod error;
pub mod item;
pub mod ports;
pub mod service;

pub use error::{Error, Result};
