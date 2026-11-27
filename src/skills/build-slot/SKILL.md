---
name: build-slot
description: "Run heavy builds through one shared FIFO queue of build slots per user and machine, so agents building at once in separate worktrees do not exhaust CPU and memory. Wrap cargo build, check, clippy and the compile of cargo test, maturin, docker build and native C/C++ extension builds in scripts/build-slot.py: it waits in arrival order for a free slot (2 by default), sets CARGO_BUILD_JOBS=6 when it is unset and returns the command's exit code. Use before any heavy compile or image build, and when the builds of several agents slow the machine down."
metadata:
  group: process
  summary: "Run heavy builds in one shared FIFO queue of build slots so parallel agents share the machine"
---

# Build slot

Many agents build at once in separate worktrees. Every heavy build goes through one queue that all agents of this user
on this machine share: at most 2 run at once, the others wait in arrival order.

## Run

```bash
python3 "<skill-dir>/scripts/build-slot.py" <command> [args...]
```

`<skill-dir>` is the directory of this file. Use its full path: your working directory is the target project. On
Windows run it with `python` or `py`. The command runs as given, with no shell: for `&&` or a pipe, make one call per
command. It waits for a free slot, prints its queue position to stderr while it waits, runs the command and exits with
the command's exit code. `--status` prints the slots and who waits.

## When to wrap

| Wrap | Do not wrap |
|---|---|
| `cargo build`, `cargo check`, `cargo clippy`, the compile of `cargo test` | lint and format (`ruff`, `cargo fmt`, `eslint`) |
| `maturin build`, `maturin develop` | plain Python and its tests |
| `docker build` | small, quick tests |
| native C/C++ extensions (a `pip install` that compiles, `cmake --build`) | |
| Go and large TypeScript builds, only when measured heavy | |

Compile inside the slot, run the tests outside it:

```bash
python3 "<skill-dir>/scripts/build-slot.py" cargo test --workspace --no-run
cargo test --workspace    # runs the tests; may still compile a little, such as doctests
```

## Rules

- **Waiting counts toward your command's timeout.** Run a long build in the background and check on it.
- **Never kill or bypass a waiting build.** A stopped and rerun command goes to the back of the queue.
- **Every agent sharing a queue uses the same slot count.**
- A nested call (the build runs a script that calls the wrapper again) reuses the outer slot.
- `docker build`: a slot limits how many builds start, not their CPU use; the Docker daemon does the work.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `BUILD_SLOT_SLOTS` | `2` | how many builds run at once |
| `BUILD_SLOT_JOBS` | `6` | the `CARGO_BUILD_JOBS` given to the command; a value already set is never changed |
| `BUILD_SLOT_TIMEOUT` | none | seconds to wait for a slot, then exit `75` without running the command |
| `BUILD_SLOT_DIR` | `~/.cache/build-slot` | the queue; every installed copy shares the default |

Exit codes: the command's own; `75` no slot within `BUILD_SLOT_TIMEOUT`; `130` interrupted (Ctrl+C) while waiting,
`143` on SIGTERM, both after leaving the queue; `127` command not found; `126` not executable; `2` usage error.

## How it works

The queue directory holds `queue.lock` (held briefly to join, check or leave), `counter` (the last ticket number),
`tickets/<number>-<pid>.ticket` (one per waiter, locked while it waits), `slot-<n>.lock` (locked while a build holds
slot `n`) and `slot-<n>.owner` (its holder). This layout is stable: other copies rely on it. Liveness is an OS file lock
(`fcntl.flock`, `msvcrt.locking` on Windows), never a PID, so a waiter that died is skipped and a reused PID changes
nothing. Only the oldest live waiter takes a free slot. There is no daemon.

## Caveats

- **Linux and macOS:** the build inherits its slot's lock, so a killed wrapper leaves the slot held until the build
  ends. A background daemon the build starts (a compiler cache server, a build daemon) inherits it too and holds the
  slot until it exits: start such a daemon before the build, outside the wrapper.
- **Windows:** the wrapper and the build run in a Job Object that ends with the wrapper: killing the wrapper ends the
  build, and a process the build leaves behind is ended when the build finishes. `.cmd` and `.bat` tools such as `npm`
  are found by name and run by `cmd.exe`, which reads `& | < > ^ %` in their arguments: pass plain arguments only.
- Ctrl+C during the build reaches the build itself; the wrapper waits for it and returns its exit code.
- Tested on Linux, macOS and Windows by `tests/build_slot_test.py` in CI.
