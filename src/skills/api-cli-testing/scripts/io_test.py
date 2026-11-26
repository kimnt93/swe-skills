#!/usr/bin/env python3
"""Test an HTTP API or a command-line tool as its caller does: real inputs in, observed outputs recorded.

    io_test.py <plan.json> --out <empty dir outside any repository> [--approve <function>/<step> ...]
    io_test.py --self-test

Each step records the input, the expected result, the observed output (status and body, or exit code, stdout and
stderr) and the time it took. A wrong answer, no answer and a slow answer all fail. The plan: references/plan.md. The
safety rules are the ones of web testing, enforced by its testkit.py. No shell, and redirects are not followed.
Exit 0 = every function passed, 1 = something failed or did not run, 2 = usage or refused. Standard library only.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin


def sibling(skill: str, script: str):
    """The module of a sibling skill's script, in the plugin layout and in a prefixed copy install."""
    own = Path(__file__).resolve().parents[1]
    path = own.parent / own.name.replace("api-cli-testing", skill) / "scripts" / f"{script}.py"
    spec = importlib.util.spec_from_file_location(script, path)
    if spec is None or not path.is_file():
        raise SystemExit(f"{path} is missing: install the {skill} skill beside this one")
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


K = sibling("web-testing", "testkit")

STEP_KEYS = {
    "http": ("kind", "method", "path", "headers", "json", "body", "expect", "expected", "effect", "max_ms",
             "timeout_ms"),
    "cli": ("kind", "argv", "stdin", "env", "cwd", "expect", "expected", "effect", "max_ms", "timeout_ms"),
}
EXPECT_KEYS = {"http": ("status", "contains", "json"),
               "cli": ("exit", "stdout_contains", "stderr_contains", "stdout_json")}
SENSITIVE_HEADER_RE = re.compile(r"authorization|cookie|token|secret|api[-_]?key|password", re.I)
SECRET_VAR_RE = re.compile(r"\$\{secret:([A-Za-z_][A-Za-z0-9_]*)\}")
DEFAULT_BUDGET_MS, DEFAULT_TIMEOUT_MS, MAX_BYTES = 2000, 10000, 65536
SPARE_BYTES = 8192  # read past the limit, redact, then cut: a secret on the boundary is still whole when redacted


# ---------------------------------------------------------------------------------------------------- the plan

def walk(value, key: str = ""):
    """(key, text) of every string in a value."""
    if isinstance(value, dict):
        for name, item in value.items():
            yield from walk(item, str(name))
    elif isinstance(value, list):
        for item in value:
            yield from walk(item, key)
    elif isinstance(value, str):
        yield key, value


def check_io_plan(plan: dict) -> None:
    K.check_plan(plan, ("allow_programs",))
    for function in plan["functions"]:
        for number, step in enumerate(function["steps"], 1):
            where = f"{function['id']}/{number}"
            kind = step.get("kind")
            if kind not in STEP_KEYS:
                raise K.Refused(f"{where}: kind is http or cli")
            K.only_keys(where, step, STEP_KEYS[kind])
            expect = step.get("expect", {})
            K.only_keys(f"{where} expect", expect, EXPECT_KEYS[kind])
            first = "status" if kind == "http" else "exit"
            if not isinstance(expect.get(first), int):
                raise K.Refused(f"{where}: expect.{first} is required: write the expected result before you run")
            if any(value in ("", {}, []) for value in expect.values()):
                raise K.Refused(f"{where}: an empty expectation is always true")
            if kind == "http":
                if not K.host_of(plan.get("target", "")):
                    raise K.Refused("an http step needs the plan's target URL")
                if not isinstance(step.get("path"), str) or not str(step.get("method", "")).isalpha():
                    raise K.Refused(f"{where}: an http step needs a method and a path")
                if SECRET_VAR_RE.search(step["path"]):
                    raise K.Refused(f"{where}: no secret in a URL: servers log them; send it in a header or the body")
                for part in ("headers", "json"):
                    for key, text in walk(step.get(part, {})):
                        if SENSITIVE_HEADER_RE.search(key) and not SECRET_VAR_RE.search(text):
                            raise K.Refused(f"{where}: '{key}' holds a credential: write ${{secret:VARIABLE}}, which is"
                                            " read from the environment")
            else:
                argv = step.get("argv")
                if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
                    raise K.Refused(f"{where}: argv is a list of strings; there is no shell")
                if argv[0] not in plan.get("allow_programs", []):
                    raise K.Refused(f"{where}: '{argv[0]}' is not in allow_programs: test only what the request allows")
                if any(SECRET_VAR_RE.search(a) for a in argv):
                    raise K.Refused(f"{where}: no secret in argv (every user of the machine can list it); use env or stdin")
                for key, text in walk(step.get("env", {})):
                    if SENSITIVE_HEADER_RE.search(key) and not SECRET_VAR_RE.search(text):
                        raise K.Refused(f"{where}: env '{key}' holds a credential: write ${{secret:VARIABLE}}")


