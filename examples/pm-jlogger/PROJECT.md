# pm-jlogger

A demo project of agents around one upstream repo, `jlogger`, set up as a **project manager** (mode pm): a manager runs
workflows that plan, build, review and merge. Claude plans and builds; the documenter runs on omp.

# Map

```yaml
repos:
  jlogger:
    role: Python JSON logger with a Rust (PyO3) core
    provides: [a Python logging library]
    depends_on: []
    docs: docs/README.md
    verify: make check test
external: {}
merge_order: [jlogger]
```

# Repos

- `jlogger/` (upstream: github.com/kimnt93/jlogger, a git submodule here): Python JSON logger with a Rust (PyO3) core.

# Dependencies

- Python 3.10+, a Rust toolchain and `maturin` to build the native extension. No services.

# Commands

- jlogger: `make develop` builds the extension; `make test` runs the unit tests; `make check` runs `cargo check` and the tests.
- jlogger has no `make verify` and no CI: use `make check test` as the verify command; there are no required checks.

# Conventions

- Branch from `main`, Conventional Commits, one PR per card, a linked issue (the `github` skill). Merge only through `swe-cli merge`.

# Gotchas

- jlogger has no required checks, so the merge gate refuses it until a verify check exists: the demo stops at a reviewed, open PR.
- The `checks` node passes after a 3 minute grace period when a repo reports no checks.

# Decisions

- 2026-11-04: the example stops at an open, reviewed PR; nothing is auto-merged.
