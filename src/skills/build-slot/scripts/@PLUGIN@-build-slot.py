#!/usr/bin/env python3
"""@PLUGIN@-build-slot: run a heavy build command of any language in one of a few shared build slots.

    @PLUGIN@-build-slot <command> [args...]    run the command (as given, no shell) when a slot is free
    @PLUGIN@-build-slot --status               print the slots and who waits
    @PLUGIN@-build-slot --help                 print this help

Callers wait in arrival order (FIFO). Every copy on a machine shares one queue per user.

Environment (exported by the caller):
    SWE_BUILD_SLOT_MAX      builds that run at once (default 2); every caller of one queue should use the same
                            value: the oldest waiter takes the next slot within its own MAX, so mixed values run
                            up to the largest MAX at once and a waiter with a smaller one holds back those behind it
    SWE_BUILD_SLOT_JOBS     job count given to the build tools below (default 6)
    SWE_BUILD_SLOT_TIMEOUT  seconds to wait for a slot, then exit 75 without running (default: no limit)
    SWE_BUILD_SLOT_DIR      the queue directory (default ~/.cache/build-slot)
    SWE_BUILD_SLOT_GRACE    seconds a cancelled build gets after SIGTERM before SIGKILL (default 10)

Cancel (Linux, macOS): SIGTERM or SIGHUP to this command while it waits leaves the queue; while it builds, the
signal goes to the build and the processes below it (nothing else), SIGKILL follows after the grace period, and the
slot is freed once they are gone. A stop of the whole process group reaches the build directly. SIGKILL of this
command alone leaves the build running with its slot: --status then shows "wrapper gone" and the build's pid to stop.
Windows: ending this command (Stop-Process, taskkill) ends the build through a Job Object and frees the slot.

Job limits set for the command, each only when you have not set it yourself:
    CARGO_BUILD_JOBS            Cargo (build.jobs)
    CMAKE_BUILD_PARALLEL_LEVEL  cmake --build
    GOFLAGS -p=<jobs>           Go, appended only when GOFLAGS (or `go env -w GOFLAGS`) has no -p, other flags
                                kept; -p also limits how many test binaries `go test` runs at once
Not set: GOMAXPROCS (it changes the program and tests that run) and MAKEFLAGS -j (not every Makefile is
parallel-safe). Pass those, or another tool's own limit, yourself: make -j6, ninja -j6, gradle
--max-workers=6, mvn -T 6, bazel build --jobs=6, dotnet build -maxcpucount:6.

Exit codes: the command's own; 75 the wait timed out (the command did not run); 128 + the signal when
cancelled (129 SIGHUP, 143 SIGTERM, 130 SIGINT while waiting); 127 command not found; 126 command not
executable; 2 usage error.

Layout of the queue directory (stable; other copies of this script rely on it):
    queue.lock         locked briefly while joining, checking or leaving the queue
    counter            the last ticket number given out
    tickets/<12-digit number>-<pid>.ticket
                       one per waiter, locked by it for as long as it waits; an unlocked ticket is dead
    slot-<n>.lock      one per slot (n from 0), locked while a build holds the slot
    slot-<n>.owner     token, wrapper pid and program name (never the arguments) of the last holder,
                       then the build's pid once it starts; a nested call checks its token
On Linux and macOS the directory and its files are readable by the user only (0700 and 0600).

Liveness uses OS file locks (fcntl.flock on Linux and macOS, msvcrt.locking on Windows), never PIDs,
so a reused PID cannot keep a dead ticket or slot alive. Only the oldest live waiter may take a free
slot. On Linux and macOS the command inherits the slot's lock, so a wrapper killed by SIGKILL leaves
the slot held until the build ends. On Windows the wrapper and the build run in a Job Object that is killed
when the wrapper's handle closes, so the build cannot outlive its slot. Standard library only.
"""

from __future__ import annotations

import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

WINDOWS = os.name == "nt"
if WINDOWS:
    import msvcrt
else:
    import fcntl

EXIT_TIMEOUT = 75
EXIT_USAGE = 2
HOLDER_ENV = "BUILD_SLOT_HOLDER"  # shared with older copies, so a nested call of either reuses the slot
PROG = "@PLUGIN@-build-slot"
MAX_ENV, JOBS_ENV, TIMEOUT_ENV, DIR_ENV, GRACE_ENV = (
    f"SWE_BUILD_SLOT_{k}" for k in ("MAX", "JOBS", "TIMEOUT", "DIR", "GRACE"))
