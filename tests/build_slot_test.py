#!/usr/bin/env python3
"""Tests of the build-slot command (src/skills/build-slot/scripts/@PLUGIN@-build-slot.py, run as built) and of its
install by scripts/install.py, on Linux, macOS and Windows.

    python3 tests/build_slot_test.py [-v]

It builds dist/<name> first. Each test uses its own temporary queue directory, home and tiny Python commands,
never a real build, and never touches the user's own queue, bin directory or Go settings. Standard library only.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = os.name == "nt"


def build() -> tuple[str, Path]:
    """Builds the plugin (as make build does) and returns its name and dist directory."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("PLUGIN_")}
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], env=env, capture_output=True, text=True)
    if run.returncode:
        sys.exit(f"build failed:\n{run.stdout}{run.stderr}")
    name = re.search(r"built dist/(\S+):", run.stdout).group(1)
    return name, ROOT / "dist" / name


NAME, DIST = build()
COMMAND = f"{NAME}-build-slot"
SCRIPT = DIST / "skills" / "build-slot" / "scripts" / f"{COMMAND}.py"
INSTALLER = DIST / "scripts" / "install.py"
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
        own = ("BUILD_SLOT", "SWE_BUILD_SLOT", "CARGO_BUILD_JOBS", "CMAKE_BUILD_PARALLEL_LEVEL", "GOFLAGS", "PLUGIN_")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(own)}
        self.env["GOENV"] = "off"  # never the user's `go env -w` settings
        self.env["SWE_BUILD_SLOT_DIR"] = str(self.queue)
        self.env["SWE_BUILD_SLOT_MAX"] = "1"
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
        self.assertEqual(self.run_wrapper(show, SWE_BUILD_SLOT_JOBS="4").stdout, "4")
        self.assertEqual(self.run_wrapper(show, SWE_BUILD_SLOT_JOBS="4", CARGO_BUILD_JOBS="2").stdout, "2")
        self.assertEqual(self.run_wrapper(show, SWE_BUILD_SLOT_MAX="0").returncode, 2)

    def test_job_limits_for_cmake_and_go_never_override(self) -> None:
        show = py("import os, sys; sys.stdout.write(os.environ.get(sys.argv[1], '<unset>'))")
        cmake, goflags = show + ["CMAKE_BUILD_PARALLEL_LEVEL"], show + ["GOFLAGS"]
        self.assertEqual(self.run_wrapper(cmake).stdout, "6")
        self.assertEqual(self.run_wrapper(cmake, CMAKE_BUILD_PARALLEL_LEVEL="").stdout, "")
        self.assertEqual(self.run_wrapper(cmake, SWE_BUILD_SLOT_JOBS="3").stdout, "3")
        self.assertEqual(self.run_wrapper(goflags).stdout, "-p=6")
        self.assertEqual(self.run_wrapper(goflags, GOFLAGS="-mod=mod -tags=a,b").stdout, "-mod=mod -tags=a,b -p=6")
        self.assertEqual(self.run_wrapper(goflags, GOFLAGS="-p=2 -mod=mod").stdout, "-p=2 -mod=mod")
        self.assertEqual(self.run_wrapper(goflags, GOFLAGS="-mod=mod --p=3").stdout, "-mod=mod --p=3")
        for untouched in ("GOMAXPROCS", "MAKEFLAGS"):  # passed on exactly as the caller has them (make sets MAKEFLAGS)
            self.assertEqual(self.run_wrapper(show + [untouched]).stdout, self.env.get(untouched, "<unset>"))
        # GOFLAGS set with `go env -w` lives in the Go env file; the wrapper keeps it
        go_env = self.tmp / "go-env"
        go_env.write_text("GOFLAGS=-mod=vendor -trimpath\nGOPROXY=off\n")
        self.assertEqual(self.run_wrapper(goflags, GOENV=str(go_env)).stdout, "-mod=vendor -trimpath -p=6")
        go_env.write_text("GOFLAGS=-p=1\n")
        self.assertEqual(self.run_wrapper(goflags, GOENV=str(go_env)).stdout, "<unset>")

    @unittest.skipUnless(shutil.which("go"), "go is not installed")
    def test_go_reads_the_goflags_it_gets(self) -> None:
        go_env = self.tmp / "go-env"
        go_env.write_text("GOFLAGS=-mod=mod\n")
        result = self.run_wrapper(["go", "env", "GOFLAGS"], GOENV=str(go_env))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "-mod=mod -p=6")

    def test_old_setting_names_are_reported(self) -> None:
        del self.env["SWE_BUILD_SLOT_MAX"]
        result = self.run_wrapper(py("pass"), BUILD_SLOT_SLOTS="5")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("no longer read", self.run_wrapper(py("pass"), BUILD_SLOT_SLOTS="5",
                                                            SWE_BUILD_SLOT_MAX="2").stderr)
        self.assertIn("BUILD_SLOT_SLOTS is no longer read: set SWE_BUILD_SLOT_MAX", result.stderr)

    def test_help_lists_the_settings(self) -> None:
        result = self.run_wrapper(["--help"])
        self.assertEqual(result.returncode, 0)
        for word in ("SWE_BUILD_SLOT_MAX", "SWE_BUILD_SLOT_JOBS", "SWE_BUILD_SLOT_TIMEOUT", "SWE_BUILD_SLOT_DIR",
                     "CARGO_BUILD_JOBS", "CMAKE_BUILD_PARALLEL_LEVEL", "GOFLAGS", f"{COMMAND} <command>"):
            self.assertIn(word, result.stdout)
        self.assertNotIn("@PLUGIN@", result.stdout)

    def concurrent(self, builds: int) -> tuple[list, list[Path]]:
        holders = [self.holder(f"c{i}") for i in range(builds)]
        return holders, [h[1] for h in holders]

    def test_default_max_is_two(self) -> None:
        del self.env["SWE_BUILD_SLOT_MAX"]
        holders, started = self.concurrent(3)
        wait_until(lambda: sum(p.exists() for p in started) == 2, what="two builds running")
        wait_until(lambda: len(self.tickets()) == 1, what="the third build queued")
        time.sleep(0.5)
        self.assertEqual(sum(p.exists() for p in started), 2)

    def test_max_raised_by_the_environment(self) -> None:
        self.env["SWE_BUILD_SLOT_MAX"] = "3"
        holders, started = self.concurrent(4)
        wait_until(lambda: sum(p.exists() for p in started) == 3, what="three builds running together")
        wait_until(lambda: len(self.tickets()) == 1, what="the fourth build queued")
        time.sleep(0.5)
        running = [h for h in holders if h[1].exists()]
        self.assertEqual(len(running), 3)
        self.assertTrue(all(h[0].poll() is None for h in running), "the three builds must run at the same time")
        running[0][2].touch()
        wait_until(lambda: all(p.exists() for p in started), what="the fourth build to start")

    def test_queueing_with_two_slots(self) -> None:
        self.env["SWE_BUILD_SLOT_MAX"] = "2"
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
        self.env["SWE_BUILD_SLOT_MAX"] = "2"
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
        result = self.run_wrapper(self.appender("late"), SWE_BUILD_SLOT_TIMEOUT="1")
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
        result = self.run_wrapper([sys.executable, str(SCRIPT)] + inner, SWE_BUILD_SLOT_TIMEOUT="10")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertNotIn("waiting", result.stderr)

    def test_a_forged_holder_does_not_skip_the_queue(self) -> None:
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        result = self.run_wrapper(self.appender("forged"), SWE_BUILD_SLOT_TIMEOUT="1", BUILD_SLOT_HOLDER="0:forged")
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
            result = self.run_wrapper(self.appender("next"), SWE_BUILD_SLOT_TIMEOUT="20")
            self.assertEqual(result.returncode, 0, result.stderr)
            release.touch()
            time.sleep(1.0)
            self.assertFalse(done.exists(), "the build kept running after its wrapper was killed")
            return
        # the build inherited the slot's lock: it keeps the slot until it ends
        result = self.run_wrapper(self.appender("next"), SWE_BUILD_SLOT_TIMEOUT="1")
        self.assertEqual(result.returncode, 75, result.stderr)
        release.touch()
        wait_until(done.exists, what="the orphaned build to finish")
        result = self.run_wrapper(self.appender("next"), SWE_BUILD_SLOT_TIMEOUT="20")
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
            found = []
            for path in (p for p in self.queue.rglob("*") if p.is_file()):
                try:
                    data = path.read_bytes()
                except PermissionError:  # Windows: a held lock file cannot be read; lock files stay empty
                    data = b"" if path.stat().st_size == 0 else secret.encode()
                if secret.encode() in data:
                    found.append(str(path))
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
        self.assertEqual(self.run_wrapper(py("pass"), SWE_BUILD_SLOT_DIR=str(other)).returncode, 0)
        self.assertEqual(other.stat().st_mode & 0o777, 0o755)

    # --- make: the BUILD_SLOT prefix variable of a project's Makefile --------------------------------------

    def makefile(self) -> Path:
        """A project whose verify target compiles (prefixed line) and then tests (unprefixed line)."""
        project = self.tmp / "project"
        project.mkdir()
        (project / "record.py").write_text(
            "import os, sys\nopen(sys.argv[1] + '.txt', 'w').write(os.environ.get('BUILD_SLOT_HOLDER', 'none'))\n")
        (project / "Makefile").write_text(
            "BUILD_SLOT ?=\nPY ?= python3\n\nverify:\n"
            "\t$(BUILD_SLOT) \"$(PY)\" record.py compile\n"
            "\t\"$(PY)\" record.py test\n")
        return project

    def make(self, project: Path, prefix: list[str] | None = None) -> list[str]:
        command = [shutil.which("make"), "-s", "-C", str(project), "verify", f"PY={sys.executable}"]
        return (prefix or []) + command

    def spaced_wrapper(self) -> str:
        """The wrapper copied to a path with spaces, as the BUILD_SLOT value an agent passes."""
        copy = self.tmp / "skill dir" / "scripts" / "build-slot.py"
        copy.parent.mkdir(parents=True)
        shutil.copy(SCRIPT, copy)
        return f'"{sys.executable}" "{copy}"'

    def recorded(self, project: Path) -> tuple[str, str]:
        return (project / "compile.txt").read_text(), (project / "test.txt").read_text()

    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_make_with_an_empty_prefix_runs_unchanged(self) -> None:
        project = self.makefile()
        result = subprocess.run(self.make(project), env=self.env, capture_output=True, text=True, timeout=WAIT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.recorded(project), ("none", "none"))
        self.assertFalse(self.queue.exists(), "an empty BUILD_SLOT must not touch the queue")

    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_make_prefix_queues_only_the_compile_line(self) -> None:
        project = self.makefile()
        h, started, release, _ = self.holder("h")
        wait_until(started.exists, what="the holder")
        proc = self.start(self.make(project), wrapper=[], BUILD_SLOT=self.spaced_wrapper())
        wait_until(lambda: len(self.tickets()) == 1, what="the prefixed compile line queued")
        time.sleep(0.5)
        self.assertFalse((project / "compile.txt").exists(), "the compile line ran without a slot")
        self.assertFalse((project / "test.txt").exists(), "the test line ran before the compile line")
        release.touch()
        self.wait_ok(h)
        self.wait_ok(proc)
        compiled, tested = self.recorded(project)
        self.assertNotEqual(compiled, "none", "the compile line did not run in a slot")
        self.assertEqual(tested, "none", "the test line held a slot")

    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_make_wrapped_and_prefixed_does_not_deadlock(self) -> None:
        project = self.makefile()
        wrapper = [sys.executable, str(SCRIPT)]
        result = subprocess.run(self.make(project, prefix=wrapper), capture_output=True, text=True, timeout=WAIT,
                                env={**self.env, "BUILD_SLOT": self.spaced_wrapper(), "SWE_BUILD_SLOT_TIMEOUT": "10"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        compiled, tested = self.recorded(project)
        self.assertNotEqual(compiled, "none")
        self.assertEqual(compiled, tested, "both lines run in the outer slot when make itself is wrapped")

    @unittest.skipUnless(WINDOWS, "Windows .cmd tools")
    def test_windows_cmd_tool_by_bare_name(self) -> None:
        tools = self.tmp / "tools"
        tools.mkdir()
        (tools / "slot-tool.cmd").write_text('@echo %~1>"%~dp0arg.txt"\r\n@exit /b 5\r\n')
        path = str(tools) + os.pathsep + self.env.get("PATH", "")
        result = self.run_wrapper(["slot-tool", "hello"], PATH=path)
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertEqual((tools / "arg.txt").read_text().strip(), "hello")


class InstallTest(unittest.TestCase):
    """scripts/install.py puts the command in a bin directory of a temporary home; never the real one."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="build-slot-install-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        own = ("BUILD_SLOT", "SWE_BUILD_SLOT", "PLUGIN_", "BIN_DIR")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(own)}
        self.env.update(PLUGIN_HOME=str(self.home), SWE_BUILD_SLOT_DIR=str(self.tmp / "queue"), GOENV="off")
        self.bin = self.home / ".local" / "bin"
        self.files = [f"{COMMAND}.cmd", f"{COMMAND}.py"] if WINDOWS else [COMMAND]

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def installer(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(INSTALLER), *args], env={**self.env, **env}, cwd=self.tmp,
                              capture_output=True, text=True, timeout=120)

    def test_install_status_reinstall_and_uninstall(self) -> None:
        result = self.installer("install", "--bin-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(p.name for p in self.bin.iterdir()), sorted(self.files))
        if not WINDOWS:
            self.assertTrue(os.access(self.bin / COMMAND, os.X_OK))
        self.assertIn("is not on PATH", result.stdout)
        self.assertIn("SetEnvironmentVariable" if WINDOWS else "fish_add_path", result.stdout)
        self.assertIn(f"{COMMAND:15} installed", self.installer("status", "--bin-only").stdout)
        self.assertEqual(self.installer("install", "--bin-only").returncode, 0, "a reinstall replaces its own files")
        result = self.installer("uninstall", "--bin-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.bin.iterdir()), [])
        self.assertIn("not installed", self.installer("status", "--bin-only").stdout)

    def test_dry_run_writes_nothing(self) -> None:
        result = self.installer("install", "--bin-only", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("would write", result.stdout)
        self.assertFalse(self.bin.exists())
        self.installer("install", "--bin-only")
        self.assertIn("would remove", self.installer("uninstall", "--bin-only", "--dry-run").stdout)
        self.assertEqual(sorted(p.name for p in self.bin.iterdir()), sorted(self.files))

    def test_never_overwrites_a_file_it_did_not_write(self) -> None:
        self.bin.mkdir(parents=True)
        foreign = self.bin / self.files[0]
        foreign.write_text("someone else's command\n")
        result = self.installer("install", "--bin-only")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("did not write", result.stdout)
        self.assertEqual(foreign.read_text(), "someone else's command\n")
        self.assertEqual(self.installer("uninstall", "--bin-only").returncode, 0)
        self.assertEqual(foreign.read_text(), "someone else's command\n")

    def test_no_warning_when_on_path_and_project_scope_installs_no_command(self) -> None:
        path = str(self.bin) + os.pathsep + self.env.get("PATH", "")
        result = self.installer("install", "--bin-only", PATH=path)
        self.assertNotIn("not on PATH", result.stdout)
        other = self.tmp / "project"
        other.mkdir()
        self.installer("uninstall", "--bin-only")
        result = self.installer("install", "--agent", "hermes", "--plugin", "no", "--scope", "project",
                                "--project-dir", str(other))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.bin.iterdir()), [], "a project install must not write the user's bin directory")

    def test_installed_command_runs_from_another_directory(self) -> None:
        bin_dir = self.tmp / "my bin"
        result = self.installer("install", "--bin-only", "--bin-dir", str(bin_dir))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        work = self.tmp / "some project"
        work.mkdir()
        code = ("import os, sys; open('out.txt', 'w').write('|'.join(sys.argv[1:]) + '|' + os.environ['CARGO_BUILD_JOBS'])"
                "; sys.exit(5)")
        command = [sys.executable, "-c", code, "a b", "c(d)", "e=f"]
        path = str(bin_dir) + os.pathsep + self.env.get("PATH", "")
        found = shutil.which(COMMAND, path=str(bin_dir))
        self.assertIsNotNone(found)
        if WINDOWS:
            self.assertTrue(found.lower().endswith(".cmd"), found)
            runs = [[found] + command, ["cmd", "/d", "/c", COMMAND] + command]
        else:
            runs = [[COMMAND] + command]
        for argv in runs:
            (work / "out.txt").unlink(missing_ok=True)
            result = subprocess.run(argv, cwd=work, env={**self.env, "PATH": path}, capture_output=True, text=True,
                                    timeout=60)
            self.assertEqual(result.returncode, 5, f"{argv[:4]}: {result.stdout}{result.stderr}")
            self.assertEqual((work / "out.txt").read_text(), "a b|c(d)|e=f|6")
        status = subprocess.run((runs[0][:1]) + ["--status"], cwd=work, env={**self.env, "PATH": path},
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("2 slots", status.stdout)

    @unittest.skipUnless(shutil.which("make") and not WINDOWS, "make is not installed")
    def test_make_passes_bin_dir_only_when_given(self) -> None:
        given = subprocess.run(["make", "-n", "-C", str(ROOT), "install", "BIN_DIR=/x/y"], capture_output=True,
                               text=True, env=self.env)
        self.assertIn('--bin-dir "/x/y"', given.stdout)
        default = subprocess.run(["make", "-n", "-C", str(ROOT), "install"], capture_output=True, text=True,
                                 env=self.env)
        self.assertNotIn("--bin-dir", default.stdout)


if __name__ == "__main__":
    unittest.main()