def fill_secrets(value, secrets: K.Secrets):
    if isinstance(value, dict):
        return {k: fill_secrets(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [fill_secrets(v, secrets) for v in value]
    if isinstance(value, str):
        return SECRET_VAR_RE.sub(lambda m: secrets.get(m.group(1)), value)
    return value


def describe_input(step: dict) -> str:
    """As the plan writes it: secrets stay ${secret:NAME}."""
    if step["kind"] == "http":
        text = f"{step['method'].upper()} {step['path']}"
        for part in ("headers", "json", "body"):
            if part in step:
                text += f", {part} {json.dumps(step[part], ensure_ascii=False)}"
        return text
    text = "run " + json.dumps(step["argv"], ensure_ascii=False)
    for part in ("env", "stdin"):
        if part in step:
            text += f", {part} {json.dumps(step[part], ensure_ascii=False)}"
    return text


def describe_expected(step: dict) -> str:
    words = ", ".join(f"{k} {json.dumps(v, ensure_ascii=False)}" for k, v in step["expect"].items())
    text = f"{words}, within {step.get('max_ms', DEFAULT_BUDGET_MS)} ms"
    return f"{step['expected']} ({text})" if step.get("expected") else text


# ---------------------------------------------------------------------------------------------------- running

def contains(actual, wanted, at: str = "$") -> str:
    """'' when every wanted key and value is in actual, else what differs. Lists must match in full."""
    if isinstance(wanted, dict) and isinstance(actual, dict):
        for key, value in wanted.items():
            if key not in actual:
                return f"{at}.{key} is missing"
            problem = contains(actual[key], value, f"{at}.{key}")
            if problem:
                return problem
        return ""
    if isinstance(wanted, list) and isinstance(actual, list) and len(wanted) == len(actual):
        return next((p for i, (a, w) in enumerate(zip(actual, wanted)) if (p := contains(a, w, f"{at}[{i}]"))), "")
    same = actual == wanted and isinstance(actual, bool) == isinstance(wanted, bool)
    return "" if same else f"{at} is {json.dumps(actual)}, wanted {json.dumps(wanted)}"


def json_problem(text: str, wanted) -> str:
    try:
        actual = json.loads(text)
    except ValueError:
        return "the output is not JSON"
    return contains(actual, wanted)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a redirect is an observed answer; following it could leave the allowed hosts


def call_http(plan: dict, step: dict, filled: dict, timeout: float) -> tuple:
    """(observed text, reasons)."""
    url = urljoin(plan["target"], filled["path"])
    headers = dict(filled.get("headers", {}))
    data = None
    if "json" in filled:
        data = json.dumps(filled["json"]).encode()
        headers.setdefault("Content-Type", "application/json")
    elif "body" in filled:
        data = filled["body"].encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=step["method"].upper())
    opener = urllib.request.build_opener(NoRedirect)
    try:
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status = response.status if hasattr(response, "status") else response.code
            body = response.read(MAX_BYTES + SPARE_BYTES).decode(errors="replace")
            extra = "".join(f"\n{name}: {response.headers[name]}" for name in ("Content-Type", "Location")
                            if response.headers.get(name))
    except (TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        if isinstance(reason, TimeoutError) or "timed out" in str(reason):
            return "(no answer)", [f"missing response: no answer in {round(timeout * 1000)} ms"]
        return f"(no answer: {reason})", [f"request failed: {reason}"]
    expect, reasons = step["expect"], []
    if status != expect["status"]:
        reasons.append(f"wrong status: {status}, wanted {expect['status']}")
    if "contains" in expect and expect["contains"] not in body:
        reasons.append(f"the body does not contain {json.dumps(expect['contains'])}")
    if "json" in expect and (problem := json_problem(body, expect["json"])):
        reasons.append(f"wrong body: {problem}")
    return f"status {status}{extra}\n\n{body}", reasons


def call_cli(base: Path, step: dict, filled: dict, timeout: float) -> tuple:
    env = {**os.environ, **filled.get("env", {})}
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            process = subprocess.Popen(filled["argv"], cwd=base / step.get("cwd", "."), env=env, stdout=out,
                                       stderr=err, stdin=subprocess.PIPE, start_new_session=True)
        except OSError as error:
            return f"(did not start: {error})", [f"the command did not start: {error}"]
        reasons = []
        try:
            process.communicate(filled.get("stdin", "").encode(), timeout=timeout)
        except subprocess.TimeoutExpired:
            reasons.append(f"missing response: still running after {round(timeout * 1000)} ms, so it was stopped")
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)  # nothing it started stays behind
            except (ProcessLookupError, PermissionError):
                pass
            process.wait()
        out.seek(0)
        err.seek(0)
        stdout, stderr = (f.read(MAX_BYTES + SPARE_BYTES).decode(errors="replace") for f in (out, err))
    observed = f"exit {process.returncode}\n--- stdout\n{stdout}\n--- stderr\n{stderr}"
    if reasons:
        return observed, reasons
    expect = step["expect"]
    if process.returncode != expect["exit"]:
        last = stderr.strip().splitlines()[-1] if stderr.strip() else ""
        reasons.append(f"wrong exit code: {process.returncode}, wanted {expect['exit']}" + (f" ({last})" if last else ""))
    for key, text in (("stdout_contains", stdout), ("stderr_contains", stderr)):
        if key in expect and expect[key] not in text:
            reasons.append(f"{key.split('_')[0]} does not contain {json.dumps(expect[key])}")
    if "stdout_json" in expect and (problem := json_problem(stdout, expect["stdout_json"])):
        reasons.append(f"wrong output: {problem}")
    return observed, reasons


def run_step(plan: dict, base: Path, folder: Path, function: str, number: int, step: dict, approved: set,
             secrets: K.Secrets) -> dict:
    ref, effect = f"{function}/{number}", step.get("effect", "read")
    label = step["path"] if step["kind"] == "http" else " ".join(step["argv"][1:])
    refusal = K.production_gate(plan["environment"], ref, effect, approved, label)
    if not refusal and step["kind"] == "cli" and plan["environment"] == "production" and ref not in approved:
        refusal = (f"production: step {ref} runs a command, and nothing here can hold back what a command does. It runs"
                   f" only with the owner's explicit approval (--approve {ref})")
    if not refusal and step["kind"] == "http":
        if K.host_of(urljoin(plan["target"], step["path"])) not in K.allowed_hosts(plan):
            refusal = f"{ref}: {step['path']} is outside the allowed hosts"
        elif not K.may_send(plan["environment"], step["method"], effect, ref in approved):
            refusal = (f"production: step {ref} sends {step['method'].upper()}, which can change data. Declare its effect;"
                       f" it runs only with the owner's explicit approval (--approve {ref})")
    if refusal:
        raise K.Refused(refusal)
    filled = fill_secrets(step, secrets)
    budget = step.get("max_ms", DEFAULT_BUDGET_MS)
    timeout = step.get("timeout_ms", max(DEFAULT_TIMEOUT_MS, budget * 2)) / 1000
    started = time.monotonic()
    if step["kind"] == "http":
        observed, reasons = call_http(plan, step, filled, timeout)
    else:
        observed, reasons = call_cli(base, step, filled, timeout)
    took = round((time.monotonic() - started) * 1000)
    answered = not any(r.startswith(("missing response", "request failed", "the command did not start")) for r in reasons)
    if answered and took > budget:
        reasons.append(f"slow: answered in {took} ms, the budget is {budget} ms")
    name = f"{function}/{number:02d}-{step['kind']}.json"
    result = {"n": number, "input": describe_input(step), "expected": describe_expected(step),
              "observed": observed, "verdict": K.FAIL if reasons else K.PASS, "reasons": reasons,
              "budget_ms": budget, "response_ms": took, "started": K.now(), "evidence": [name]}
    # redact first, shorten after: a cut could split a secret into parts that nothing recognises
    result = secrets.redact(result)
    result["observed"] = K.clip(result["observed"], MAX_BYTES)
    result["reasons"] = [K.clip(r, 300) for r in result["reasons"]]
    (folder / name).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {**result, "observed": K.clip(result["observed"])}


def run(plan_path: str, out: str, approve: list) -> int:
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    check_io_plan(plan)
    approved = K.check_approvals(plan, approve)
    secrets = K.Secrets()
    for function in plan["functions"]:  # every credential is there, or nothing is sent
        fill_secrets(function["steps"], secrets)
    folder = K.evidence_dir(out)
    results = {"kind": "api/cli", "target": plan.get("target") or ", ".join(plan.get("allow_programs", [])),
               "environment": plan["environment"], "started": K.now(), "approved": sorted(approved), "functions": []}
    base = Path(plan_path).resolve().parent
    for function in plan["functions"]:
        (folder / function["id"]).mkdir()
        done = []
        for number, step in enumerate(function["steps"], 1):
            why = f"step {done[-1]['n']} did not pass" if done and done[-1]["verdict"] != K.PASS else ""
            if not why:
                try:
                    done.append(run_step(plan, base, folder, function["id"], number, step, approved, secrets))
                    continue
                except K.Refused as refusal:
                    why = str(refusal)
            done.append(K.skipped_step(number, describe_input(step), describe_expected(step), why))
        results["functions"].append(K.function_result(function, done))
    code = K.write_results(folder, results, secrets)
    K.print_summary(folder, folder / "results.json")
    return code


# ---------------------------------------------------------------------------------------------------- self-test

class Fake(BaseHTTPRequestHandler):
    hits: list = []

    def log_message(self, *args):
        pass

    def reply(self, status, body, headers=()):
        data = body.encode()
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        Fake.hits.append(f"GET {self.path}")
        if self.path == "/slow":
            time.sleep(0.4)
        if self.path == "/hang":
            time.sleep(1.5)
        if self.path == "/moved":
            return self.reply(302, "", [("Location", "/ok")])
        if self.path == "/broken":
            return self.reply(500, "boom")
        echo = self.headers.get("Authorization", "")
        return self.reply(200, json.dumps({"ok": True, "total": "29.97", "echo": echo}))

    def do_POST(self):
        Fake.hits.append(f"{self.command} {self.path}")
        self.reply(200, "{}")

    do_DELETE = do_POST


def self_test() -> int:
    shipped = (Path(__file__).resolve().parents[1] / "assets/example-plan.json").read_text()
    # In the source tree the host is still the build's placeholder.
    check_io_plan(json.loads(re.sub(r"@[A-Z]+@", "example.test", shipped)))
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    server.handle_error = lambda *args: None  # the client that gave up on /hang closes the connection
    threading.Thread(target=server.serve_forever, daemon=True).start()
    python = sys.executable

    def get(path, **extra):
        return {"kind": "http", "method": "GET", "path": path, "expect": {"status": 200}, **extra}

    def cli(code, **extra):
        return {"kind": "cli", "argv": [python, "-c", code], "expect": {"exit": 0}, **extra}

    def plan(steps: dict, environment="local"):
        return {"environment": environment, "target": f"http://127.0.0.1:{server.server_address[1]}/",
                "allow_programs": [python],
                "functions": [{"id": k, "name": k, "steps": [v]} for k, v in steps.items()]}

    def execute(value, tmp, name, approve=()):
        path = Path(tmp) / f"{name}.json"
        path.write_text(json.dumps(value))
        with contextlib.redirect_stdout(io.StringIO()):
            code = run(str(path), str(Path(tmp) / name), list(approve))
        found = json.loads((Path(tmp) / name / "results.json").read_text())
        return code, {f["id"]: f for f in found["functions"]}

    os.environ["IO_SELF_TEST_TOKEN"] = "tok-5f2a9c11d7"
    with tempfile.TemporaryDirectory() as tmp:
        bearer = {"Authorization": "Bearer ${secret:IO_SELF_TEST_TOKEN}"}
        code, got = execute(plan({
            "works": get("/ok", headers=bearer, expect={"status": 200, "json": {"total": "29.97"}}),
            "broken": get("/broken"),
            "wrong": get("/ok", expect={"status": 200, "json": {"total": "30.00"}}),
            "slow": get("/slow", max_ms=100, timeout_ms=5000),
            "hang": get("/hang", max_ms=100, timeout_ms=300),
            "moved": get("/moved", expect={"status": 302}),
            "tool": cli("print(input()[::-1])", stdin="abc\n", expect={"exit": 0, "stdout_contains": "cba"}),
            "tool-broken": cli("raise SystemExit('no such order')"),
            "tool-slow": cli("import time; time.sleep(0.4)", max_ms=100),
            "tool-hang": cli("import time, subprocess; subprocess.run(['sleep', '30'])", timeout_ms=2000, max_ms=100),
            "tool-secret": cli("import os; print(os.environ['API_TOKEN'])",
                               env={"API_TOKEN": "${secret:IO_SELF_TEST_TOKEN}"}),
        }), tmp, "local")
        verdicts = {k: v["verdict"] for k, v in got.items()}
        passed = {"works", "moved", "tool", "tool-secret"}
        assert code == 1 and verdicts == {k: K.PASS if k in passed else K.FAIL for k in verdicts}, verdicts
        for name, words in (("broken", "wrong status: 500"), ("wrong", "$.total is"), ("slow", "slow:"),
                            ("hang", "missing response"), ("tool-broken", "no such order"), ("tool-slow", "slow:"),
                            ("tool-hang", "missing response")):
            assert words in got[name]["reason"], (name, got[name]["reason"])
        assert Fake.hits.count("GET /ok") == 2, "a redirect is not followed"
        for path in Path(tmp, "local").rglob("*"):
            assert path.is_dir() or "tok-5f2a9c11d7" not in path.read_text(), path
        assert "<secret:IO_SELF_TEST_TOKEN>" in got["works"]["steps"][0]["observed"]
        pad = "x" * 275  # puts the secret across the point where a reason is shortened
        code, got = execute(plan({
            "split": cli(f"import os, sys; sys.exit('{pad[:240]}' + os.environ['API_TOKEN'])",
                         env={"API_TOKEN": "${secret:IO_SELF_TEST_TOKEN}"}),
            "echo": get("/ok", headers=bearer, expect={"status": 200, "json": {"echo": pad}})}), tmp, "split")
        for path in Path(tmp, "split").rglob("*"):
            assert path.is_dir() or "tok-5f2" not in path.read_text(), path

        # production: nothing that can change data, and nothing that says it deletes, leaves without a named approval
        Fake.hits.clear()
        change = {"kind": "http", "method": "POST", "path": "/api/items", "expect": {"status": 200}}
        marker = Path(tmp) / "ran"
        risky = {"kind": "cli", "argv": [python, "-c", f"open({str(marker)!r}, 'w')", "delete"], "expect": {"exit": 0}}
        production = plan({"post": change, "declared": {**change, "effect": "delete", "method": "DELETE"},
                           "named": get("/api/orders/delete"), "tool": risky, "look": get("/ok")}, "production")
        code, got = execute(production, tmp, "prod")
        assert code == 1 and Fake.hits == ["GET /ok"] and not marker.exists(), Fake.hits
        assert [v["verdict"] for v in got.values()] == [K.NOT_RUN] * 4 + [K.PASS]
        quiet = {"kind": "cli", "argv": [python, "-c", f"open({str(marker)!r}, 'w')"], "expect": {"exit": 0}}
        code, got = execute(plan({"quiet": quiet}, "production"), tmp, "quiet")
        assert got["quiet"]["verdict"] == K.NOT_RUN and not marker.exists(), "no command runs unapproved on production"
        code, got = execute(plan({"quiet": quiet}, "production"), tmp, "quiet-approved", ["quiet/1"])
        assert got["quiet"]["verdict"] == K.PASS and marker.exists()
        marker.unlink()
        Fake.hits.clear()
        code, got = execute(production, tmp, "approved", ["declared/1", "post/1"])
        assert Fake.hits == ["DELETE /api/items", "GET /ok"], ("approval opens only a step that declares its effect", Fake.hits)
        assert got["post"]["verdict"] == K.NOT_RUN and got["declared"]["verdict"] == K.PASS

        for words, bad in (
            ("holds a credential", get("/ok", headers={"Authorization": "Bearer abcdef123456"})),
            ("holds a credential", {**change, "json": {"user": {"password": "hunter22"}}}),
            ("no secret in a URL", get("/ok?t=${secret:IO_SELF_TEST_TOKEN}")),
            ("no secret in argv", {"kind": "cli", "argv": [python, "${secret:IO_SELF_TEST_TOKEN}"], "expect": {"exit": 0}}),
            ("not in allow_programs", {"kind": "cli", "argv": ["rm", "-rf", "x"], "expect": {"exit": 0}}),
            ("expect.status is required", {"kind": "http", "method": "GET", "path": "/ok"}),
            ("unknown key", get("/ok", expects={})),
        ):
            assert words in K.refused(lambda: check_io_plan(plan({"x": bad}))), words
        Fake.hits.clear()
        code, got = execute(plan({"away": get("https://elsewhere.invalid/x")}), tmp, "away")
        assert got["away"]["verdict"] == K.NOT_RUN and "outside the allowed hosts" in got["away"]["reason"]
        assert "no such step" in K.refused(lambda: K.check_approvals(production, ["post/9"]))
    server.shutdown()
    print("self-test passed: wrong, slow and missing answers fail; production, hosts and secrets are held")
    return 0


def main(argv: list) -> int:
    if argv[:1] == ["--self-test"]:
        return self_test()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan")
    parser.add_argument("--out", required=True, help="an empty directory outside any repository")
    parser.add_argument("--approve", action="append", default=[], metavar="FUNCTION/STEP",
                        help="production only: a step the owner approved by name")
    args = parser.parse_args(argv)
    try:
        return run(args.plan, args.out, args.approve)
    except (K.Refused, OSError, ValueError) as why:
        print(f"REFUSED {why}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
