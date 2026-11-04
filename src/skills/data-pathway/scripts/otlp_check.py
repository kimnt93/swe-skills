#!/usr/bin/env python3
"""Local OTLP/HTTP metrics receiver that checks a service against the pipeline metric contract.

Run it, point the service at it, and read the verdict:

    python3 scripts/otlp_check.py --role transform --wait 30
    OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 <start the service>

Roles: transform (Kafka -> Kafka) and sink (Kafka -> store) are the Pathway ones; ingestion and
consumer remain for other services. Exit code 0 = pass, 1 = contract violation,
2 = nothing received. Standard library only; decodes OTLP protobuf and OTLP JSON.
See references/metric-contract.md (data-pathway) for the contract this file encodes.
"""

from __future__ import annotations

import argparse
import gzip
import json
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFIX = "stream_pipeline_"
STATUSES = {"received", "dropped", "published"}

# name -> instrument kind (counter, gauge, histogram)
KINDS = {
    "messages_total": "counter",
    "payload_bytes_total": "counter",
    "latency_ms": "histogram",
    "errors_total": "counter",
    "restarts_total": "counter",
    "reconnects_total": "counter",
    "running": "gauge",
    "connection_active": "gauge",
    "kafka_healthy": "gauge",
    "last_message_age_ms": "gauge",
    "consumer_lag": "gauge",
    "in_flight": "gauge",
    "start_timestamp_seconds": "gauge",
    "latest_event_timestamp_seconds": "gauge",
}
# Exported from the first collection, before any traffic.
ALWAYS = {"running", "restarts_total", "start_timestamp_seconds"}
# Appear only once there is activity (a counter series exists after its first add).
ACTIVITY = {"messages_total", "payload_bytes_total", "latency_ms", "last_message_age_ms", "latest_event_timestamp_seconds"}
ROLE_ALWAYS = {"ingestion": {"connection_active"}, "transform": set(), "sink": set(), "consumer": set()}
ROLE_ACTIVITY = {"ingestion": {"in_flight"}, "transform": set(), "sink": set(), "consumer": set()}
ROLE_FORBIDDEN = {  # emitted only by ingestion services
    "transform": {"connection_active", "reconnects_total", "in_flight"},
    "sink": {"connection_active", "reconnects_total", "in_flight"},
    "consumer": {"connection_active", "reconnects_total", "in_flight"},
}

# --------------------------------------------------------------------------- #
# Minimal protobuf reader (only the OTLP metrics fields the check needs)