RENAMED = {"BUILD_SLOT_SLOTS": MAX_ENV, "BUILD_SLOT_JOBS": JOBS_ENV, "BUILD_SLOT_TIMEOUT": TIMEOUT_ENV,
           "BUILD_SLOT_DIR": DIR_ENV}
# Per-tool job limits: (variable, value given the job count). Each is set only when the caller has not set it.
JOB_LIMITS = (
    ("CARGO_BUILD_JOBS", str),  # Cargo: the build.jobs setting
    ("CMAKE_BUILD_PARALLEL_LEVEL", str),  # cmake --build
)
POLL = 0.2
REPORT_MIN = 5.0
REPORT_EVERY = 60.0


class Interrupted(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def say(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr, flush=True)


def env_int(name: str, default: int, minimum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        say(f"{name}={raw!r} is not a whole number")
        sys.exit(EXIT_USAGE)
    if value < minimum:
        say(f"{name}={value} must be at least {minimum}")
        sys.exit(EXIT_USAGE)
    return value


def queue_dir() -> Path:
    raw = os.environ.get(DIR_ENV, "").strip()
    path = Path(raw).expanduser() if raw else Path.home() / ".cache" / "build-slot"
    try:
        new = not path.exists()
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not WINDOWS and (new or (path / "queue.lock").exists()):  # never chmod a directory that is not a queue
            os.chmod(path, 0o700)
        (path / "tickets").mkdir(mode=0o700, exist_ok=True)
        if not WINDOWS:
            os.chmod(path / "tickets", 0o700)
    except OSError as exc:
        say(f"cannot use the queue directory {path} ({DIR_ENV}): {exc}")
        sys.exit(EXIT_USAGE)
    return path.resolve()


def write_private(path: Path, text: str) -> None:
    """Writes path readable by the user only, also when an older copy created it with the default umask."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        if not WINDOWS:
            os.fchmod(fd, 0o600)
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)


def shown(line: str) -> str:
    """The program name from an owner file; an older copy wrote the whole command line there."""
    return os.path.basename(line.split(" ", 1)[0]) if line else ""


# --- OS locks ---------------------------------------------------------------------------------------

def open_lock(path: Path) -> int:
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
    if not WINDOWS:
        try:
            os.fchmod(fd, 0o600)  # also a lock file made with a wider mode
        except OSError:
            pass
    return fd


def try_lock(fd: int) -> bool:
    try:
        if WINDOWS:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def lock(fd: int) -> None:
    if not WINDOWS:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return
    while not try_lock(fd):
        time.sleep(0.02)


def unlock(fd: int) -> None:
    try:
        if WINDOWS:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def is_locked(path: Path) -> bool:
    """True when another open file holds the lock on path."""
    try:
        fd = os.open(str(path), os.O_RDWR)
    except OSError:
        return False
    try:
        if try_lock(fd):
            unlock(fd)
            return False
        return True
    finally:
        os.close(fd)


class QueueLock:
    def __init__(self, base: Path) -> None:
        self.fd = open_lock(base / "queue.lock")

    def __enter__(self) -> "QueueLock":
        lock(self.fd)
        return self

    def __exit__(self, *exc: object) -> None:
        unlock(self.fd)

    def close(self) -> None:
        os.close(self.fd)


# --- the queue --------------------------------------------------------------------------------------

def ticket_number(path: Path) -> int:
    try:
        return int(path.name.split("-", 1)[0])
    except ValueError:
        return -1


def tickets(base: Path) -> list[Path]:
    found = [p for p in (base / "tickets").glob("*.ticket") if ticket_number(p) >= 0]
    return sorted(found, key=ticket_number)


def next_number(base: Path) -> int:
    counter = base / "counter"
    try:
        last = int(counter.read_text(encoding="ascii").strip() or "0")
    except (OSError, ValueError):
        last = 0
    last = max([last] + [ticket_number(p) for p in tickets(base)]) + 1
    tmp = base / f"counter.{os.getpid()}.tmp"
    write_private(tmp, f"{last}\n")
    os.replace(tmp, counter)
    return last


def drop_if_dead(path: Path) -> bool:
    """Called under the queue lock: removes a ticket nobody holds. True when it was dead."""
    try:
        fd = os.open(str(path), os.O_RDWR)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    try:
        if not try_lock(fd):
            return False
        unlock(fd)
    finally:
        os.close(fd)
    try:
        path.unlink()
    except OSError:
        pass
    return True


class Ticket:
    def __init__(self, base: Path, queue: QueueLock) -> None:
        self.base = base
        self.queue = queue
        with queue:
            self.number = next_number(base)
            self.path = base / "tickets" / f"{self.number:012d}-{os.getpid()}.ticket"
            self.fd = open_lock(self.path)
            lock(self.fd)

    def ahead(self) -> int:
        """Called under the queue lock: live waiters before this one; dead tickets are removed."""
        count = 0
        for path in tickets(self.base):
            if ticket_number(path) >= self.number:
                break
            if not drop_if_dead(path):
                count += 1
        return count

    def leave(self) -> None:
        if self.fd < 0:
            return
        unlock(self.fd)
        os.close(self.fd)
        self.fd = -1
        try:
            self.path.unlink()
        except OSError:
            pass


def take_free_slot(base: Path, slots: int) -> tuple[int, int] | None:
    for index in range(slots):
        fd = open_lock(base / f"slot-{index}.lock")
        if try_lock(fd):
            return index, fd
        os.close(fd)
    return None


def busy_slots(base: Path, slots: int) -> int:
    return sum(is_locked(base / f"slot-{i}.lock") for i in range(slots))


def wait_for_slot(base: Path, slots: int, timeout: int) -> tuple[int, int]:
    queue = QueueLock(base)
    ticket = Ticket(base, queue)
    started = time.monotonic()
    reported_at = 0.0
    reported = None
    try:
        while True:
            with queue:
                ahead = ticket.ahead()
                taken = take_free_slot(base, slots) if ahead == 0 else None
                if taken:
                    ticket.leave()
            if taken:
                waited = time.monotonic() - started
                if reported is not None:
                    say(f"got slot {taken[0]} after {waited:.0f}s")
                return taken
            now = time.monotonic()
            if timeout and now - started >= timeout:
                say(f"no slot after {timeout}s ({TIMEOUT_ENV}); the command did not run")
                raise Interrupted(EXIT_TIMEOUT)
            position = ahead + 1
            if reported is None or (position != reported and now - reported_at >= REPORT_MIN) \
                    or now - reported_at >= REPORT_EVERY:
                busy = busy_slots(base, slots)
                say(f"waiting for a build slot: position {position} in the queue, {busy} of {slots} "
                    f"slots busy, {now - started:.0f}s so far ({base})")
                reported, reported_at = position, now
            time.sleep(POLL)
    finally:
        ticket.leave()
        queue.close()


# --- nested calls -----------------------------------------------------------------------------------

def outer_slot(base: Path) -> int | None:
    """The slot an outer build-slot already holds for this process tree, if any."""
    raw = os.environ.get(HOLDER_ENV, "")
    index, _, token = raw.partition(":")
    if not index.isdigit() or not token:
        return None
    try:
        owner = (base / f"slot-{index}.owner").read_text(encoding="utf-8").split("\n", 1)[0]
    except OSError:
        return None
    if owner != token or not is_locked(base / f"slot-{index}.lock"):
        return None
    return int(index)


# --- Windows Job Object -----------------------------------------------------------------------------

def windows_job() -> object | None:
    """Puts this process (and so every process it starts) in a job killed when this process ends."""
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class Io(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount",
                    "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Io), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        return None
    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
        return None
    return job


# --- running the command ----------------------------------------------------------------------------

def resolve(argv: list[str]) -> list[str]:
    """On Windows find npm.cmd and the like by PATHEXT; CreateProcess alone finds only .exe."""
    if WINDOWS:
        found = shutil.which(argv[0])
        if found:
            return [found] + argv[1:]
    return argv


def descendants(root: int) -> set[int]:
    """The processes below root (Linux: /proc, macOS: ps). Empty when they cannot be read."""
    parents: dict[int, int] = {}
    proc = Path("/proc")
    if proc.is_dir():
        for entry in proc.iterdir():
            if entry.name.isdigit():
                try:
                    stat = (entry / "stat").read_text()
                    parents[int(entry.name)] = int(stat.rsplit(")", 1)[1].split()[1])
                except (OSError, ValueError, IndexError):
                    pass
    else:
        try:
            out = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for line in out.splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[0].isdigit() and fields[1].isdigit():
                parents[int(fields[0])] = int(fields[1])
    found, todo = set(), [root]
    while todo:
        parent = todo.pop()
        for pid, ppid in parents.items():
            if ppid == parent and pid not in found:
                found.add(pid)
                todo.append(pid)
    return found


class Build:
    """The command, run in this process group so that a stop of the whole group reaches it too.

    A SIGTERM or SIGHUP sent to this wrapper alone is passed to the build and to the processes below it, and only to
    them; after the grace period those still running get SIGKILL. The wrapper returns, and frees the slot, only
    once they are gone. SIGKILL of the wrapper cannot be handled: the build runs on and keeps the slot (--status shows
    its pid).
    """

    def __init__(self, child: subprocess.Popen, grace: int) -> None:
        self.child = child
        self.grace = grace
        self.cancelled = 0
        self.started: set[int] = set()

    def ours(self) -> set[int]:
        """Started processes still alive in this process group (a reused pid would sit in another group)."""
        alive = set()
        for pid in self.started:
            try:
                if os.getpgid(pid) == os.getpgrp():
                    alive.add(pid)
            except OSError:
                pass
        return alive

    def signal(self, signum: int) -> None:
        if self.child.poll() is None:
            self.started |= {self.child.pid} | descendants(self.child.pid)
        for pid in self.ours():
            try:
                os.kill(pid, signum)
            except OSError:
                pass

    def cancel(self, signum: int, _frame: object) -> None:
        if self.cancelled:  # a second cancel: stop it now
            self.signal(signal.SIGKILL)
            return
        self.cancelled = signum
        self.signal(signum)

    def wait(self) -> int:
        deadline = None
        while True:
            try:
                code = self.child.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                code = None
            if self.cancelled and deadline is None:
                deadline = time.monotonic() + self.grace
            if code is not None and not (self.cancelled and self.ours()):
                break
            if deadline is not None and time.monotonic() >= deadline:
                self.signal(signal.SIGKILL)
                deadline = time.monotonic() + self.grace
        if self.cancelled:
            say(f"stopped by {signal.Signals(self.cancelled).name}: the build is gone and its slot is free")
            return 128 + self.cancelled
        return 128 - code if code < 0 else code


def run(argv: list[str], env: dict[str, str], slot_fd: int | None, started=None) -> int:
    kwargs = {}
    if slot_fd is not None and not WINDOWS:
        kwargs["pass_fds"] = (slot_fd,)
    try:
        child = subprocess.Popen(resolve(argv), env=env, **kwargs)
    except FileNotFoundError:
        say(f"command not found: {argv[0]}")
        return 127
    except PermissionError:
        say(f"command not executable: {argv[0]}")
        return 126
    except OSError as exc:
        say(f"cannot start {argv[0]}: {exc}")
        return 126
    if started:
        started(child.pid)
    # Ctrl+C at a terminal reaches the build itself (same process group or console); the wrapper only waits for it.
    signal.signal(signal.SIGINT, lambda *_: None)
    if WINDOWS:  # the Job Object ends the build with this process
        code = child.wait()
        return 128 - code if code < 0 else code
    build = Build(child, env_int(GRACE_ENV, 10, 0))
    for name in ("SIGTERM", "SIGHUP"):
        signal.signal(getattr(signal, name), build.cancel)
    return build.wait()


def go_env_file() -> Path | None:
    """The file `go env -w` writes: $GOENV, else <user config dir>/go/env (`go help environment`)."""
    named = os.environ.get("GOENV", "")
    if named == "off":
        return None
    if named:
        return Path(named)
    if WINDOWS:
        base = os.environ.get("APPDATA", "")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "go" / "env" if base else None


def go_flags(env: dict[str, str], jobs: int) -> str | None:
    """GOFLAGS with -p=<jobs> appended, or None when -p is set already. An empty GOFLAGS counts as unset, as in Go."""
    flags = env.get("GOFLAGS", "")
    if not flags:
        path = go_env_file()
        try:
            lines = path.read_text(encoding="utf-8").splitlines() if path else []
        except OSError:
            lines = []
        flags = next((line.split("=", 1)[1] for line in lines if line.startswith("GOFLAGS=")), "")
    if any(flag == "-p" or flag.startswith(("-p=", "--p=")) or flag == "--p" for flag in flags.split()):
        return None
    return f"{flags} -p={jobs}".strip()


def command_env(jobs: int, extra: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    for name, value in JOB_LIMITS:
        if name not in env:
            env[name] = value(jobs)
    goflags = go_flags(env, jobs)
    if goflags is not None:
        env["GOFLAGS"] = goflags
    env.update(extra)
    return env


def warn_renamed() -> None:
    for old, new in RENAMED.items():
        if old in os.environ and new not in os.environ:
            say(f"{old} is no longer read: set {new}")


def raise_interrupted(signum: int, _frame: object) -> None:
    if signum == getattr(signal, "SIGBREAK", None):  # Ctrl+Break on Windows counts as Ctrl+C
        raise KeyboardInterrupt
    raise Interrupted(128 + signum)


def main_run(argv: list[str]) -> int:
    base = queue_dir()
    warn_renamed()
    slots = env_int(MAX_ENV, 2, 1)
    timeout = env_int(TIMEOUT_ENV, 0, 0)
    jobs = env_int(JOBS_ENV, 6, 1)
    if outer_slot(base) is not None:
        return run(argv, command_env(jobs, {}), None)
    previous = {}
    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        if hasattr(signal, name):
            previous[name] = signal.signal(getattr(signal, name), raise_interrupted)
    try:
        index, slot_fd = wait_for_slot(base, slots, timeout)
    except KeyboardInterrupt:
        say("interrupted while waiting; left the queue, the command did not run")
        return 130
    except Interrupted as exc:
        if exc.code != EXIT_TIMEOUT:
            say("stopped while waiting; left the queue, the command did not run")
        return exc.code
    for name, handler in previous.items():
        signal.signal(getattr(signal, name), handler)
    token = secrets.token_hex(8)
    owner = base / f"slot-{index}.owner"
    write_private(owner, f"{token}\n{os.getpid()}\n{os.path.basename(argv[0])}\n")
    if WINDOWS and windows_job() is None:
        say("warning: no Job Object; if this wrapper is killed the build keeps running without a slot")
    def started(pid: int) -> None:
        fd = os.open(str(owner), os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd, f"{pid}\n".encode())
        finally:
            os.close(fd)

    try:
        return run(argv, command_env(jobs, {HOLDER_ENV: f"{index}:{token}"}), slot_fd, started)
    finally:
        unlock(slot_fd)
        os.close(slot_fd)


def running(pid: int) -> bool:
    if WINDOWS:
        return True  # only shown as gone where that can be told
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        pass
    return True


def main_status() -> int:
    base = queue_dir()
    warn_renamed()
    slots = env_int(MAX_ENV, 2, 1)
    print(f"queue {base}, {slots} slots")
    for index in range(slots):
        held = is_locked(base / f"slot-{index}.lock")
        detail = ""
        if held:
            try:
                lines = (base / f"slot-{index}.owner").read_text(encoding="utf-8").splitlines()
                detail = f"  {shown(lines[2])}, wrapper pid {lines[1]}"
                if len(lines) > 3:
                    detail += f", build pid {lines[3]}"
                    if not running(int(lines[1])):
                        detail += f" (wrapper gone: stop the build you started with `kill {lines[3]}`)"
            except (OSError, IndexError):
                pass
        print(f"slot {index}: {'busy' if held else 'free'}{detail}")
    waiting = [p for p in tickets(base) if is_locked(p)]
    print(f"{len(waiting)} waiting")
    for position, path in enumerate(waiting, 1):
        print(f"  {position}. ticket {ticket_number(path)}, pid {path.stem.split('-', 1)[1]}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--"]:
        argv = argv[1:]
    elif argv[:1] == ["--status"]:
        return main_status()
    elif argv[:1] in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    if not argv or argv[0].startswith("-"):
        say(f"usage: {PROG} <command> [args...]   or   {PROG} --status | --help")
        return EXIT_USAGE
    return main_run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
