//! Exponential moving average, seeded with the simple average of the first `period` values (warm-up
//! is `None`).

use crate::{Error, Result};

#[derive(Debug, Clone)]
pub struct ExponentialMovingAverage {
    period: usize,
    alpha: f64,
    seen: usize,
    seed_sum: f64,
    value: Option<f64>,
}

impl ExponentialMovingAverage {
    pub fn new(period: usize) -> Result<Self> {
        if period == 0 {
            return Err(Error::InvalidPeriod(period));
        }
        Ok(Self {
            period,
            alpha: 2.0 / (period as f64 + 1.0),
            seen: 0,
            seed_sum: 0.0,
            value: None,
        })
    }

    /// Consumes one value; returns the latest EMA (`None` while warming up). A `NaN` input leaves
    /// the state unchanged.
    pub fn update(&mut self, x: f64) -> Option<f64> {
        if x.is_nan() {
            return self.value;
        }
        match self.value {
            Some(prev) => self.value = Some(prev + self.alpha * (x - prev)),
            None => {
                self.seen += 1;
                self.seed_sum += x;
                if self.seen == self.period {
                    self.value = Some(self.seed_sum / self.period as f64);
                }
            }
        }
        self.value
    }

    pub fn value(&self) -> Option<f64> {
        self.value
    }

    pub fn period(&self) -> usize {
        self.period
    }

    pub fn reset(&mut self) {
        self.seen = 0;
        self.seed_sum = 0.0;
        self.value = None;
    }

    /// Bulk path: one output per input (`NaN` while warming up), the same post-run state as scalar
    /// replay.
    pub fn extend(&mut self, xs: &[f64]) -> Vec<f64> {
        let mut out = Vec::with_capacity(xs.len());
        for &x in xs {
            out.push(self.update(x).unwrap_or(f64::NAN));
        }
        out
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used)]
mod tests {
    use super::*;

    #[test]
    fn warms_up_with_the_simple_average_then_smooths() {
        let mut ema = ExponentialMovingAverage::new(3).unwrap();
        assert_eq!(ema.update(1.0), None);
        assert_eq!(ema.update(2.0), None);
        assert_eq!(ema.update(3.0), Some(2.0)); // seed = mean(1,2,3)
        let next = ema.update(4.0).unwrap(); // 2 + 0.5 * (4 - 2)
        assert!((next - 3.0).abs() < 1e-12);
    }

    #[test]
    fn bulk_equals_scalar_replay_and_leaves_the_same_state() {
        let xs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0];
        let (mut a, mut b) = (
            ExponentialMovingAverage::new(3).unwrap(),
            ExponentialMovingAverage::new(3).unwrap(),
        );
        let bulk = a.extend(&xs);
        let scalar: Vec<f64> = xs
            .iter()
            .map(|&x| b.update(x).unwrap_or(f64::NAN))
            .collect();
        assert_eq!(bulk.len(), scalar.len());
        for (x, y) in bulk.iter().zip(&scalar) {
            assert!(x == y || (x.is_nan() && y.is_nan()));
        }
        assert_eq!(a.value(), b.value());
    }

    #[test]
    fn rejects_a_zero_period_and_ignores_nan() {
        assert_eq!(
            ExponentialMovingAverage::new(0).unwrap_err(),
            Error::InvalidPeriod(0)
        );
        let mut ema = ExponentialMovingAverage::new(2).unwrap();
        ema.update(1.0);
        ema.update(f64::NAN);
        assert_eq!(ema.update(3.0), Some(2.0));
    }

    #[test]
    fn reset_restores_fresh_behaviour() {
        let mut ema = ExponentialMovingAverage::new(2).unwrap();
        ema.extend(&[1.0, 2.0, 3.0]);
        ema.reset();
        assert_eq!(ema.value(), None);
        assert_eq!(ema.update(5.0), None);
    }
}
