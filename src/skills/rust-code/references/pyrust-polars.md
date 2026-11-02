# pyo3 + polars

*Verified with: pyo3 0.28, pyo3-polars 0.27, polars =0.54.4 (Rust) exchanging frames with Python polars 2.0, built by maturin (8 pytest tests pass). Re-test when any version of the set changes.*

Reference: `assets/pyrust-polars/lib_with_polars.rs` (the pyo3 crate with `ema_frame`), `assets/pyrust-polars/test_frame.py`, `assets/pyrust-polars/polars.toml.snippet`. Use polars, **not pandas**,
across the boundary: Arrow memory is shared, so nothing is converted row by row.

## Dependencies (one version set)

```toml
polars = { version = "=0.54.4", default-features = false }                       # exact pin, features only as needed
pyo3-polars = { version = "0.27", default-features = false, features = ["derive", "lazy"] }
```

`pyo3-polars`, `polars` and `pyo3` are released together; copy the set the repository already pins. `default-features = false` keeps compile
time and size down (add `lazy`, `dtype-datetime`, ... per use). `cargo tree -d -i polars` must print nothing (two polars versions in one binary
cannot exchange data).

## Frame in, frame out

```rust
#[pyfunction]
fn ema_frame(py: Python<'_>, df: PyDataFrame, column: &str, period: usize) -> PyResult<PyDataFrame> {
    let mut frame: DataFrame = df.into();
    let series = frame.column(column).map_err(bad)?.as_materialized_series().cast(&DataType::Float64).map_err(bad)?;
    let xs: Vec<f64> = series.f64().map_err(bad)?.iter().map(|v| v.unwrap_or(f64::NAN)).collect();
    let out = py.detach(|| core_compute(&xs, period)).map_err(to_py)?;       // GIL released
    let values: Vec<Option<f64>> = out.into_iter().map(|v| if v.is_nan() { None } else { Some(v) }).collect();
    frame.with_column(Series::new("name".into(), values).into()).map_err(bad)?;
    Ok(PyDataFrame(frame))
}
```

## Rules

- **Null vs NaN:** polars `null` is "missing"; `NaN` is a float. Map nulls to `NaN` for the numeric core (`unwrap_or(f64::NAN)`), and map the
  core's warm-up `NaN` back to `null` on the way out. Never replace missing data with `0`.
- **Prefer borrowing the chunked array** (`series.f64()?` and `.cont_slice()` when contiguous with no nulls) over collecting into a `Vec` for large
  data; collect only when the core needs a slice.
- **No row-wise callbacks into Python** (no `map_elements`, no `apply` in tests or docs): vectorise in Rust or express it in polars.
- **Types and time:** UTC `Datetime("ns", "UTC")`; preserve the input schema and column order; add output columns with a documented suffix.
- **Lazy:** accept `PyLazyFrame` to compose with the caller's query plan when the work is a pure transformation; otherwise collect once.
- **Expression plugins** (`#[polars_expr]`, `pyo3_polars::derive`) are for functions that should run inside polars' engine in parallel across
  chunks; ship them in a separate cdylib and register with `register_plugin_function` (follow the polars plugin guide for the version pinned).
- **Errors:** polars errors map to `ValueError` with the polars message; domain errors keep their own exception classes.
- **Tests:** build tiny frames inline, assert `columns`, values, `null_count()`, dtype, determinism, and that the input frame is unchanged.

## Example usage

- “Add a Rust rolling indicator that takes a polars DataFrame and returns the frame with a new column.”
- “Why do two polars versions in my wheel crash on import?”
