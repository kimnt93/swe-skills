#!/usr/bin/env python3
"""Validate JSON log lines against the unified service log format.

    ./my-service 2>&1 | python3 scripts/logcheck.py --service feed-ws --env local
    python3 scripts/logcheck.py --require-trace < captured.log

Reads lines from stdin (or files), ignores blank lines, and exits 0 when every line
conforms, 1 on violations, 2 when no JSON line was found. Standard library only.
The rules are the ones in references/log-format.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

LEVELS = {"trace", "debug", "info", "warn", "error", "fatal"}
CORE = ("level", "development_environment", "service_name", "node_name", "logger", "time", "caller", "message")
RESERVED = set(CORE) | {"trace_id", "span_id"}
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{9}Z$")
CALLER = re.compile(r"^[^\s:/][^\s:]*:[1-9]\d*$")
HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX16 = re.compile(r"^[0-9a-f]{16}$")
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
SECRET_VALUE = re.compile(r"(://[^/\s:@]+:[^@\s]+@|\bBearer\s+[A-Za-z0-9._~+/-]{8,}|\bpassword\s*[=:]\s*\S+)", re.I)
SECRET_KEY = re.compile(r"(password|passwd|secret|token|api_?key|authorization|dsn)", re.I)


def duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            seen.setdefault("__duplicates__", []).append(key)
        seen[key] = value
    return seen


def check_line(text: str, args: argparse.Namespace) -> tuple[list[str], list[str], dict | None]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        line = json.loads(text, object_pairs_hook=duplicate_keys)
    except json.JSONDecodeError as error:
        return [f"not JSON: {error.msg}"], warnings, None
    if not isinstance(line, dict):
        return ["not a JSON object"], warnings, None
    for key in line.pop("__duplicates__", []):
        errors.append(f"duplicate key {key!r} (a custom field collides with a core field)")
    for key in CORE:
        if key not in line:
            errors.append(f"missing {key}")
        elif not isinstance(line[key], str) or not line[key]:
            errors.append(f"{key} must be a non-empty string, got {line[key]!r}")
    if line.get("level") and line["level"] not in LEVELS:
        errors.append(f"level {line['level']!r} is not one of {sorted(LEVELS)} (warning->warn, critical->fatal)")
    if isinstance(line.get("time"), str) and not TIME.match(line["time"]):
        errors.append(f"time {line['time']!r} must be UTC RFC 3339 with exactly 9 fractional digits and Z, e.g. 2026-10-07T02:49:55.245633769Z")
    caller = line.get("caller")
    if isinstance(caller, str):
        if not CALLER.match(caller):
            errors.append(f"caller {caller!r} must be <root>/<relative path>:<line>, relative, with a line number")
        elif ".." in caller.split(":")[0].split("/") or "/home/" in caller or "/Users/" in caller:
            errors.append(f"caller {caller!r} leaks an absolute or parent path")
    for key, expected in (("service_name", args.service), ("development_environment", args.env), ("node_name", args.node)):
        if expected and line.get(key) != expected:
            errors.append(f"{key} is {line.get(key)!r}, expected {expected!r}")
    trace, span = line.get("trace_id"), line.get("span_id")
    if ("trace_id" in line) != ("span_id" in line):
        errors.append("trace_id and span_id must appear together")
    if "trace_id" in line:
        if not isinstance(trace, str) or not HEX32.match(trace) or set(trace) == {"0"}:
            errors.append(f"trace_id {trace!r} must be 32 lowercase hex characters, not all zero (omit it when there is no span)")
        if not isinstance(span, str) or not HEX16.match(span) or set(span) == {"0"}:
            errors.append(f"span_id {span!r} must be 16 lowercase hex characters, not all zero (omit it when there is no span)")
    if "exception" in line:
        warnings.append("field 'exception' is the legacy name: use error (message), error_type, stack")
    if line.get("level") in {"error", "fatal"} and "error" not in line:
        warnings.append("error/fatal line without an error field")
    for key, value in line.items():
        if key not in RESERVED and not SNAKE.match(key):
            warnings.append(f"field {key!r} is not snake_case")
        if isinstance(value, (dict, list)) and key not in RESERVED:
            warnings.append(f"field {key!r} is nested: keep custom fields flat scalars")
        if key not in RESERVED and SECRET_KEY.search(key) and value not in ("", None):
            warnings.append(f"field {key!r} looks like a credential: never log secrets")
        if isinstance(value, str) and SECRET_VALUE.search(value):
            warnings.append(f"field {key!r} value looks like a credential or DSN")
    return errors, warnings, line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="log files (default: stdin)")
    parser.add_argument("--service", help="expected service_name")
    parser.add_argument("--env", help="expected development_environment")
    parser.add_argument("--node", help="expected node_name")
    parser.add_argument("--require-trace", action="store_true", help="fail unless at least one line has trace_id and span_id")
    parser.add_argument("--max-problems", type=int, default=20, help="stop printing after this many problem lines")
    args = parser.parse_args()

    sources = [open(f) for f in args.files] if args.files else [sys.stdin]
    total = bad = traced = printed = 0
    loggers: set[str] = set()
    for source in sources:
        for number, raw in enumerate(source, 1):
            text = raw.strip()
            if not text:
                continue
            if not text.startswith("{"):
                continue  # plain text noise (build output, panics): not a log line
            total += 1
            errors, warnings, line = check_line(text, args)
            if line:
                loggers.add(str(line.get("logger", "")))
                traced += "trace_id" in line
            if errors:
                bad += 1
            if (errors or warnings) and printed < args.max_problems:
                printed += 1
                print(f"line {number}: {text[:160]}")
                for message in errors:
                    print(f"  FAIL  {message}")
                for message in warnings:
                    print(f"  warn  {message}")
    if not total:
        print("FAIL no JSON log lines found")
        return 2
    print(f"checked {total} line(s): {total - bad} conform, {bad} violate; loggers: {sorted(loggers)}; with trace ids: {traced}")
    if args.require_trace and not traced:
        print("FAIL --require-trace: no line carries trace_id/span_id")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
