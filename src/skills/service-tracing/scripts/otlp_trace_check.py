#!/usr/bin/env python3
"""Local OTLP/HTTP trace receiver that rebuilds the service dependency graph and checks it.

Start it, point the services at it, drive one request through them, read the verdict:

    python3 scripts/otlp_trace_check.py --expect web>api --expect api>postgres --wait 60
    OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 <start the services>

    python3 scripts/otlp_trace_check.py --map docs/dependency-map.md --wait 90     # rows of the map are the expectations

What it derives (the same pairs a trace backend's service graph uses):
  * sync/async edge  CLIENT|PRODUCER span in service A  ->  its child SERVER|CONSUMER span in service B
  * peer edge        CLIENT|PRODUCER span with no remote child but peer attributes (peer.service,
                     server.address, db.system, messaging.system, ...) -> a virtual node (database, broker, API)
  * problems         unresolved client spans (no remote child, no peer attributes: the edge is silently lost),
                     self edges, unknown_service names, missing parents (propagation break), a trace that
                     contains internal spans while --mode dependency (the default) expects boundary spans only

Exit code 0 = every expectation met and no error, 1 = expectation/error failed, 2 = no spans received.
Standard library only; decodes OTLP protobuf and OTLP JSON (optionally gzip). See references/verification.md.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import threading
import time
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KINDS = {0: "UNSPECIFIED", 1: "INTERNAL", 2: "SERVER", 3: "CLIENT", 4: "PRODUCER", 5: "CONSUMER"}
JSON_KINDS = {"SPAN_KIND_" + v: k for k, v in KINDS.items()}
CALLERS = {"CLIENT", "PRODUCER"}
CALLEES = {"SERVER", "CONSUMER"}
PEER_KEYS = ("peer.service", "server.address", "net.peer.name", "url.domain", "db.system", "db.system.name",
             "messaging.system", "rpc.service", "http.host", "server.socket.address")

# --------------------------------------------------------------------------- #
# Minimal protobuf reader (only the OTLP trace fields the check needs)


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


def _any_value(raw: bytes) -> str:
    for number, wire, value in _fields(raw):
        if number == 1:
            return value.decode("utf-8", "replace")
        if number in (2, 3):
            return str(value)
        if number == 4:
            import struct

            return str(struct.unpack("<d", value)[0])
    return ""


def _attributes(items: list[bytes]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        key, value = "", ""
        for number, _, raw in _fields(item):
            if number == 1:
                key = raw.decode()
            elif number == 2:
                value = _any_value(raw)
        out[key] = value
    return out


def parse_protobuf(body: bytes) -> list[dict]:
    """ExportTraceServiceRequest -> [span dicts]."""
    spans: list[dict] = []
    for number, _, resource_spans in _fields(body):
        if number != 1:
            continue
        resource: dict[str, str] = {}
        scopes: list[bytes] = []
        for n, _, raw in _fields(resource_spans):
            if n == 1:
                resource = _attributes([r for k, _, r in _fields(raw) if k == 1])
            elif n == 2:
                scopes.append(raw)
        for scope in scopes:
            scope_name = ""
            for n, _, raw in _fields(scope):
                if n == 1:
                    scope_name = next((v.decode() for k, _, v in _fields(raw) if k == 1), "")
                elif n == 2:
                    span = {"resource": resource, "scope": scope_name, "kind": "UNSPECIFIED", "attrs": {},
                            "parent": "", "name": "", "links": 0, "status": 0, "events": 0}
                    attrs = []
                    for m, _, value in _fields(raw):
                        if m == 1:
                            span["trace"] = value.hex()
                        elif m == 2:
                            span["span"] = value.hex()
                        elif m == 4:
                            span["parent"] = value.hex()
                        elif m == 5:
                            span["name"] = value.decode("utf-8", "replace")
                        elif m == 6:
                            span["kind"] = KINDS.get(value, "UNSPECIFIED")
                        elif m == 9:
                            attrs.append(value)
                        elif m == 11:
                            span["events"] += 1
                        elif m == 13:
                            span["links"] += 1
                        elif m == 15:
                            span["status"] = next((v for k, _, v in _fields(value) if k == 3), 0)
                    span["attrs"] = _attributes(attrs)
                    spans.append(span)
    return spans


def _json_attrs(items: list[dict]) -> dict[str, str]:
    out = {}
    for item in items or []:
        value = item.get("value", {})
        out[item.get("key", "")] = str(next(iter(value.values()), "")) if value else ""
    return out


def parse_json(body: bytes) -> list[dict]:
    spans = []
    data = json.loads(body)
    for rs in data.get("resourceSpans", []):
        resource = _json_attrs(rs.get("resource", {}).get("attributes", []))
        for ss in rs.get("scopeSpans", []):
            for s in ss.get("spans", []):
                kind = s.get("kind", 0)
                kind = KINDS.get(kind, "UNSPECIFIED") if isinstance(kind, int) else (
                    KINDS.get(JSON_KINDS.get(kind, 0), "UNSPECIFIED"))
                spans.append({"resource": resource, "scope": ss.get("scope", {}).get("name", ""), "kind": kind,
                              "trace": s.get("traceId", ""), "span": s.get("spanId", ""),
                              "parent": s.get("parentSpanId", ""), "name": s.get("name", ""),
                              "attrs": _json_attrs(s.get("attributes", [])), "links": len(s.get("links", [])),
                              "events": len(s.get("events", [])), "status": s.get("status", {}).get("code", 0)})
    return spans


# --------------------------------------------------------------------------- #
# Receiver


class Store:
    def __init__(self) -> None:
        self.spans: list[dict] = []
        self.lock = threading.Lock()
        self.last = 0.0
        self.requests = 0
        self.unauthorized = 0

    def add(self, spans: list[dict]) -> None:
        with self.lock:
            self.spans.extend(spans)
            self.last = time.time()
            self.requests += 1

    def snapshot(self) -> list[dict]:
        with self.lock:
            return list(self.spans)


def make_handler(store: Store, token: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):  # quiet
            pass

        def read_body(self) -> bytes:
            """Content-Length or chunked transfer encoding (the Node exporter streams chunked)."""
            if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
                chunks = []
                while True:
                    size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                    if size == 0:
                        while self.rfile.readline().strip():  # trailers
                            pass
                        return b"".join(chunks)
                    chunks.append(self.rfile.read(size))
                    self.rfile.readline()
            return self.rfile.read(int(self.headers.get("Content-Length", 0)))

        def do_POST(self):  # noqa: N802
            if self.path.rstrip("/") not in ("/v1/traces", "/v1/traces/"):
                self.send_response(404)
                self.end_headers()
                return
            if token and self.headers.get("Authorization", "") != f"Bearer {token}":
                store.unauthorized += 1
                self.send_response(401)
                self.end_headers()
                return
            body = self.read_body()
            if self.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
            ctype = self.headers.get("Content-Type", "")
            try:
                spans = parse_json(body) if "json" in ctype else parse_protobuf(body)
            except Exception as exc:  # malformed payload
                print(f"! undecodable payload ({ctype}): {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return
            store.add(spans)
            self.send_response(200)
            self.send_header("Content-Type", ctype or "application/x-protobuf")
            self.send_header("Content-Length", "2" if "json" in ctype else "0")
            self.end_headers()
            if "json" in ctype:
                self.wfile.write(b"{}")

    return Handler


# --------------------------------------------------------------------------- #
# Analysis


def service_of(span: dict) -> str:
    return span["resource"].get("service.name", "") or "<missing service.name>"


def peer_name(span: dict) -> tuple[str, str]:
    """Virtual node name and its type for a client/producer span with no remote child."""
    a = span["attrs"]
    if a.get("peer.service"):
        name = a["peer.service"]
    elif a.get("db.system") or a.get("db.system.name"):
        name = a.get("server.address") or a.get("net.peer.name") or a.get("db.system") or a.get("db.system.name")
    elif a.get("messaging.system"):
        name = a.get("server.address") or a.get("net.peer.name") or a["messaging.system"]
    else:
        name = a.get("server.address") or a.get("net.peer.name") or a.get("url.domain") or a.get("http.host") or a.get("rpc.service") or ""
    kind = ("database" if (a.get("db.system") or a.get("db.system.name")) else
            "messaging" if a.get("messaging.system") else "external")
    return name, kind


def analyse(spans: list[dict], mode: str) -> dict:
    by_id = {(s["trace"], s["span"]): s for s in spans}
    children: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for s in spans:
        if s["parent"]:
            children[(s["trace"], s["parent"])].append(s)

    edges: Counter = Counter()
    edge_info: dict[tuple[str, str], dict] = {}
    problems: list[tuple[str, str]] = []  # (severity, message)
    services = Counter(service_of(s) for s in spans)

    def add_edge(a: str, b: str, kind: str, via: str) -> None:
        edges[(a, b)] += 1
        edge_info.setdefault((a, b), {"kind": kind, "via": set()})["via"].add(via)

    for s in spans:
        svc = service_of(s)
        if s["kind"] in CALLEES and s["parent"]:
            parent = by_id.get((s["trace"], s["parent"]))
            if parent is None:
                problems.append(("warning", f"{svc}: {s['kind']} span '{s['name']}' has parent {s['parent'][:8]} "
                                            "that was never received (context dropped, uninstrumented hop, or not exported yet)"))
            elif parent["kind"] in CALLERS and service_of(parent) != svc:
                add_edge(service_of(parent), svc, "async" if s["kind"] == "CONSUMER" else "sync", s["name"])
            elif parent["kind"] in CALLERS and service_of(parent) == svc:
                problems.append(("error", f"{svc}: self edge ('{parent['name']}' -> '{s['name']}'): two services share one service.name"))
    for s in spans:
        if s["kind"] not in CALLERS:
            continue
        svc = service_of(s)
        remote = [c for c in children[(s["trace"], s["span"])] if c["kind"] in CALLEES and service_of(c) != svc]
        if remote:
            continue
        name, kind = peer_name(s)
        if name:
            add_edge(svc, name, kind, s["name"])
        else:
            problems.append(("error", f"{svc}: {s['kind']} span '{s['name']}' has no remote child and no peer attributes "
                                      f"({', '.join(PEER_KEYS[:4])}...): the edge is dropped from the graph"))
    for name in services:
        if name.startswith("unknown_service") or name == "<missing service.name>":
            problems.append(("error", f"spans carry service name '{name}': set OTEL_SERVICE_NAME / resource service.name"))
    if mode == "dependency":
        internal = Counter(service_of(s) for s in spans if s["kind"] == "INTERNAL")
        for svc, n in internal.items():
            problems.append(("warning", f"{svc}: {n} INTERNAL span(s) in dependency mode (boundary spans only; "
                                        "enable detailed mode deliberately)"))
    missing_env = {service_of(s) for s in spans if not (s["resource"].get("deployment.environment")
                                                        or s["resource"].get("deployment.environment.name"))}
    for svc in sorted(missing_env):
        problems.append(("warning", f"{svc}: resource has no deployment.environment(.name)"))
    traces = {s["trace"] for s in spans}
    multi = [t for t in traces if len({service_of(s) for s in spans if s["trace"] == t}) > 1]
    return {"services": services, "edges": edges, "edge_info": edge_info, "problems": sorted(set(problems)),
            "traces": len(traces), "multi_service_traces": len(multi)}


def parse_map(path: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Expected edges from a dependency-map markdown table (rows whose status is not gap/inferred)."""
    expect, skipped = [], []
    cols: dict[str, int] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip().startswith("|"):
                cols = {} if cols and not line.strip().startswith("|") else cols
                continue
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            lowered = [c.lower() for c in cells]
            if "caller" in lowered and "callee" in lowered:
                cols = {name: i for i, name in enumerate(lowered)}
                continue
            if not cols or set("".join(cells)) <= set("-: "):
                continue
            caller, callee = cells[cols["caller"]], cells[cols["callee"]]
            status = cells[cols["status"]].lower() if "status" in cols and cols["status"] < len(cells) else ""
            if status in ("gap", "inferred", "planned"):
                skipped.append(f"{caller}>{callee} ({status})")
            elif caller and callee and not caller.startswith("<"):
                expect.append((caller, callee))
    return expect, skipped


