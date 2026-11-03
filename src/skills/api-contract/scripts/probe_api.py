#!/usr/bin/env python3
"""Probe a running service against the platform's API contract.

    probe_api.py https://orders-api.stg.@DOMAIN@
    probe_api.py http://127.0.0.1:3000 --service orders-api --env local --versions v1,v2
    probe_api.py https://127.0.0.1 --host-header orders-api.stg.@DOMAIN@   # through Traefik by IP

Checks: the host is {service}.{env}.{domain}; /docs is Swagger UI and /docs/openapi.json lists
/healthz and only /healthz or versioned (/v1/...) routes; /healthz (one endpoint, not per version)
has the exact body (see assets/healthz.schema.json), lists every version in `api_versions`, answers
200 for status ok and 503 for status down, is not cached, names the same service and env as the
host, and shows no secret in `config`; /readyz and /{version}/healthz do not answer 200. /internal
answers 401 without the service token; with --token it accepts the plain and the `Bearer` form and
returns the /healthz body plus the `x-user-id` / `x-username` it was sent as `caller`.
Exit 0 = no errors (warnings allowed), 1 = errors.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

FIELDS = {
    "status", "service_name", "env_name", "node_name", "api_versions", "service_version",
    "started_at", "checked_at", "uptime_seconds", "config", "checks",
}
INTERNAL_FIELDS = FIELDS | {"caller"}
TOKEN_HEADER = "x-internal-service-token"
CHECK_FIELDS = {"name", "status", "latency_ms", "error"}
SECRET_KEY = re.compile(r"pass|secret|token|key|dsn|credential|auth", re.I)
URL_WITH_PASSWORD = re.compile(r"://[^/\s:@]+:[^/\s@]+@")
RFC3339 = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)$")


class Report:
    def __init__(self) -> None:
        self.errors = 0

    def ok(self, where: str, message: str) -> None:
        print(f"  ok     {where}: {message}")

    def error(self, where: str, message: str) -> None:
        self.errors += 1
        print(f"  ERROR  {where}: {message}")

    def warn(self, where: str, message: str) -> None:
        print(f"  warn   {where}: {message}")

    def expect(self, condition: bool, where: str, good: str, bad: str) -> bool:
        (self.ok if condition else self.error)(where, good if condition else bad)
        return condition


def fetch(base: str, path: str, host_header: str, timeout: float, insecure: bool, headers: dict | None = None):
    request = urllib.request.Request(base.rstrip("/") + path, headers={"Accept": "*/*", **(headers or {})})
    if host_header:
        request.add_header("Host", host_header)
    context = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {}, str(exc).encode()


def host_parts(host: str) -> tuple[str, str, str]:
    labels = host.split(".")
    if len(labels) >= 3 and not re.fullmatch(r"[\d.]+", host):
        return labels[0], labels[1], ".".join(labels[2:])
    return "", "", ""


def check_secret_free(rep: Report, where: str, config: dict) -> None:
    for key, value in config.items():
        if SECRET_KEY.search(key) and key not in {"docs_url"}:
            rep.error(where, f"config key `{key}` looks like a secret: show only non-secret values")
        if isinstance(value, str) and URL_WITH_PASSWORD.search(value):
            rep.error(where, f"config `{key}` contains a URL with a password")


def check_healthz_body(rep: Report, where: str, versions: list[str], status: int, headers: dict, body: bytes, want: dict,
                       fields: set[str] = FIELDS) -> dict | None:
    try:
        data = json.loads(body)
    except ValueError:
        rep.error(where, f"HTTP {status} is not JSON")
        return None
    if not isinstance(data, dict):
        rep.error(where, "body is not a JSON object")
        return None
    missing, extra = fields - set(data), set(data) - fields
    rep.expect(not missing and not extra, where, "has exactly the contract fields",
               f"missing {sorted(missing)} extra {sorted(extra)}")
    state = data.get("status")
    rep.expect((state, status) in {("ok", 200), ("down", 503)}, where, f"status `{state}` with HTTP {status}",
               f"status `{state}` with HTTP {status} (ok -> 200, down -> 503)")
    cache = {k.lower(): v for k, v in headers.items()}.get("cache-control", "")
    rep.expect("no-store" in cache, where, "Cache-Control: no-store", f"Cache-Control is `{cache}`, expected no-store")
    served = data.get("api_versions")
    good = isinstance(served, list) and bool(served) and all(re.match(r"^v\d+$", str(v)) for v in served)
    rep.expect(good, where, f"api_versions = {served}", f"api_versions must be a non-empty list like [\"v1\"], got `{served}`")
    if good:
        absent = [v for v in versions if v not in served]
        rep.expect(not absent, where, f"api_versions lists {versions}", f"api_versions does not list {absent}")
    for field in ("service_name", "env_name", "node_name"):
        rep.expect(bool(data.get(field)), where, f"{field} = {data.get(field)}", f"{field} is empty")
    for field, expected in want.items():
        if expected:
            rep.expect(data.get(field) == expected, where, f"{field} matches the host ({expected})",
                       f"{field} is `{data.get(field)}` but the host says `{expected}`")
    for field in ("started_at", "checked_at"):
        rep.expect(bool(RFC3339.match(str(data.get(field, "")))), where, f"{field} is RFC 3339", f"{field} is not RFC 3339")
    check_config(rep, where, data.get("config"))
    check_checks(rep, where, data.get("checks"))
    return data


def check_config(rep: Report, where: str, config) -> None:
    if not isinstance(config, dict):
        rep.error(where, "config is not an object")
        return
    rep.expect(config.get("port") == 3000, where, "config.port is 3000", f"config.port is `{config.get('port')}`, must be 3000")
    rep.expect(config.get("docs_url") == "/docs", where, "config.docs_url is /docs", "config.docs_url must be /docs")
    rep.expect("log_level" in config, where, "config.log_level present", "config.log_level missing")
    check_secret_free(rep, where, config)


def check_checks(rep: Report, where: str, checks) -> None:
    if not isinstance(checks, list):
        rep.error(where, "checks is not a list (use [] when there are none)")
        return
    for item in checks:
        bad = not isinstance(item, dict) or set(item) != CHECK_FIELDS
        if bad:
            rep.error(where, f"check entry must have exactly {sorted(CHECK_FIELDS)}: {item}")
        elif item["error"] not in ("", "timeout", "unavailable"):
            rep.error(where, f"check `{item['name']}` error must be a short code, got `{item['error']}`")


def check_internal(rep: Report, args, versions: list[str], want: dict) -> None:
    """/internal: 401 without the token; with it, the /healthz body plus the caller it was told about."""
    where = "/internal"
    status, _, _ = fetch(args.base, where, args.host_header, args.timeout, args.insecure)
    rep.expect(status == 401, where, "401 without the service token", f"HTTP {status} without a token: must be 401")
    status, _, _ = fetch(args.base, where, args.host_header, args.timeout, args.insecure, {TOKEN_HEADER: "wrong-" + "x" * 8})
    rep.expect(status == 401, where, "401 with a wrong token", f"HTTP {status} with a wrong token: must be 401")
    if not args.token:
        rep.warn(where, "no --token (or INTERNAL_SERVICE_TOKEN): the authenticated checks were skipped")
        return
    identity = {"x-user-id": "probe-user", "x-username": "probe"}
    for label, value in (("plain", args.token), ("Bearer", f"Bearer {args.token}")):
        status, headers, body = fetch(args.base, where, args.host_header, args.timeout, args.insecure,
                                      {TOKEN_HEADER: value, **identity})
        if status == 0:
            rep.error(where, f"no response: {body.decode('utf-8', 'replace')}")
            return
        rep.expect(status in (200, 503), where, f"{label} token accepted (HTTP {status})", f"{label} token gave HTTP {status}")
        if status not in (200, 503):
            continue
        if label == "plain":
            data = check_healthz_body(rep, where, versions, status, headers, body, want, INTERNAL_FIELDS)
            caller = (data or {}).get("caller")
            rep.expect(caller == {"user_id": "probe-user", "username": "probe"}, where,
                       "caller shows x-user-id and x-username", f"caller is `{caller}`")


def check_docs(rep: Report, args) -> None:
    where = "/docs"
    status, headers, body = fetch(args.base, "/docs", args.host_header, args.timeout, args.insecure)
    text = body.decode("utf-8", "replace").lower()
    rep.expect(status == 200 and "swagger" in text, where, "Swagger UI served", f"HTTP {status}, no Swagger UI in the body")
    where = "/docs/openapi.json"
    status, _, body = fetch(args.base, where, args.host_header, args.timeout, args.insecure)
    if not rep.expect(status == 200, where, "served", f"HTTP {status}"):
        return
    try:
        spec = json.loads(body)
    except ValueError:
        rep.error(where, "not JSON")
        return
    rep.expect("openapi" in spec or "swagger" in spec, where, "is an OpenAPI document", "no `openapi`/`swagger` key")
    paths = spec.get("paths", {})
    rep.expect("/healthz" in paths, where, "documents /healthz", "does not document /healthz")
    rep.expect("/internal" in paths, where, "documents /internal", "does not document /internal")
    loose = [p for p in paths if p not in ("/healthz", "/internal") and not re.match(r"^/v\d+(/|$)", p)]
    rep.expect(not loose, where, "every documented path is /healthz, /internal or versioned", f"unversioned paths: {loose}")
    stale = [p for p in paths if re.match(r"^/v\d+/healthz$", p)]
    rep.expect(not stale, where, "no versioned healthz documented", f"remove {stale}: health is /healthz only")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base", help="base URL, for example https://orders-api.stg.@DOMAIN@")
    parser.add_argument("--versions", default="v1", help="comma-separated API versions /healthz must list (default v1)")
    parser.add_argument("--service", default="", help="expected service name (default: first host label)")
    parser.add_argument("--env", default="", help="expected env name (default: second host label)")
    parser.add_argument("--host-header", default="", help="send this Host header (probe through an IP)")
    parser.add_argument("--token", default=os.environ.get("INTERNAL_SERVICE_TOKEN", ""),
                        help="the service token, to check /internal (default: $INTERNAL_SERVICE_TOKEN)")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--insecure", action="store_true", help="do not verify TLS certificates")
    parser.add_argument("--allow-legacy-health", action="store_true",
                        help="warn (not error) while the old /readyz and /{version}/healthz still answer 200")
    args = parser.parse_args()
    args.base = args.base.rstrip("/")
    rep = Report()
    host = args.host_header or (urlsplit(args.base).hostname or "")
    service, env, domain = host_parts(host)
    want = {"service_name": args.service or service, "env_name": args.env or env}
    print(f"probe {args.base} (host {host})")
    if service:
        rep.ok("host", f"{service}.{env}.{domain} = {{service_name}}.{{env_name}}.{{host}}")
    elif not (args.service and args.env):
        rep.warn("host", "not {service_name}.{env_name}.{host}; pass --service and --env to check the body")
    versions = [v.strip() for v in args.versions.split(",") if v.strip()]
    check_docs(rep, args)
    where = "/healthz"
    status, headers, body = fetch(args.base, where, args.host_header, args.timeout, args.insecure)
    if status == 0:
        rep.error(where, f"no response: {body.decode('utf-8', 'replace')}")
    else:
        check_healthz_body(rep, where, versions, status, headers, body, want)
    check_internal(rep, args, versions, want)
    legacy_paths = ["/readyz"] + [f"/{version}/healthz" for version in versions]
    for legacy in legacy_paths:
        status, _, _ = fetch(args.base, legacy, args.host_header, args.timeout, args.insecure)
        # /v1 needs the service token, so an unknown path there is 401, not 404: only 200 is wrong.
        gone = status != 200
        if args.allow_legacy_health and not gone:
            rep.warn(legacy, "still answers 200: remove it after the callers moved to /healthz")
            continue
        rep.expect(gone, legacy, "not a health endpoint", "answered 200: health is /healthz only")
    print(f"{rep.errors} error(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
