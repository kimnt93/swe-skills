#!/usr/bin/env python3
"""Audit a service repository for the platform's error-tracking contract (static, no network).

    audit_errors.py [PROJECT_DIR] [--json]

Looks at Go, Python, Rust and TypeScript/JavaScript source, Compose files and env files:

  ERR-1  an SDK initialisation exists (sentry.NewClient/Init, sentry_sdk.init, sentry::init, Sentry.init)
  ERR-2  no DSN is hard-coded in source; a DSN in a committed deploy env file is a WARN (prefer a secret)
  ERR-3  privacy: no send_default_pii, local variables, breadcrumbs, tracing or request data switched on
  ERR-4  environment and release are set at initialisation
  ERR-5  a before_send / BeforeSend scrubber exists
  ERR-6  SENTRY_DSN is documented in an env example and passed by Compose (a *_FILE secret in Swarm)

FAIL means the contract is broken; WARN means look at it by hand. Exit 1 when any FAIL. Heuristic:
`sentry_receiver.py` checks what the running service really sends. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "target", ".venv", "venv", "vendor", "dist", "build", "__pycache__",
    ".ruff_cache", ".mypy_cache", ".next", "site-packages",
}
SOURCE = {".go", ".py", ".rs", ".ts", ".tsx", ".js", ".mjs", ".cjs"}
INIT = re.compile(r"sentry\.NewClient\(|sentry\.Init\(|sentry_sdk\.init\(|sentry::init\(|Sentry\.init\(")
DSN = re.compile(r"""https?://[0-9a-f]{16,}(?::[0-9a-f]+)?@[\w.-]+(?::\d+)?/\d+""")
RISKY = [
    (re.compile(r"send_default_pii\s*=\s*True|SendDefaultPII\s*:\s*true|sendDefaultPii\s*:\s*true|send_default_pii\s*:\s*true"),
     "send_default_pii is on: IP addresses, users and cookies leave the process"),
    (re.compile(r"include_local_variables\s*=\s*True|includeLocalVariables\s*:\s*true"),
     "local variables are attached: a frame's locals hold submitted data and secrets"),
    (re.compile(r"max_breadcrumbs\s*=\s*[1-9]|MaxBreadcrumbs\s*:\s*[1-9]|maxBreadcrumbs\s*:\s*[1-9]"),
     "breadcrumbs are on: they carry log text and request data"),
    (re.compile(r"traces_sample_rate\s*=\s*(?:0\.\d*[1-9]|[1-9])|TracesSampleRate\s*:\s*(?:0\.\d*[1-9]|[1-9])"
                r"|tracesSampleRate\s*:\s*(?:0\.\d*[1-9]|[1-9])|EnableTracing\s*:\s*true|traces_sample_rate\s*:\s*(?:0\.\d*[1-9]|[1-9])"),
     "Sentry tracing is on: OpenTelemetry owns traces"),
    (re.compile(r"default_integrations\s*=\s*True|DefaultIntegrations\s*:\s*true"), "default integrations collect request data"),
]
SCRUBBER = re.compile(r"before_send|BeforeSend|beforeSend")


class Finding:
    def __init__(self, level: str, rule: str, where: str, message: str) -> None:
        self.level, self.rule, self.where, self.message = level, rule, where, message

    def as_dict(self) -> dict:
        return {"level": self.level, "rule": self.rule, "where": self.where, "message": self.message}


def files(root: Path):
    """Every file under root, without descending into build and dependency directories."""
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            yield Path(current) / name


def relevant(path: Path) -> bool:
    """Source, Compose and env files under 2 MB: anything else is never opened."""
    wanted = path.suffix in SOURCE or path.suffix in {".yaml", ".yml", ".env"} or path.name.startswith(".env")
    try:
        return wanted and path.stat().st_size < 2_000_000
    except OSError:
        return False


def read(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def is_test(path: Path) -> bool:
    name = path.name
    return (
        name.startswith("test_") or name.endswith(("_test.go", "_test.py", "tests.rs", ".test.ts", ".spec.ts", ".test.js"))
        or bool({"tests", "test", "__tests__", "e2e"} & set(path.parts))
    )


def comment_free(line: str) -> str:
    return re.sub(r"\s(//|#)\s.*$", "", line)


def run(root: Path) -> list[Finding]:
    out: list[Finding] = []
    init_files: list[Path] = []
    scrubber = False
    env_example = compose = False
    for path in files(root):
        if not relevant(path):
            continue
        rel = path.relative_to(root)
        lines = read(path)
        text = "\n".join(lines)
        if path.suffix in SOURCE and not is_test(path):
            if INIT.search(text):
                init_files.append(rel)
                scrubber = scrubber or bool(SCRUBBER.search(text))
                if not re.search(r"environment|Environment", text) or not re.search(r"release|Release", text):
                    out.append(Finding("WARN", "ERR-4", str(rel), "initialisation does not set both environment and release"))
            for number, raw in enumerate(lines, 1):
                line = comment_free(raw)
                if DSN.search(line):
                    out.append(Finding("FAIL", "ERR-2", f"{rel}:{number}", "a DSN is hard-coded in source: read SENTRY_DSN"))
                for pattern, message in RISKY:
                    if pattern.search(line):
                        out.append(Finding("FAIL", "ERR-3", f"{rel}:{number}", message))
            if SCRUBBER.search(text) and INIT.search(text) is None:
                scrubber = True
        elif path.suffix in {".yaml", ".yml"} and "compose" in path.name:
            if re.search(r"\bSENTRY_DSN(_FILE)?\b", text):
                compose = True
        elif path.name.startswith(".env") or path.suffix == ".env":
            if re.search(r"\bSENTRY_DSN(_FILE)?\b", text):
                if path.name.endswith(".example"):
                    env_example = True
                for number, raw in enumerate(lines, 1):
                    if DSN.search(raw) and not raw.lstrip().startswith("#"):
                        out.append(Finding("WARN", "ERR-2", f"{rel}:{number}",
                                           "a DSN is committed in an env file: prefer a mounted secret (SENTRY_DSN_FILE)"))
    if not init_files:
        out.append(Finding("FAIL", "ERR-1", str(root), "no Sentry/GlitchTip SDK initialisation found"))
    elif not scrubber:
        out.append(Finding("FAIL", "ERR-5", str(init_files[0]), "no before_send / BeforeSend scrubber: events may carry request and user data"))
    if init_files and not env_example:
        out.append(Finding("WARN", "ERR-6", str(root), "SENTRY_DSN is not documented in an .env example"))
    if init_files and not compose:
        out.append(Finding("WARN", "ERR-6", str(root), "no Compose file passes SENTRY_DSN or SENTRY_DSN_FILE"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    findings = run(root)
    fails = sum(1 for item in findings if item.level == "FAIL")
    warns = len(findings) - fails
    if args.json:
        print(json.dumps({"root": str(root), "fail": fails, "warn": warns, "findings": [i.as_dict() for i in findings]}, indent=2))
    else:
        for item in findings:
            print(f"{item.level:<5} {item.rule:<6} {item.where}: {item.message}")
        print(f"{fails} FAIL, {warns} WARN in {root}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
