#!/usr/bin/env python3
"""Run a heavy build command in one of a few shared build slots, waiting in a FIFO queue.

    python3 build-slot.py <command> [args...]    # run the command when a slot is free
    python3 build-slot.py --status               # print the slots and the queue

Every copy of this script on a machine shares one queue per user: the directory
BUILD_SLOT_DIR (default ~/.cache/build-slot). Standard library only.

Environment:
    BUILD_SLOT_SLOTS    number of slots (default 2); every agent on a queue should use the same value
    BUILD_SLOT_JOBS     CARGO_BUILD_JOBS given to the command when it is not set already (default 6)
    BUILD_SLOT_TIMEOUT  seconds to wait for a slot, then exit 75 without running the command (default: no limit)
    BUILD_SLOT_DIR      the queue directory (default ~/.cache/build-slot)

Exit codes: the command's own; 75 the wait timed out (the command did not run); 130 interrupted while
waiting (143 on SIGTERM); 127 command not found; 126 command not executable; 2 usage error.

Layout of the queue directory (stable; other copies of this script rely on it):
    queue.lock         locked briefly while joining, checking or leaving the queue
    counter            the last ticket number given out
    tickets/<12-digit number>-<pid>.ticket
                       one per waiter, locked by it for as long as it waits; an unlocked ticket is dead
    slot-<n>.lock      one per slot (n from 0), locked while a build holds the slot
    slot-<n>.owner     token, pid and command of the last holder; a nested call checks its token

Liveness uses OS file locks (fcntl.flock on Linux and macOS, msvcrt.locking on Windows), never PIDs,
so a reused PID cannot keep a dead ticket or slot alive. Only the oldest live waiter may take a free
slot. On Linux and macOS the command inherits the slot's lock, so a killed wrapper leaves the slot
held until the build ends. On Windows the wrapper and the build run in a Job Object that is killed
when the wrapper's handle closes, so the build cannot outlive its slot.
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
HOLDER_ENV = "BUILD_SLOT_HOLDER"
POLL = 0.2
REPORT_MIN = 5.0
REPORT_EVERY = 60.0


class Interrupted(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def say(message: str) -> None:
    print(f"build-slot: {message}", file=sys.stderr, flush=True)


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
    raw = os.environ.get("BUILD_SLOT_DIR", "").strip()
    path = Path(raw).expanduser() if raw else Path.home() / ".cache" / "build-slot"
    try:
        (path / "tickets").mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        say(f"cannot use the queue directory {path} (BUILD_SLOT_DIR): {exc}")
        sys.exit(EXIT_USAGE)
    return path.resolve()


# --- OS locks ---------------------------------------------------------------------------------------

def open_lock(path: Path) -> int:
    return os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)


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
    tmp.write_text(f"{last}\n", encoding="ascii")
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
                say(f"no slot after {timeout}s (BUILD_SLOT_TIMEOUT); the command did not run")
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


def run(argv: list[str], env: dict[str, str], slot_fd: int | None) -> int:
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
    # Ctrl+C reaches the build itself (same process group or console); the wrapper only waits for it.
    signal.signal(signal.SIGINT, lambda *_: None)
    code = child.wait()
    return 128 - code if code < 0 else code


def command_env(jobs: int, extra: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("CARGO_BUILD_JOBS", str(jobs))
    env.update(extra)
    return env


def raise_interrupted(signum: int, _frame: object) -> None:
    if signum == getattr(signal, "SIGBREAK", None):  # Ctrl+Break on Windows counts as Ctrl+C
        raise KeyboardInterrupt
    raise Interrupted(128 + signum)


def main_run(argv: list[str]) -> int:
    base = queue_dir()
    slots = env_int("BUILD_SLOT_SLOTS", 2, 1)
    timeout = env_int("BUILD_SLOT_TIMEOUT", 0, 0)
    jobs = env_int("BUILD_SLOT_JOBS", 6, 1)
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
    owner.write_text(f"{token}\n{os.getpid()}\n{' '.join(argv)}\n", encoding="utf-8")
    if WINDOWS and windows_job() is None:
        say("warning: no Job Object; if this wrapper is killed the build keeps running without a slot")
    try:
        return run(argv, command_env(jobs, {HOLDER_ENV: f"{index}:{token}"}), slot_fd)
    finally:
        unlock(slot_fd)
        os.close(slot_fd)


def main_status() -> int:
    base = queue_dir()
    slots = env_int("BUILD_SLOT_SLOTS", 2, 1)
    print(f"queue {base}, {slots} slots")
    for index in range(slots):
        held = is_locked(base / f"slot-{index}.lock")
        detail = ""
        if held:
            try:
                lines = (base / f"slot-{index}.owner").read_text(encoding="utf-8").splitlines()
                detail = f"  pid {lines[1]}: {lines[2]}"
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
        say("usage: build-slot.py <command> [args...]   or   build-slot.py --status")
        return EXIT_USAGE
    return main_run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