def _varint(buf: bytes, pos: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def _fields(buf: bytes):
    """Yield (field number, wire type, value) for one message."""
    pos = 0
    while pos < len(buf):
        key, pos = _varint(buf, pos)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _varint(buf, pos)
        elif wire == 1:
            value, pos = buf[pos : pos + 8], pos + 8
        elif wire == 2:
            size, pos = _varint(buf, pos)
            value, pos = buf[pos : pos + size], pos + size
        elif wire == 5:
            value, pos = buf[pos : pos + 4], pos + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        yield number, wire, value


def _attributes(items: list[bytes]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        key, value = "", ""
        for number, _, raw in _fields(item):
            if number == 1:
                key = raw.decode()
            elif number == 2:
                for inner, wire, v in _fields(raw):
                    if inner == 1:
                        value = v.decode()
                    elif wire == 0:
                        value = str(v)
        out[key] = value
    return out


def parse_protobuf(body: bytes) -> list[dict]:
    """ExportMetricsServiceRequest -> [{resource, name, kind, unit, series}]."""
    metrics = []
    for number, _, resource_metrics in _fields(body):
        if number != 1:
            continue
        resource: dict[str, str] = {}
        scopes: list[bytes] = []
        for n, _, raw in _fields(resource_metrics):
            if n == 1:
                resource = _attributes([r for k, _, r in _fields(raw) if k == 1])
            elif n == 2:
                scopes.append(raw)
        for scope in scopes:
            for n, _, metric in _fields(scope):
                if n != 2:
                    continue
                name = unit = kind = ""
                points: list[bytes] = []
                for m, _, raw in _fields(metric):
                    if m == 1:
                        name = raw.decode()
                    elif m == 3:
                        unit = raw.decode()
                    elif m in (5, 7, 9, 10, 11):
                        kind = {5: "gauge", 7: "counter", 9: "histogram"}.get(m, "other")
                        points = [p for k, _, p in _fields(raw) if k == 1]
                attr_field = 9 if kind == "histogram" else 7
                series = [_attributes([a for k, _, a in _fields(p) if k == attr_field]) for p in points]
                metrics.append({"resource": resource, "name": name, "kind": kind, "unit": unit, "series": series})
    return metrics


def parse_json(body: bytes) -> list[dict]:
    def attrs(items):
        return {a["key"]: next(iter(a.get("value", {}).values()), "") for a in items or []}

    metrics = []
    for rm in json.loads(body).get("resourceMetrics", []):
        resource = attrs(rm.get("resource", {}).get("attributes"))
        for sm in rm.get("scopeMetrics", []):
            for m in sm.get("metrics", []):
                kind = next((k for k in ("gauge", "sum", "histogram") if k in m), "other")
                points = m.get(kind, {}).get("dataPoints", []) if kind != "other" else []
                metrics.append({
                    "resource": resource, "name": m["name"], "unit": m.get("unit", ""),
                    "kind": "counter" if kind == "sum" else kind,
                    "series": [attrs(p.get("attributes")) for p in points],
                })
    return metrics


# --------------------------------------------------------------------------- #
# Receiver


class Collected:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.metrics: dict[str, dict] = {}
        self.resource: dict[str, str] = {}
        self.exports = 0
        self.paths: set[str] = set()

    def add(self, path: str, items: list[dict]) -> None:
        with self.lock:
            self.exports += 1
            self.paths.add(path)
            for item in items:
                self.resource = item["resource"] or self.resource
                entry = self.metrics.setdefault(item["name"], {"kind": item["kind"], "unit": item["unit"], "series": []})
                for labels in item["series"]:
                    if labels not in entry["series"]:
                        entry["series"].append(labels)


def serve(port: int, collected: Collected, token: str | None) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _body(self) -> bytes:
            """Content-Length body, or chunked (the JavaScript exporter streams chunks)."""
            if "chunked" in self.headers.get("Transfer-Encoding", ""):
                chunks = []
                while True:
                    size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                    if size == 0:
                        self.rfile.readline()  # trailing CRLF after the last chunk
                        return b"".join(chunks)
                    chunks.append(self.rfile.read(size))
                    self.rfile.readline()
            return self.rfile.read(int(self.headers.get("Content-Length", 0)))

        def do_POST(self) -> None:  # noqa: N802
            body = self._body()
            if token and self.headers.get("Authorization") != f"Bearer {token}":
                self.send_response(401)
                self.end_headers()
                return
            if self.path != "/v1/metrics":  # what a collector gateway does
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 page not found")
                return
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            ctype = self.headers.get("Content-Type", "")
            items = parse_json(body) if "json" in ctype else parse_protobuf(body)
            collected.add(self.path, items)
            self.send_response(200)
            self.send_header("Content-Type", ctype or "application/x-protobuf")
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# --------------------------------------------------------------------------- #
# Contract check


def check(collected: Collected, role: str) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ok: list[str] = []
    resource = collected.resource
    for key in ("service.name", "service.namespace", "deployment.environment", "host.name"):
        if not resource.get(key):
            errors.append(f"resource attribute {key} is missing")
    if resource.get("service.name"):
        ok.append(f"service.name = {resource['service.name']} (this is the pipeline name)")
    seen = {}
    for name, entry in collected.metrics.items():
        if not name.startswith(PREFIX):
            errors.append(f"unexpected metric {name}: every pipeline metric starts with {PREFIX}")
            continue
        short = name[len(PREFIX) :]
        if short not in KINDS:
            errors.append(f"unknown metric {name}: not in the contract (references/metric-contract.md)")
            continue
        seen[short] = entry
        if entry["kind"] != KINDS[short]:
            errors.append(f"{name} is a {entry['kind']}, the contract says {KINDS[short]}")
        if entry["unit"]:
            errors.append(f"{name} has unit {entry['unit']!r}: set no unit, or Mimir renames the series")
        for labels in entry["series"]:
            if short == "messages_total":
                if set(labels) != {"status"} or labels.get("status") not in STATUSES:
                    errors.append(f"{name} labels {labels}: only status=received|dropped|published is allowed")
            elif labels:
                errors.append(f"{name} has labels {labels}: only messages_total carries a label (status)")
    required = ALWAYS | ROLE_ALWAYS[role]
    for short in sorted(required):
        (ok if short in seen else errors).append(
            f"{PREFIX}{short}" if short in seen else f"missing {PREFIX}{short} (exported from the first collection)"
        )
    for short in sorted((ACTIVITY | ROLE_ACTIVITY[role]) - set(seen)):
        warnings.append(f"{PREFIX}{short} not seen yet: it appears after the first message; send traffic and re-run")
    for short in sorted(ROLE_FORBIDDEN.get(role, set()) & set(seen)):
        errors.append(f"{PREFIX}{short} is ingestion-only but the role is {role}")
    if "messages_total" in seen:
        statuses = {labels.get("status") for labels in seen["messages_total"]["series"]}
        for status in ("received", "published"):
            if status not in statuses:
                warnings.append(f"messages_total has no status={status} series yet")
    return errors, warnings, ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--role", choices=sorted(ROLE_ALWAYS), required=True)
    parser.add_argument("--port", type=int, default=4318)
    parser.add_argument("--wait", type=float, default=30, help="seconds to collect before the verdict")
    parser.add_argument("--min-exports", type=int, default=2, help="stop early after this many exports")
    parser.add_argument("--token", help="require this bearer token (like the staging gateway)")
    args = parser.parse_args()

    collected = Collected()
    server = serve(args.port, collected, args.token)
    print(f"listening on http://127.0.0.1:{args.port}/v1/metrics (role={args.role}, waiting up to {args.wait:.0f}s)", flush=True)
    deadline = time.monotonic() + args.wait
    while time.monotonic() < deadline and collected.exports < args.min_exports:
        time.sleep(0.5)
    time.sleep(0.5)
    server.shutdown()

    if not collected.exports:
        print("FAIL nothing received: check OTEL_EXPORTER_OTLP_ENDPOINT, the /v1/metrics path, and the export interval")
        return 2
    errors, warnings, ok = check(collected, args.role)
    print(f"received {collected.exports} export(s), {len(collected.metrics)} metric(s)")
    for line in ok:
        print(f"  ok    {line}")
    for line in warnings:
        print(f"  warn  {line}")
    for line in errors:
        print(f"  FAIL  {line}")
    print("PASS" if not errors else f"FAIL ({len(errors)} violation(s))")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
