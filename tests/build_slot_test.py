#!/usr/bin/env python3
"""Tests of src/skills/build-slot/scripts/build-slot.py on Linux, macOS and Windows.

    python3 tests/build_slot_test.py [-v]

Each test uses its own temporary queue directory and tiny Python commands, never a real build, and
never touches the user's own queue. Standard library only.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "src" / "skills" / "build-slot" / "scripts" / "build-slot.py"
WINDOWS = os.name == "nt"
WAIT = 30.0


def wait_until(predicate, timeout: float = WAIT, what: str = "condition") -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {what}")


def py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


class BuildSlotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="build-slot-test-"))
        self.queue = self.tmp / "queue"
        self.procs: list[subprocess.Popen] = []
        self.releases: list[Path] = []
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("BUILD_SLOT") and k != "CARGO_BUILD_JOBS"}
        self.env["BUILD_SLOT_DIR"] = str(self.queue)
        self.env["BUILD_SLOT_SLOTS"] = "1"
        self.count = 0

    def tearDown(self) -> None:
        for release in self.releases:
            release.touch()
        for proc in self.procs:
            try:
                proc.wait(timeout=WAIT)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        time.sleep(0.2)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- helpers ------------------------------------------------------------------------------------

    def start(self, command: list[str], wrapper: list[str] | None = None, group: bool = False, **env: str):
        self.count += 1
        log = open(self.tmp / f"wrapper-{self.count}.log", "w")
        kwargs = {}
        if group and WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        elif group:  # a shell running this in the background may have set SIGINT to ignored
            kwargs["preexec_fn"] = lambda: signal.signal(signal.SIGINT, signal.SIG_DFL)
        wrapper = [sys.executable, str(SCRIPT)] if wrapper is None else wrapper
        proc = subprocess.Popen(wrapper + command, env={**self.env, **env},
                                stdout=log, stderr=subprocess.STDOUT, **kwargs)
        proc.log = self.tmp / f"wrapper-{self.count}.log"
        log.close()
        self.procs.append(proc)
        return proc

    def run_wrapper(self, command: list[str], **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT)] + command, env={**self.env, **env},
                              capture_output=True, text=True, timeout=WAIT)

    def holder(self, name: str, **env: str):
        """A build that holds its slot until its release file exists; writes <name>.started and .done."""
        started, release, done = (self.tmp / f"{name}.{s}" for s in ("started", "release", "done"))
        self.releases.append(release)
        code = (f"import os, time\nopen({str(started)!r}, 'w').write(str(os.getpid()))\n"
                f"while not os.path.exists({str(release)!r}): time.sleep(0.05)\n"
                f"open({str(done)!r}, 'w').close()\n")
        return self.start(py(code), **env), started, release, done

    def appender(self, name: str) -> list[str]:
        order = self.tmp / "order.txt"
        return py(f"open({str(order)!r}, 'a').write({name + chr(10)!r})")

    def order(self) -> list[str]:
        path = self.tmp / "order.txt"
        return path.read_text().split() if path.exists() else []

    def tickets(self) -> list[Path]:
        return sorted((self.queue / "tickets").glob("*.ticket"))

    def enqueue(self, command: list[str], group: bool = False, **env: str):
        before = len(self.tickets())
        proc = self.start(command, group=group, **env)
        wait_until(lambda: len(self.tickets()) > before, what="the waiter's ticket")
        return proc

    def wait_ok(self, proc, code: int = 0) -> None:
        self.assertEqual(proc.wait(timeout=WAIT), code, proc.log.read_text())

    # --- tests --------------------------------------------------------------------------------------

    def test_exit_code_is_the_commands(self) -> None:
        self.assertEqual(self.run_wrapper(py("raise SystemExit(3)")).returncode, 3)
        self.assertEqual(self.run_wrapper(py("pass")).returncode, 0)
        missing = self.run_wrapper(["no-such-command-build-slot-test"])
        self.assertEqual(missing.returncode, 127, missing.stderr)
        self.assertEqual(self.run_wrapper([]).returncode, 2)
        self.assertEqual(self.run_wrapper(["--bogus"]).returncode, 2)
        self.assertEqual(self.run_wrapper(["--", *py("raise SystemExit(4)")]).returncode, 4)
        if not WINDOWS:
            killed = self.run_wrapper(py("import os, signal; os.kill(os.getpid(), signal.SIGTERM)"))
            self.assertEqual(killed.returncode, 128 + signal.SIGTERM)

    def test_cargo_jobs_default_and_never_overridden(self) -> None:
        show = py("import os, sys; sys.stdout.write(os.environ['CARGO_BUILD_JOBS'])")
        self.assertEqual(self.run_wrapper(show).stdout, "6")
        self.assertEqual(self.run_wrapper(show, CARGO_BUILD_JOBS="3").stdout, "3")
        self.assertEqual(self.run_wrapper(show, BUILD_SLOT_JOBS="4").stdout, "4")
        self.assertEqual(self.run_wrapper(show, BUILD_SLOT_JOBS="4", CARGO_BUILD_JOBS="2").stdout, "2")
        self.assertEqual(self.run_wrapper(show, BUILD_SLOT_SLOTS="0").returncode, 2)

    def test_queueing_with_two_slots(self) -> None:
        self.env["BUILD_SLOT_SLOTS"] = "2"
        a, a_started, a_release, _ = self.holder("a")
        b, b_started, b_release, _ = self.holder("b")
        wait_until(lambda: a_started.exists() and b_started.exists(), what="two builds in two slots")
        c, c_started, c_release, _ = self.holder("c")
        wait_until(lambda: len(self.tickets()) == 1, what="the third build queued")
        time.sleep(0.6)
        self.assertFalse(c_started.exists(), "a third build ran with two slots")
        status = self.run_wrapper(["--status"]).stdout
        self.assertIn("slot 0: busy", status)
        self.assertIn("slot 1: busy", status)
        self.assertIn("1 waiting", status)
        wait_until(lambda: "position 1 in the queue" in c.log.read_text(), what="the queue position on stderr")
        a_release.touch()
        self.wait_ok(a)
        wait_until(c_started.exists, what="the queued build to start")
        b_release.touch()
        c_release.touch()
        self.wait_ok(b)
        self.wait_ok(c)
        self.assertIn("got slot", c.log.read_text())
        self.assertEqual(self.tickets(), [])

    def test_never_more_builds_than_slots(self) -> None:
        self.env["BUILD_SLOT_SLOTS"] = "2"
        running = self.tmp / "running"
        running.mkdir()
        peaks = self.tmp / "peaks"  # one file per build: two builds run at once, and a shared append can lose a line
        peaks.mkdir()
        code = (f"import os, time, uuid\nmine = os.path.join({str(running)!r}, uuid.uuid4().hex)\n"
                f"open(mine, 'w').close()\nn = len(os.listdir({str(running)!r}))\n"
                f"time.sleep(0.3)\nn = max(n, len(os.listdir({str(running)!r})))\n"
                f"open(os.path.join({str(peaks)!r}, os.path.basename(mine)), 'w').write(str(n))\nos.remove(mine)\n")
        procs = [self.start(py(code)) for _ in range(8)]
        for proc in procs:
            self.wait_ok(proc)
        counts = [int(p.read_text()) for p in peaks.iterdir()]
        self.assertEqual(len(counts), 8)
        self.assertLessEqual(max(counts), 2, counts)
        self.assertEqual(self.tickets(), [])

    def test_fifo_order(self) -> None:
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        names = [f"w{i}" for i in range(1, 7)]
        waiters = [self.enqueue(self.appender(name)) for name in names]
        release.touch()
        self.wait_ok(h)
        for proc in waiters:
            self.wait_ok(proc)
        self.assertEqual(self.order(), names)

    def test_dead_waiter_is_skipped(self) -> None:
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        dead = self.enqueue(self.appender("dead"))
        alive = self.enqueue(self.appender("alive"))
        dead.kill()
        dead.wait(timeout=WAIT)
        self.assertEqual(len(self.tickets()), 2, "the killed waiter's ticket should be left behind")
        release.touch()
        self.wait_ok(h)
        self.wait_ok(alive)
        self.assertEqual(self.order(), ["alive"])
        self.assertEqual(self.tickets(), [])

    def test_interrupt_while_waiting_leaves_the_queue(self) -> None:
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        first = self.enqueue(self.appender("first"), group=True)
        second = self.enqueue(self.appender("second"))
        os.kill(first.pid, signal.CTRL_BREAK_EVENT if WINDOWS else signal.SIGINT)
        self.assertEqual(first.wait(timeout=WAIT), 130, first.log.read_text())
        self.assertIn("left the queue", first.log.read_text())
        self.assertEqual(len(self.tickets()), 1)
        if not WINDOWS:
            third = self.enqueue(self.appender("third"))
            third.terminate()
            self.assertEqual(third.wait(timeout=WAIT), 128 + signal.SIGTERM, third.log.read_text())
            self.assertEqual(len(self.tickets()), 1)
        release.touch()
        self.wait_ok(h)
        self.wait_ok(second)
        self.assertEqual(self.order(), ["second"])
        self.assertEqual(self.tickets(), [])

    def test_timeout_exits_75_without_running(self) -> None:
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        begin = time.monotonic()
        result = self.run_wrapper(self.appender("late"), BUILD_SLOT_TIMEOUT="1")
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertLess(time.monotonic() - begin, 15)
        self.assertIn("did not run", result.stderr)
        self.assertEqual(self.order(), [])
        self.assertEqual(self.tickets(), [])
        release.touch()
        self.wait_ok(h)

    def test_nested_call_reuses_the_slot(self) -> None:
        inner = [sys.executable, str(SCRIPT)] + py("raise SystemExit(7)")
        # with one slot, an inner call that queued would wait for itself; the timeout makes that exit 75, not hang
        result = self.run_wrapper([sys.executable, str(SCRIPT)] + inner, BUILD_SLOT_TIMEOUT="10")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertNotIn("waiting", result.stderr)

    def test_a_forged_holder_does_not_skip_the_queue(self) -> None:
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        result = self.run_wrapper(self.appender("forged"), BUILD_SLOT_TIMEOUT="1", BUILD_SLOT_HOLDER="0:forged")
        self.assertEqual(result.returncode, 75, result.stderr)
        release.touch()
        self.wait_ok(h)

    def test_killed_wrapper(self) -> None:
        h, started, release, done = self.holder("h")
        wait_until(started.exists, what="the holder")
        h.kill()
        h.wait(timeout=WAIT)
        if WINDOWS:
            # the Job Object ends the build with its wrapper: the slot is free and the build never finishes
            result = self.run_wrapper(self.appender("next"), BUILD_SLOT_TIMEOUT="20")
            self.assertEqual(result.returncode, 0, result.stderr)
            release.touch()
            time.sleep(1.0)
            self.assertFalse(done.exists(), "the build kept running after its wrapper was killed")
            return
        # the build inherited the slot's lock: it keeps the slot until it ends
        result = self.run_wrapper(self.appender("next"), BUILD_SLOT_TIMEOUT="1")
        self.assertEqual(result.returncode, 75, result.stderr)
        release.touch()
        wait_until(done.exists, what="the orphaned build to finish")
        result = self.run_wrapper(self.appender("next"), BUILD_SLOT_TIMEOUT="20")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.order(), ["next"])

    def test_no_argument_in_queue_files_or_status(self) -> None:
        secret = "tok-" + "9f3Kq2xLw7Zs"
        started, release = self.tmp / "s.started", self.tmp / "s.release"
        self.releases.append(release)
        code = (f"import os, time\nopen({str(started)!r}, 'w').close()\n"
                f"while not os.path.exists({str(release)!r}): time.sleep(0.05)\n")
        proc = self.start(py(code) + ["--build-arg", f"TOKEN={secret}", f"--password={secret}"])
        wait_until(started.exists, what="the build holding a slot")

        def leaks() -> list[str]:
            found = [str(p) for p in self.queue.rglob("*") if p.is_file() and secret.encode() in p.read_bytes()]
            status = self.run_wrapper(["--status"]).stdout
            return found + (["--status"] if secret in status else [])

        status = self.run_wrapper(["--status"]).stdout
        self.assertIn(f"slot 0: busy  pid {proc.pid}: {Path(sys.executable).name}", status)
        self.assertEqual(leaks(), [])
        release.touch()
        self.wait_ok(proc)
        self.assertEqual(leaks(), [])
        # an owner file written by an older copy holds the whole command line: --status shows only the program
        held = self.holder("h")
        wait_until(held[1].exists, what="the next build")
        (self.queue / "slot-0.owner").write_text(f"old\n1\n/usr/bin/docker build --build-arg TOKEN={secret} .\n")
        status = self.run_wrapper(["--status"]).stdout
        self.assertIn("slot 0: busy  pid 1: docker", status)
        self.assertNotIn(secret, status)

    @unittest.skipIf(WINDOWS, "POSIX file modes")
    def test_queue_is_readable_by_the_user_only(self) -> None:
        self.queue.mkdir(mode=0o755)
        (self.queue / "queue.lock").touch()
        old_owner = self.queue / "slot-0.owner"
        old_owner.write_text("old\n1\nmake\n")
        os.chmod(self.queue, 0o755)
        os.chmod(old_owner, 0o644)
        self.assertEqual(self.run_wrapper(py("pass")).returncode, 0)
        modes = {str(p.relative_to(self.queue)): p.stat().st_mode & 0o777 for p in [self.queue, *self.queue.rglob("*")]}
        for name, mode in modes.items():
            self.assertEqual(mode & 0o077, 0, f"{name} is {oct(mode)}")
        self.assertEqual(modes["."], 0o700)
        # a directory that is not a queue is never chmodded
        other = self.tmp / "other"
        other.mkdir(mode=0o755)
        os.chmod(other, 0o755)
        self.assertEqual(self.run_wrapper(py("pass"), BUILD_SLOT_DIR=str(other)).returncode, 0)
        self.assertEqual(other.stat().st_mode & 0o777, 0o755)

    @unittest.skipUnless(WINDOWS, "Windows .cmd tools")
    def test_windows_cmd_tool_by_bare_name(self) -> None:
        tools = self.tmp / "tools"
        tools.mkdir()
        (tools / "slot-tool.cmd").write_text('@echo %~1>"%~dp0arg.txt"\r\n@exit /b 5\r\n')
        path = str(tools) + os.pathsep + self.env.get("PATH", "")
        result = self.run_wrapper(["slot-tool", "hello"], PATH=path)
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertEqual((tools / "arg.txt").read_text().strip(), "hello")


if __name__ == "__main__":
    unittest.main()
