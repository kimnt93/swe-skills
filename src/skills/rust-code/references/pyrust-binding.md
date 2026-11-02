# pyo3 binding rules

*Verified with: pyo3 0.28 and numpy 0.28 in the scaffold template (built with maturin, 7 pytest tests pass, clippy -D warnings clean).*

Reference: `pyassets/template/crates/example-ta-python/src/lib.rs`. The binding crate **converts types and errors and nothing else**.

## Adding a symbol (checklist)

1. **Core first:** implement and unit-test it in `<name>-core` (typed error, no pyo3, deterministic). A free `pyfunction` that computes is a
   bug: the computation belongs to the core type.
2. **Adapter:** a `#[pyclass]` for stateful things (wraps the core state: `inner`), a `#[pyfunction]` for one-shots; `#[pyo3(signature = (...))]`
   for defaults and keyword-only arguments; docstrings (`///`) become Python docstrings.
3. **Register** in the `#[pymodule]` (`m.add_class`, `m.add_function(wrap_pyfunction!(..))`, exception classes).
4. **Python side:** add it to `python/<pkg>/__init__.py` (`from ._native import ...` and `__all__`) and to `_native.pyi` with precise types
   (`npt.NDArray[np.float64]`, `float | None`).
5. **Tests** (pytest): parity of bulk and scalar paths, warm-up/`None`, `NaN` handling, every exception, non-contiguous and wrong-dtype input,
   and (for long calls) GIL release.

## Rules

- **Release the GIL around real work:** `py.detach(|| core_call(slice))` (pyo3 0.26+; formerly `allow_threads`). Everything inside must be `Send`
  and must not touch Python objects. Quick getters do not need it.
- **Zero-copy in, one allocation out:** accept `PyReadonlyArray1<f64>` and borrow `as_slice()?` (reject non-contiguous input with a clear
  `ValueError`; do not silently copy); return `PyArray1::from_vec(py, out)`. 2-D: `PyReadonlyArray2`, `as_array()`. Never loop over Python
  objects per element in native code.
- **Errors:** one Python base exception (`create_exception!(_native, PkgError, PyException)`), one subclass per core error variant, built from the
  core error with a `to_py` function (a `match`, so adding a variant forces a mapping). Messages name the parameter, never data or secrets.
  Argument type errors (`OverflowError` for a negative `usize`) come from pyo3 and are tested.
- **Validation at the boundary** (shape, dtype, range) with `ValueError`/`TypeError`; the core validates domain rules.
- **State types** expose `update`, `value` (getter), `reset`, `extend`; `#[pyclass(module = "<pkg>._native", name = "<PublicName>")]` so
  pickling and `repr` show the public path. Add `__repr__` for debuggability.
- **No global mutable state**, no `unsafe` (`unsafe_code = "forbid"`), no `unwrap()` on Python input.
- **Time and units:** UTC integer ns/ms or aware datetimes converted once by shared helpers; the unit is in the argument name (`ts_ns`).
- **Determinism:** same inputs, same outputs, independent of thread scheduling; no `HashMap` iteration order in results.

## Version discipline

`pyo3`, `numpy`, `pyo3-polars` and `polars` move **as one set** (the repositories pin pyo3 0.28 / pyo3-polars 0.27 / polars =0.54.4). Upgrading one
alone breaks the build or, worse, the ABI between Rust and Python polars. `cargo tree -d -i polars` must print nothing.

## Example usage

- “Expose the rolling-correlation state to Python with numpy input and typed errors.”
- “Why does `cargo test --workspace` fail with undefined Py symbols?” (extension-module on in Cargo)
