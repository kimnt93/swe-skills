---
name: build-slot
description: "Limit how many heavy builds run at once on a machine where several workers build: `@PLUGIN@-build-slot <command>` waits in arrival order for one of 2 shared build slots per user and machine (SWE_BUILD_SLOT_MAX), gives Cargo, CMake and Go a job limit you have not set yourself, runs the command as given and returns its exit code. Use before a heavy compile, image build, make target or build script of any language (Rust, Go, C/C++, TypeScript, native Python, Java/Kotlin, docker build and the like), in every brief that starts one, and when builds slow the machine down."
metadata:
  group: process
  summary: "Limit concurrent heavy builds of any language on a shared machine: @PLUGIN@-build-slot <command>"
---

# Build slot

At most 2 heavy builds run at once on this machine (per user); the others wait in arrival order.

```bash
@PLUGIN@-build-slot <command> [args...]
```

The command runs as given, with no shell (for `&&` or a pipe, make one call per command), and its exit code is
returned. `--status` prints the slots and who waits; `--help` prints the settings and the details. Not found? Run the
script by its full path, `python3 "<skill-dir>/scripts/@PLUGIN@-build-slot.py"` (`python` or `py` on Windows,
`<skill-dir>` is this file's directory), and tell the user `make install` puts the command in `~/.local/bin`.

## Steps

1. Before you run a build, a `make` target or a build script, decide whether it is heavy: read what it runs (its
   prerequisites and the scripts it calls).
2. Heavy: run it through `@PLUGIN@-build-slot`, compiling inside the slot and running tests outside it (table below).
3. Long, or it may wait for a slot: run it in the background (below). Waiting counts toward a command's timeout.
4. While it waits: do not bypass the queue or start a second copy. A cancelled and rerun command goes to the back of
   the queue.
5. Put the same rule in every brief to an agent you start: "run heavy builds through `@PLUGIN@-build-slot`".

## Run in the background, check, cancel

- **Run:** start it with your harness's background run, or from a shell:
  `@PLUGIN@-build-slot <command> > build.log 2>&1 & echo $!` (the printed number is the wrapper's pid).
- **Check:** read `build.log` (the queue position comes first) and `@PLUGIN@-build-slot --status`, which lists each
  busy slot's program, wrapper pid and build pid, and the waiters.
- **Cancel:** stop the background task, or `kill <wrapper pid>` (SIGTERM). Waiting, it leaves the queue; building, it
  stops the build it started and frees the slot once the build is gone, then exits `143`. Stopping its whole process
  group, as `timeout <seconds> @PLUGIN@-build-slot ...` does, works too.
- **A foreground timeout may not cancel:** some harnesses move a timed-out command to the background instead. Check
  `--status` and cancel it as above.
- **Never `kill -9` the wrapper alone:** the build keeps running and holds its slot. If it happened, `--status` shows
  `wrapper gone` with the build pid: `kill <build pid>` (only a build you started) frees the slot.
- **Windows:** `Stop-Process -Id <wrapper pid>` or `taskkill /F /PID <wrapper pid>` ends the build and frees the slot.

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

Any other heavy build works the same way. A slot limits how many builds start, not their CPU use: the wrapper sets
`CARGO_BUILD_JOBS`, `CMAKE_BUILD_PARALLEL_LEVEL` and Go's `-p` (in `GOFLAGS`) to `SWE_BUILD_SLOT_JOBS` (6) when you
have not set them, but no `GOMAXPROCS` or `MAKEFLAGS`: pass `make -j6`, `ninja -j6`, `--max-workers=6`, `mvn -T 6`,
`bazel build --jobs=6` or `dotnet build -maxcpucount:6` yourself. `docker build` runs in the Docker daemon, which the
slot does not limit.

## Builds started by make or a script

1. **It only builds** (heavy): wrap the whole call: `@PLUGIN@-build-slot make build`.
2. **It mixes a build with tests or lint** (such as `verify`) **and the Makefile has the `BUILD_SLOT` prefix
   variable:** do not wrap `make`; pass the command, so only the prefixed compile lines take a slot:
   `BUILD_SLOT=@PLUGIN@-build-slot make verify`.
3. **It mixes them without the variable:** wrap the whole `make` call and accept that the slot is held during the
   tests. Edit the project's Makefile only when your task includes it.

`make -n` shows a target's lines, but it still runs lines marked `+` or that call `$(MAKE)`. Never wrap `make` and also
pass `BUILD_SLOT`: the inner calls reuse the outer slot. The Makefile convention, empty by default so people and CI run
unchanged:

```make
BUILD_SLOT ?=

verify:
	$(BUILD_SLOT) cargo test --workspace --no-run
	cargo test --workspace
```

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `SWE_BUILD_SLOT_MAX` | `2` | builds that run at once; every caller of a queue should use the same value |
| `SWE_BUILD_SLOT_JOBS` | `6` | the job limit given to Cargo, CMake and Go; a value you set is never changed |
| `SWE_BUILD_SLOT_TIMEOUT` | none | seconds to wait for a slot, then exit `75` without running the command |
| `SWE_BUILD_SLOT_GRACE` | `10` | seconds a cancelled build gets to stop before it is killed |
| `SWE_BUILD_SLOT_DIR` | `~/.cache/build-slot` | the queue; every installed copy shares the default |

Exit codes: the command's own; `75` no slot in time; `143` (SIGTERM) or `129` (SIGHUP) cancelled; `130` interrupted
while waiting; `127` command not found; `126` not executable; `2` usage error.

## Caveats

- The queue keeps the program's name, never its arguments, readable by you only (Linux and macOS).
- **Linux and macOS:** a background daemon the build starts (a compiler cache server, a build daemon) holds the slot
  until it exits: start such a daemon before the build, outside the wrapper.
- **Windows:** the command is the `@PLUGIN@-build-slot.cmd` launcher. `.cmd` and `.bat` tools such as `npm` are run by
  `cmd.exe`, which reads `& | < > ^ %` in their arguments: pass plain arguments only.
