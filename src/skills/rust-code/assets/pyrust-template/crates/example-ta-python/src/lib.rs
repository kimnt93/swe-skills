//! PyO3 adapter: converts types and errors, nothing else. All numeric logic lives in
//! `example-ta-core`.
//!
//! Rules (see the pyrust-binding skill): release the GIL around real work (`py.detach`), map every
//! core error to a Python exception class, validate arguments at the boundary, never copy a numpy
//! array to compute on it, and keep this crate free of arithmetic.

use example_ta_core::{Error as CoreError, ExponentialMovingAverage};
use numpy::{PyArray1, PyReadonlyArray1, PyUntypedArrayMethods};
use pyo3::{create_exception, exceptions::PyValueError, prelude::*};

create_exception!(
    _native,
    ExampleTaError,
    pyo3::exceptions::PyException,
    "Base class of every example_ta error."
);
create_exception!(
    _native,
    InvalidPeriodError,
    ExampleTaError,
    "The period is not a positive integer."
);

fn to_py(e: CoreError) -> PyErr {
    match e {
        CoreError::InvalidPeriod(_) => InvalidPeriodError::new_err(e.to_string()),
    }
}

/// Streaming exponential moving average: `update(x)` one value at a time, `extend(array)` in bulk.
#[pyclass(module = "example_ta._native", name = "ExponentialMovingAverage")]
struct PyEma {
    inner: ExponentialMovingAverage,
}

#[pymethods]
impl PyEma {
    #[new]
    fn new(period: usize) -> PyResult<Self> {
        Ok(Self {
            inner: ExponentialMovingAverage::new(period).map_err(to_py)?,
        })
    }

    #[getter]
    fn period(&self) -> usize {
        self.inner.period()
    }

    /// The latest value, or `None` while warming up.
    #[getter]
    fn value(&self) -> Option<f64> {
        self.inner.value()
    }

    fn update(&mut self, x: f64) -> Option<f64> {
        self.inner.update(x)
    }

    fn reset(&mut self) {
        self.inner.reset();
    }

    /// Bulk path over a float64 array: one output per input, `NaN` while warming up.
    fn extend<'py>(
        &mut self,
        py: Python<'py>,
        values: PyReadonlyArray1<'py, f64>,
    ) -> PyResult<Bound<'py, PyArray1<f64>>> {
        let xs = contiguous(&values)?;

        // The GIL is released: other Python threads keep running.
        let out = py.detach(|| self.inner.extend(xs));

        Ok(PyArray1::from_vec(py, out))
    }
}

/// `ema(values, period)`: a one-shot EMA over a float64 array (no state kept).
#[pyfunction]
fn ema<'py>(
    py: Python<'py>,
    values: PyReadonlyArray1<'py, f64>,
    period: usize,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let xs = contiguous(&values)?;
    let out = py
        .detach(|| ExponentialMovingAverage::new(period).map(|mut e| e.extend(xs)))
        .map_err(to_py)?;
    Ok(PyArray1::from_vec(py, out))
}

/// Borrow the numpy buffer without copying; non-contiguous input is rejected with a clear message.
fn contiguous<'a>(a: &'a PyReadonlyArray1<'_, f64>) -> PyResult<&'a [f64]> {
    a.as_slice().map_err(|_| {
        PyValueError::new_err(format!(
            "expected a contiguous float64 array, got shape {:?}",
            a.shape()
        ))
    })
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEma>()?;
    m.add_function(wrap_pyfunction!(ema, m)?)?;
    m.add("ExampleTaError", m.py().get_type::<ExampleTaError>())?;
    m.add(
        "InvalidPeriodError",
        m.py().get_type::<InvalidPeriodError>(),
    )?;
    Ok(())
}
