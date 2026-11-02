# pyo3 package: build, test, release

*Verified with: maturin 1.15 in a Rust container (abi3 wheel for Python >= 3.11); CI/publish commands follow the maturin documentation and should be dry-run in the target CI first.*

## Develop

```bash
python -m venv .venv && . .venv/bin/activate && pip install maturin pytest numpy
maturin develop --release      # editable install; rebuild after every Rust change (debug builds are 10-100x slower)
pytest -q
```

Always benchmark and run parity tests on `--release`; a debug build proves nothing about performance.

## Gates before every merge

```bash
cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace                       # core unit tests (extension-module is OFF in Cargo)
maturin develop --release && pytest -q       # the real extension
ruff check python tests && pycodestyle --max-line-length=79 python tests     # PEP 8
python -c "import <pkg>, importlib.resources as r; print(r.files('<pkg>').joinpath('py.typed').is_file())"   # py.typed shipped
```

Also: every native symbol is in `_native.pyi` and `__init__.__all__` (a test can compare `dir(_native)` with the stub); `cargo tree -d -i polars` is
empty when polars is used; `Cargo.lock` is committed for binaries and wheels you publish.

## Build wheels

```bash
maturin build --release --strip              # abi3 wheel for the host: <pkg>-<ver>-cp311-abi3-<platform>.whl
maturin sdist                                # source distribution
```

- **abi3** (`abi3-py311`) means one wheel per OS/arch for every Python >= 3.11; set the floor deliberately.
- **Linux:** build in a manylinux image (`ghcr.io/pyo3/maturin` / `maturin-action` with `manylinux: auto`) so the wheel runs on older glibc;
  musl needs its own target (`--target x86_64-unknown-linux-musl`). **macOS:** build `x86_64` and `aarch64` (or `universal2`). **Windows:** MSVC.
- Native dependencies (librdkafka, OpenSSL) make wheels platform-specific: vendor them (`cmake-build`, `vendored`) or document the system packages.

## CI matrix (outline)

1. `lint`: fmt, clippy, ruff/pycodestyle.  2. `test`: `cargo test`, then `maturin develop` + pytest on Python 3.11/3.12/3.13.
3. `wheels`: matrix of OS/arch with the maturin action, artifacts uploaded.  4. `publish` on a version tag only: trusted publishing (OIDC) to the
package index; never a long-lived token in the repository. Pin third-party actions to commit SHAs.

## Docker

Multi-stage: a Rust+Python builder stage (`rust:1` + `python3-dev` + `maturin`, `cmake` if rdkafka) runs `maturin build --release`, the runtime stage
`pip install`s the wheel into a slim Python image (non-root). Pin images, copy `Cargo.lock`, use BuildKit cache mounts for `~/.cargo/registry` and `target`.
See `deployment-setup` for the Dockerfile and Compose conventions.

## Release checklist

Version bumped in `Cargo.toml` (workspace) and `pyproject.toml` (keep them equal); changelog; wheels built for every target and **installed in a clean
venv and smoke-tested** (import, one call per public symbol); stubs in sync; license files included; tag created; publish from CI; verify
`pip install <pkg>==<ver>` from the index in a clean environment.

## Example usage

- “Set up CI to build abi3 wheels for Linux, macOS and Windows and publish on tag.”
- “Write the Dockerfile for a service that depends on our maturin package.”
