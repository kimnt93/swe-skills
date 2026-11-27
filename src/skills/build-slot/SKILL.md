---
name: build-slot
description: "Run every heavy build, of any language, through one shared FIFO queue of build slots per user and machine, so agents building at once in separate worktrees do not exhaust CPU and memory: `@PLUGIN@-build-slot <command>` waits in arrival order for one of 2 slots (SWE_BUILD_SLOT_MAX), gives Cargo, CMake and Go a job limit you have not set yourself, runs the command as given and returns its exit code. Use before a heavy compile, image build, make target or build script (Rust, Go, C/C++, TypeScript, native Python, Java/Kotlin, docker build and the like), in every brief that starts one, and when the builds of several agents slow the machine down."
metadata:
  group: process
  summary: "Run heavy builds of any language in one shared FIFO queue of build slots: @PLUGIN@-build-slot <command>"
---

# Build slot

Many agents build at once in separate worktrees. Every heavy build goes through one queue that all agents of this user
on this machine share: at most 2 run at once, the others wait in arrival order.

```bash
@PLUGIN@-build-slot <command> [args...]
```

The command runs as given, with no shell (for `&&` or a pipe, make one call per command), and its exit code is
returned. `--status` prints the slots and who waits; `--help` prints the settings. Not found? Run the script by its full
path, `python3 "<skill-dir>/scripts/@PLUGIN@-build-slot.py"` (`python` or `py` on Windows, `<skill-dir>` is this
file's directory), and tell the user `make install` puts the command in `~/.local/bin`.

## Steps for an agent

1. Before you run a build, a `make` target or a build script, decide whether it is heavy: read what it runs (its
   prerequisites and the scripts it calls).
2. Heavy: run it through `@PLUGIN@-build-slot`, compiling inside the slot and running tests outside it (table below).
3. A long build: start it in the background and check on it; waiting counts toward your command's timeout.
4. While it waits: do not kill it, bypass the queue or start a second copy. A stopped and rerun command goes to the
   back of the queue.
5. Put the same rule in every brief to an agent you start: "run heavy builds through `@PLUGIN@-build-slot`".

## What to run through a slot

| Language / tool | Through a slot | Not through a slot |
|---|---|---|
| Rust | `cargo build`, `cargo check`, `cargo clippy`, `cargo test --workspace --no-run`, `maturin build --release`, `maturin develop` | then `cargo test --workspace` (may still compile a little, such as doctests); `cargo fmt` |
| Go, when measured heavy | `go build ./...`, `go test -c -o <dir>/ ./...` (compiles the tests) | then `go test ./...`; `gofmt` |
| C/C++ | `cmake --build build`, `make -j6 build`, `ninja -C build` | `ctest --test-dir build`; `clang-format` |
| TypeScript/JavaScript, when large | `npm run build` (`next build`, `vite build`, `tsc -b`) | `npm test`, `eslint`, a small `tsc --noEmit` |
| Python with native code | `pip install .` or `uv build` of a package that compiles, `python -m build` | pure-Python installs, `pytest`, `ruff` |
| Java/Kotlin | `./gradlew assemble testClasses --max-workers=6`, `mvn -T 6 test-compile` | then `./gradlew test`, `mvn surefire:test` |
| Containers | `docker build -t <image> .` | `docker run` |

Any other heavy build works the same way. A slot limits how many builds start, not their CPU use, so the tool's own
limit still matters: the wrapper sets `CARGO_BUILD_JOBS`, `CMAKE_BUILD_PARALLEL_LEVEL` and Go's `-p` (in `GOFLAGS`)
to `SWE_BUILD_SLOT_JOBS` (6) when you have not set them. It sets no `GOMAXPROCS` (it changes the program and tests that
run) and no `MAKEFLAGS` `-j` (not every Makefile is parallel-safe): pass `make -j6`, `ninja -j6`, `--max-workers=6`,
`mvn -T 6`, `bazel build --jobs=6` or `dotnet build -maxcpucount:6` yourself. `docker build` runs in the Docker daemon,
which the slot does not limit.

## Builds started by make or a script

1. **It only builds** (heavy): wrap the whole call: `@PLUGIN@-build-slot make build`.
2. **It mixes a build with tests or lint** (such as `verify`) **and the Makefile has the `BUILD_SLOT` prefix
   variable:** do not wrap `make`; pass the command, so only the prefixed compile lines take a slot:
   `BUILD_SLOT=@PLUGIN@-build-slot make verify`.
3. **It mixes them without the variable:** wrap the whole `make` call and accept that the slot is held during the
   tests. Edit the project's Makefile only when your task includes it.

`make -n` shows a target's lines, but it still runs lines marked `+` or that call `$(MAKE)`. Never wrap `make` and also
pass `BUILD_SLOT` as if it narrowed the slot: the inner calls reuse the outer slot. The Makefile convention, empty by
default so people and CI run unchanged:

```make
BUILD_SLOT ?=

verify:
	$(BUILD_SLOT) cargo test --workspace --no-run
	cargo test --workspace
```

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `SWE_BUILD_SLOT_MAX` | `2` | builds that run at once; export a higher value to raise it |
| `SWE_BUILD_SLOT_JOBS` | `6` | the job limit given to Cargo, CMake and Go; a value you set is never changed |
| `SWE_BUILD_SLOT_TIMEOUT` | none | seconds to wait for a slot, then exit `75` without running the command |
| `SWE_BUILD_SLOT_DIR` | `~/.cache/build-slot` | the queue; every installed copy shares the default |

**Every caller of a queue uses the same `SWE_BUILD_SLOT_MAX`.** The oldest waiter takes the next slot within its own
maximum: mixed values run up to the largest one at once, and a waiter with a smaller one holds back those behind it.
Exit codes: the command's own; `75` no slot in time; `130` interrupted while waiting (`143` on SIGTERM), after leaving
the queue; `127` command not found; `126` not executable; `2` usage error.

## How it works

The queue directory holds `queue.lock` (held briefly to join, check or leave), `counter` (the last ticket number),
`tickets/<number>-<pid>.ticket` (one per waiter, locked while it waits), `slot-<n>.lock` (locked while a build holds
slot `n`) and `slot-<n>.owner` (the token, pid and program name of its last holder). This layout is stable: other
copies rely on it. Liveness is an OS file lock (`fcntl.flock`, `msvcrt.locking` on Windows), never a PID, so a waiter
that died is skipped and a reused PID changes nothing. Only the oldest live waiter takes a free slot. There is no
daemon. A nested call (the build runs the wrapper again) reuses the outer slot.

## Caveats

- The queue directory and its files are readable by you only (Linux and macOS). `slot-<n>.owner` and `--status`
  hold the program's name, never its arguments, which can carry tokens or build args.
- **Linux and macOS:** the build inherits its slot's lock, so a killed wrapper leaves the slot held until the build
  ends. A background daemon the build starts (a compiler cache server, a build daemon) inherits it too and holds the
  slot until it exits: start such a daemon before the build, outside the wrapper.
- **Windows:** the wrapper and the build run in a Job Object that ends with the wrapper: killing the wrapper ends the
  build, and a process the build leaves behind is ended when the build finishes. The command is the
  `@PLUGIN@-build-slot.cmd` launcher, which runs the script with `py`, else `python`; Ctrl+C in it may ask "Terminate
  batch job". `.cmd` and `.bat` tools such as `npm` are found by name and run by `cmd.exe`, which reads `& | < > ^ %`
  in their arguments: pass plain arguments only.
- Ctrl+C during the build reaches the build itself; the wrapper waits for it and returns its exit code.
- Tested on Linux, macOS and Windows by `tests/build_slot_test.py` in CI.
