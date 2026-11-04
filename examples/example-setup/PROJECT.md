# example-setup

A demo project of agents around one upstream repo, `jlogger`. Claude Code plans and builds, oh-my-pi reviews.

# Repos

- `jlogger/` (upstream: github.com/kimnt93/jlogger): Python JSON logger with a Rust (PyO3) core. Python and Rust.

# Dependencies

- Python 3.10+ with `uv`, a Rust toolchain and `maturin` to build the native extension. No services.

# Commands

- jlogger: `make develop` builds the extension; `make test` runs pytest; `make check` runs lint and type checks.
- jlogger has no `make verify` and no CI yet: use `make check test` as the verify command, and expect no required checks.

# Conventions

- Branch from `main`, Conventional Commits, one PR per card (the `github` skill). Merge only through `swe-cli merge`.

# Gotchas

- jlogger has no required checks, so the merge gate refuses it until a verify check is added. The demo stops at a ready PR.

# Decisions

- 2026-11-04: the example stops at an open, reviewed PR; nothing is auto-merged.
