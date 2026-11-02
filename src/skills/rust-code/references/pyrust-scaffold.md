# Python + Rust native: scaffold

*Verified with: Rust stable (1.99), pyo3 0.28 (abi3-py311), numpy 0.28, maturin 1.15, Python 3.13 (abi3 wheel for >= 3.11); cargo test --workspace, clippy -D warnings, pytest (7 tests) and pycodestyle pass.*

Pattern used by the engine repositories: **Rust owns the logic, Python is an adapter.** Start from `assets/pyrust-template`.

## Layout

```text
Cargo.toml                       [workspace] crates/*, one version set for pyo3 (+ numpy, pyo3-polars, polars), lints, profiles
pyproject.toml                   build-backend maturin; [tool.maturin] manifest-path, python-source, module-name, features
crates/<name>-core/              PURE Rust: the single implementation (state types), typed errors, unit tests. No pyo3.
crates/<name>-python/            cdylib `_native`: #[pyclass]/#[pyfunction] adapters, error -> exception mapping. No arithmetic.
python/<pkg>/__init__.py         re-exports from ._native (no logic); __all__
python/<pkg>/_native.pyi         type stubs for every native symbol;  py.typed
tests/                           pytest against the installed extension
```

Rules: one canonical implementation per concept, in core, with the lifecycle `new(..) -> Result`, `update`, `value`, `reset`, bulk
`extend` that leaves the same state as scalar replay ([feature](feature.md)); Python never re-implements
arithmetic, warm-up or repair. Missing data is `NaN`/`null` at the boundary, never `0`.

## Why the build is set up this way

- `pyo3 = { features = ["abi3-py311"] }`: one wheel per platform for all Python >= 3.11.
- `extension-module` is **off** in Cargo and **on** only through maturin (`[tool.maturin] features = ["pyo3/extension-module"]`): with it on,
  `cargo test --workspace` fails to link (undefined `Py*` symbols). So plain `cargo test` works on the core, and maturin builds the wheel.
- `crate-type = ["cdylib"]`, `[lib] name = "_native"`, `module-name = "<pkg>._native"`: the private extension sits inside the public package.
- Profiles: `[profile.release] lto = "thin", codegen-units = 1`; `[profile.test] debug = 0` (large test binaries).

## Steps

1. Copy `assets/pyrust-template/.`; rename `example-ta` / `example_ta`; keep or replace the sample `ExponentialMovingAverage`.
2. `python -m venv .venv && . .venv/bin/activate && pip install maturin pytest numpy && maturin develop --release`
3. Add the next symbol with [pyrust-binding](pyrust-binding.md); frames with [pyrust-polars](pyrust-polars.md);
   release with [pyrust-release](pyrust-release.md).

## Checks

```bash
cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace
maturin develop --release && pytest -q
ruff check python tests && pycodestyle --max-line-length=79 python tests      # Python side is PEP 8 (79 columns)
```

## Example usage

- “Scaffold a Python package whose indicators are implemented in Rust.”
- “Add a Rust core to this pure-Python module.”
