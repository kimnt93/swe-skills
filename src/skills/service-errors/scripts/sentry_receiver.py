#!/usr/bin/env python3
"""A local stand-in for a Sentry or GlitchTip ingest, to verify what a service really sends.

    sentry_receiver.py serve [--port 9100] [--out events.jsonl]
        accepts /api/<project>/envelope/ and /api/<project>/store/, writes one JSON event per line
    sentry_receiver.py check events.jsonl --environment stg --service orders-api [--release R]
        checks the captured events against the service-errors contract; exit 1 on a violation

Run the service with SENTRY_DSN=http://test-key@127.0.0.1:9100/1, trigger one failure, stop the
service (it flushes at shutdown), then run `check`. Standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ALLOWED_TAGS = {"service_name", "component", "logger", "trace_id", "span_id"}
FORBIDDEN_KEYS = ("request", "user", "breadcrumbs", "contexts", "extra", "attachments")


def decode_body(body: bytes, encoding: str) -> bytes:
    if encoding == "gzip":
        return gzip.decompress(body)
    if encoding == "deflate":
        return zlib.decompress(body)
    return body


def events_in(payload: bytes) -> list[dict]:
    """Events of an envelope (header, then item header + payload lines) or of a store request."""
    text = payload.decode("utf-8", "replace")
    lines = text.split("\n")
    try:
        whole = json.loads(text)
        if isinstance(whole, dict) and ("message" in whole or "exception" in whole or "event_id" in whole):
            return [whole]
    except ValueError:
        pass
    events, index = [], 1  # line 0 is the envelope header
    while index < len(lines):
        try:
            item_header = json.loads(lines[index])
        except ValueError:
            index += 1
            continue
        body = lines[index + 1] if index + 1 < len(lines) else ""
        if item_header.get("type") == "event":
            try:
                events.append(json.loads(body))
            except ValueError:
                pass
        index += 2
    return events


def serve(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.write_text("")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            body = decode_body(self.rfile.read(length), self.headers.get("Content-Encoding", ""))
            found = events_in(body)
            with out.open("a", encoding="utf-8") as handle:
                for event in found:
                    handle.write(json.dumps(event) + "\n")
            print(f"{self.path}: {len(found)} event(s)", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"listening on 127.0.0.1:{args.port}, DSN http://test-key@127.0.0.1:{args.port}/1, events -> {out}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def check(args: argparse.Namespace) -> int:
    events = [json.loads(line) for line in Path(args.file).read_text().splitlines() if line.strip()]
    problems: list[str] = []
    if not events:
        problems.append("no event was received")
    for number, event in enumerate(events, 1):
        label = f"event {number} ({event.get('message') or (event.get('logentry') or {}).get('message') or 'exception'})"
        if event.get("environment") != args.environment:
            problems.append(f"{label}: environment is `{event.get('environment')}`, expected `{args.environment}`")
        release = event.get("release") or ""
        if not release or (args.release and release != args.release) or (not args.release and "@" not in release):
            problems.append(f"{label}: release `{release}` should be `<service_name>@<version>`")
        tags = event.get("tags") or {}
        if isinstance(tags, list):  # the envelope may send [[k, v], ...]
            tags = {k: v for k, v in tags}
        if tags.get("service_name") != args.service:
            problems.append(f"{label}: tag service_name is `{tags.get('service_name')}`, expected `{args.service}`")
        extra_tags = sorted(set(tags) - ALLOWED_TAGS)
        if extra_tags:
            problems.append(f"{label}: tags outside the allowlist: {extra_tags}")
        for key in FORBIDDEN_KEYS:
            if event.get(key):
                problems.append(f"{label}: carries `{key}`")
        for exception in (event.get("exception") or {}).get("values") or []:
            if exception.get("value") and not args.allow_exception_text:
                problems.append(f"{label}: exception text is sent (use --allow-exception-text if intended)")
            for frame in (exception.get("stacktrace") or {}).get("frames") or []:
                if frame.get("vars"):
                    problems.append(f"{label}: stack frame carries local variables")
                    break
        blob = json.dumps(event)
        for word in args.forbid:
            if word in blob:
                problems.append(f"{label}: contains forbidden text `{word}`")
    for problem in problems:
        print("FAIL", problem)
    print(f"{len(events)} event(s), {len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    serve_parser = commands.add_parser("serve", help="receive events")
    serve_parser.add_argument("--port", type=int, default=9100)
    serve_parser.add_argument("--out", default="events.jsonl")
    check_parser = commands.add_parser("check", help="check captured events")
    check_parser.add_argument("file")
    check_parser.add_argument("--environment", required=True)
    check_parser.add_argument("--service", required=True)
    check_parser.add_argument("--release", default="")
    check_parser.add_argument("--forbid", action="append", default=[], help="text that must not appear (repeatable)")
    check_parser.add_argument("--allow-exception-text", action="store_true")
    args = parser.parse_args()
    return serve(args) if args.command == "serve" else check(args)


if __name__ == "__main__":
    sys.exit(main())