def report(result: dict, expect: list[tuple[str, str]], services: list[str], forbid: list[tuple[str, str]],
           as_json: bool) -> int:
    edges, problems = result["edges"], result["problems"]
    failed = False
    out = []
    if as_json:
        print(json.dumps({"services": dict(result["services"]),
                          "edges": [{"from": a, "to": b, "count": n, **{"kind": result["edge_info"][(a, b)]["kind"]}}
                                    for (a, b), n in sorted(edges.items())],
                          "problems": [{"severity": s, "message": m} for s, m in problems],
                          "traces": result["traces"], "multi_service_traces": result["multi_service_traces"]}, indent=2))
    else:
        out.append(f"services ({len(result['services'])}): " + ", ".join(f"{k} [{v} spans]" for k, v in sorted(result["services"].items())))
        out.append(f"traces: {result['traces']} ({result['multi_service_traces']} span more than one service)")
        out.append("edges:")
        for (a, b), n in sorted(edges.items()):
            info = result["edge_info"][(a, b)]
            out.append(f"  {a} -> {b}   {info['kind']:9} x{n}   via {', '.join(sorted(info['via']))[:80]}")
        if not edges:
            out.append("  (none)")
    for a, b in expect:
        ok = (a, b) in edges
        failed |= not ok
        out.append(f"{'PASS' if ok else 'FAIL'}  expected edge {a} -> {b}" + ("" if ok else "  (not observed)"))
    for svc in services:
        ok = svc in result["services"]
        failed |= not ok
        out.append(f"{'PASS' if ok else 'FAIL'}  expected service {svc}" + ("" if ok else "  (no spans)"))
    for a, b in forbid:
        ok = (a, b) not in edges
        failed |= not ok
        out.append(f"{'PASS' if ok else 'FAIL'}  forbidden edge {a} -> {b}" + ("" if ok else "  (observed)"))
    for severity, message in problems:
        out.append(f"{severity.upper():7} {message}")
        failed |= severity == "error"
    if not as_json or failed:
        print("\n".join(out), file=sys.stderr if as_json else sys.stdout)
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4318)
    parser.add_argument("--token", default="", help="require 'Authorization: Bearer <token>' (401 otherwise), to test auth wiring")
    parser.add_argument("--expect", action="append", default=[], metavar="A>B", help="edge that must be observed (repeatable)")
    parser.add_argument("--forbid", action="append", default=[], metavar="A>B", help="edge that must not appear")
    parser.add_argument("--service", action="append", default=[], help="service that must send spans (repeatable)")
    parser.add_argument("--map", help="dependency-map markdown file: its caller/callee rows become --expect (gap/inferred rows skipped)")
    parser.add_argument("--mode", choices=["dependency", "detailed"], default="dependency",
                        help="dependency: warn about INTERNAL spans (default); detailed: allow them")
    parser.add_argument("--wait", type=float, default=60, help="max seconds to wait for spans/expectations")
    parser.add_argument("--quiet-period", type=float, default=3, help="seconds without new spans before judging")
    parser.add_argument("--json", action="store_true", help="print the graph as JSON")
    args = parser.parse_args()

    def pair(text: str) -> tuple[str, str]:
        if ">" not in text:
            parser.error(f"expected A>B, got {text!r}")
        a, b = text.split(">", 1)
        return a.strip(), b.strip()

    expect = [pair(e) for e in args.expect]
    forbid = [pair(e) for e in args.forbid]
    if args.map:
        mapped, skipped = parse_map(args.map)
        expect += mapped
        for item in skipped:
            print(f"note: map row {item} not required", file=sys.stderr)

    store = Store()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store, args.token))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"listening on http://{args.host}:{args.port}/v1/traces (waiting up to {args.wait:.0f}s)", file=sys.stderr)

    deadline = time.time() + args.wait
    while time.time() < deadline:
        time.sleep(0.5)
        spans = store.snapshot()
        if spans and time.time() - store.last >= args.quiet_period:
            edges = analyse(spans, args.mode)["edges"]
            wanted_services = set(args.service)
            if all(e in edges for e in expect) and wanted_services <= {service_of(s) for s in spans}:
                break
    server.shutdown()
    spans = store.snapshot()
    if not spans:
        print("no spans received" + (f" ({store.unauthorized} rejected: wrong or missing bearer token)" if store.unauthorized else ""),
              file=sys.stderr)
        sys.exit(2)
    sys.exit(report(analyse(spans, args.mode), expect, args.service, forbid, args.json))


if __name__ == "__main__":
    main()
