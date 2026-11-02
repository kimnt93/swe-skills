//! Pure Rust core: the single implementation of every indicator. No Python, no I/O. The Python
//! crate only adapts.
//!
//! Contract (the same one every state type follows): `new(..) -> Result<Self>` validates the
//! configuration, `update(x)` consumes one chronological value, `value()` is the latest result
//! (`None` during warm-up), `reset()` restores fresh-state behaviour, `extend(&[f64]) -> Vec<f64>`
//! is the bulk path and leaves the same state as scalar replay. Missing data is `NaN` at the
//! boundary and `None` inside; it is never silently replaced by 0.

mod ema;
mod error;

pub use ema::ExponentialMovingAverage;
pub use error::{Error, Result};
