#!/usr/bin/env python3
"""Audit a service repository against the platform's API contract (static, no network).

    audit_api.py [PROJECT_DIR] [--json]

Looks at source (Go, Python, Rust, TypeScript/JavaScript), Dockerfiles, Compose files and env files:

  PORT-1   Dockerfile EXPOSE and the compose PORT / Traefik server port are 3000
  PORT-2   no other well-known default port (8080, 8000, ...) in listen/port/addr lines
  HOST-1   every Traefik Host() rule is {service_name}.{env_name}.{domain}
  HOST-2   a routed service has a Traefik loadbalancer server port label
  ENV-1    a routed service receives ENV_NAME (or DEVELOPMENT_ENVIRONMENT)
  HEALTH-1 one root /healthz route exists; no /readyz /health /livez /ping and no /{version}/healthz
  HEALTH-2 the container healthcheck and health.sh probe /healthz, not /v1/healthz or /readyz
  HEALTH-3 healthz code shows env_name, node_name, service_name and api_versions
  INT-1    an /internal route exists; the service token is read from x-internal-service-token
  DOCS-1   Swagger UI at /docs and the spec at /docs/openapi.json
  VER-1    routes are registered under /v{N}

FAIL means the contract is broken; WARN means look at it by hand. Exit 1 when any FAIL. This is a
heuristic scan: run scripts/probe_api.py against the running service for the authoritative check.
Standard library only.
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
    ".ruff_cache", ".mypy_cache", ".next", "site-packages", "docs-generated",
}
SOURCE = {".go", ".py", ".rs", ".ts", ".tsx", ".js", ".mjs", ".cjs"}
ENV_LABELS = {"stg", "prod", "dev", "local", "uat"}
OTHER_PORTS = r"(?:8080|8000|8081|8888|8443)"
INFRA = re.compile(r"POSTGRES|REDIS|KAFKA|CLICKHOUSE|S3_|OTEL|RUSTFS|MINIO|MONGO|MYSQL|GRAFANA|PROMETHEUS", re.I)
VERSION_EVIDENCE = re.compile(r"""["'`]/?v\d+["'`/]|\{version\}|prefix\s*=\s*f?["']/v|Group\(\s*["']/v|nest\(\s*["']/v""")
ROUTE_CALL = re.compile(
    r"""\b(?:app|router|r|api|server)\.(?:get|post|put|patch|delete|Get|Post|Put|Patch|Delete)\(\s*f?["'`](/[^"'`]*)["'`]""")
ROOT_HEALTH = re.compile(r"""["'`](/(?:readyz|health|livez|ready|live|ping))["'`]""")
INTERNAL_ROUTE = re.compile(r"""["'`]/internal["'`]""")
HEALTHZ_ROUTE = re.compile(r"""["'`]/healthz["'`]""")
VERSIONED_HEALTHZ = re.compile(r"""/v\d+/healthz|/\{version\}/healthz|/\$\{\w+\}/healthz""")


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


def is_deploy(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.startswith("dockerfile") or name.endswith((".yaml", ".yml", ".env", ".sh"))
        or name.startswith(".env") or name == "makefile"
    )


def read(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def comment_free(line: str) -> str:
    stripped = line.strip()
    return "" if stripped.startswith(("#", "//", "--", "*", "/*")) else line


def audit_ports(root: Path, path: Path, lines: list[str], out: list[Finding]) -> None:
    rel = path.relative_to(root)
    for number, raw in enumerate(lines, 1):
        line = comment_free(raw)
        where = f"{rel}:{number}"
        expose = re.match(r"\s*EXPOSE\s+(.*)", line)
        if expose and expose.group(1).split()[0].split("/")[0] != "3000":
            out.append(Finding("FAIL", "PORT-1", where, f"EXPOSE {expose.group(1)}: the service listens on 3000"))
        lb = re.search(r"loadbalancer\.server\.port\s*[=:]\s*[\"']?(\$\{[^}]*\}|\d+)", line)
        if lb and not lb.group(1).endswith("3000") and "3000" not in lb.group(1):
            out.append(Finding("FAIL", "PORT-1", where, f"Traefik server port {lb.group(1)}: must be 3000"))
        env_port = re.match(r"\s*(?:-\s*)?PORT\s*[=:]\s*[\"']?(\d+)", line)
        if env_port and env_port.group(1) != "3000":
            out.append(Finding("FAIL", "PORT-1", where, f"PORT={env_port.group(1)}: must be 3000"))
        listens = re.search(r"(?i)\b(http_)?port\b|http_addr|\blisten|\bbind|uvicorn", line)
        if listens and not INFRA.search(line) and re.search(rf"[^\d.]{OTHER_PORTS}\b", line):
            if "PORT-1" not in {f.rule for f in out if f.where == where}:
                out.append(Finding("WARN", "PORT-2", where, f"another default port in `{raw.strip()[:90]}`: use 3000"))


def label_value(line: str, key: str) -> str | None:
    match = re.search(re.escape(key) + r"""[^=:]*[=:]\s*["']?(.*?)["']?\s*$""", line)
    return match.group(1) if match else None


def audit_traefik(root: Path, path: Path, lines: list[str], out: list[Finding]) -> None:
    rel = path.relative_to(root)
    text = "\n".join(lines)
    routed = "traefik.http.routers" in text
    if not routed:
        return
    service_default = re.search(r"SERVICE_NAME\s*:\s*[\"']?\$\{[A-Z_]+:-([a-z0-9-]+)\}", text) or re.search(
        r"SERVICE_NAME\s*[:=]\s*[\"']?([a-z0-9-]+)[\"']?\s*$", text, re.M)
    for number, line in enumerate(lines, 1):
        if "traefik.http.routers" not in line or ".rule" not in line:
            continue
        where = f"{rel}:{number}"
        hosts = re.findall(r"Host\(`([^`]+)`\)", line)
        if not hosts:
            out.append(Finding("WARN", "HOST-1", where, "router rule has no Host(`...`)"))
        for host in hosts:
            labels = host.split(".")
            if len(labels) < 3:
                out.append(Finding("FAIL", "HOST-1", where, f"host `{host}` is not {{service_name}}.{{env_name}}.{{host}}"))
                continue
            env_label = labels[1]
            env_ok = env_label in ENV_LABELS or bool(re.search(r"\$\{[^}]*(ENV|PLANE)[^}]*\}", env_label))
            if not env_ok:
                out.append(Finding("FAIL", "HOST-1", where, f"host `{host}`: second label must be the env name (stg, prod, ...)"))
            first_default = re.search(r"\$\{[A-Z_]+:-([a-z0-9-]+)\}", labels[0])
            first = first_default.group(1) if first_default else labels[0]
            if service_default and re.fullmatch(r"[a-z0-9-]+", first) and first != service_default.group(1):
                out.append(Finding("FAIL", "HOST-1", where,
                                   f"host service label `{first}` differs from SERVICE_NAME `{service_default.group(1)}`"))
    if not re.search(r"loadbalancer\.server\.port", text):
        out.append(Finding("FAIL", "HOST-2", str(rel), "routed service has no traefik loadbalancer.server.port label"))
    if not re.search(r"\b(ENV_NAME|DEVELOPMENT_ENVIRONMENT)\b", text):
        out.append(Finding("FAIL", "ENV-1", str(rel), "routed service gets no ENV_NAME (or DEVELOPMENT_ENVIRONMENT) variable"))


def audit_health_deploy(root: Path, path: Path, lines: list[str], out: list[Finding]) -> None:
    rel = path.relative_to(root)
    for number, raw in enumerate(lines, 1):
        line = comment_free(raw)
        if not re.search(r"HEALTH_APP_PATH|HEALTHCHECK|curl|wget|health\.sh|test:|path", line, re.I):
            continue
        if "S3_HEALTH_PATH" in line:
            continue
        if VERSIONED_HEALTHZ.search(line) or re.search(r"(?<![\w}\]/])/(readyz|livez|health)\b", line):
            out.append(Finding("FAIL", "HEALTH-2", f"{rel}:{number}", "probe uses a versioned or old health path: use /healthz"))
        elif re.search(r"HEALTH_APP_PATH\s*[=:]", line) and "/healthz" not in line:
            out.append(Finding("FAIL", "HEALTH-2", f"{rel}:{number}", "HEALTH_APP_PATH must be /healthz"))


class SourceScan:
    def __init__(self) -> None:
        self.healthz = False
        self.internal = False
        self.token_header = False
        self.docs = False
        self.spec_path = False
        self.legacy_docs: list[str] = []
        self.health_files: list[tuple[Path, str]] = []


def root_health_level(before: str, prefix_evidence: bool) -> str | None:
    """FAIL on the root app, silent on a group when the file mounts versions (the probe decides)."""
    receiver = re.search(r"(\w+)\.\w+\(\s*f?$", before)
    if receiver and receiver.group(1) in {"app", "server"}:
        return "FAIL"
    if not prefix_evidence:
        return "FAIL"
    return None


def is_test(path: Path) -> bool:
    name = path.name
    return (
        name.startswith("test_") or name.endswith(("_test.go", "_test.py", "tests.rs", ".test.ts", ".spec.ts", ".test.js"))
        or bool({"tests", "test", "__tests__", "e2e"} & set(path.parts))
    )


def audit_source(root: Path, path: Path, lines: list[str], scan: SourceScan, out: list[Finding]) -> None:
    rel = path.relative_to(root)
    text = "\n".join(lines)
    if is_test(path):
        return
    if HEALTHZ_ROUTE.search(text) or "healthz" in text:
        scan.health_files.append((rel, text))
    if HEALTHZ_ROUTE.search(text):
        scan.healthz = True
    if INTERNAL_ROUTE.search(text):
        scan.internal = True
    if re.search(r"x[-_]internal[-_]service[-_]token", text, re.I):
        scan.token_header = True
    prefix_evidence = bool(VERSION_EVIDENCE.search(text))
    for number, raw in enumerate(lines, 1):
        line = comment_free(raw)
        where = f"{rel}:{number}"
        for match in ROOT_HEALTH.finditer(line):
            level = root_health_level(line[: match.start()], prefix_evidence)
            if level:
                out.append(Finding(level, "HEALTH-1", where, f"health route {match.group(1)}: the one health endpoint is /healthz"))
        if VERSIONED_HEALTHZ.search(line):
            out.append(Finding("FAIL", "HEALTH-1", where, "versioned healthz: health is one root /healthz, not per version"))
        for match in ROUTE_CALL.finditer(line):
            route = match.group(1)
            if route == "/" or re.match(r"/(v\d+|docs|healthz|internal)(/|$)", route) or ROOT_HEALTH.search(f'"{route}"'):
                continue
            if not prefix_evidence:
                out.append(Finding("WARN", "VER-1", where, f"route {route} is not under /v{{N}}"))
    if re.search(r"/docs\b", text) and re.search(r"(?i)openapi|swagger", text):
        scan.docs = True
    if "/docs/openapi.json" in text:
        scan.spec_path = True
    for legacy in ("/swagger", "/api-docs", "/redoc"):
        if re.search(rf"""["'`]{legacy}["'`/]""", text):
            scan.legacy_docs.append(f"{rel} ({legacy})")


def audit_health_body(scan: SourceScan, out: list[Finding]) -> None:
    low = "\n".join(text for _, text in scan.health_files).lower()
    for want, alts in (("env_name", ("env_name", "envname")), ("node_name", ("node_name", "nodename")),
                       ("service_name", ("service_name", "servicename")),
                       ("api_versions", ("api_versions", "apiversions"))):
        if scan.health_files and not any(a in low for a in alts):
            out.append(Finding("WARN", "HEALTH-3", str(scan.health_files[0][0]), f"healthz code does not mention {want}"))


def run(root: Path) -> list[Finding]:
    out: list[Finding] = []
    scan = SourceScan()
    seen_deploy = False
    for path in files(root):
        lines = read(path)
        if path.suffix in SOURCE:
            audit_source(root, path, lines, scan, out)
            audit_ports(root, path, lines, out)
        elif is_deploy(path):
            seen_deploy = True
            audit_ports(root, path, lines, out)
            audit_health_deploy(root, path, lines, out)
            if path.suffix in {".yaml", ".yml"}:
                audit_traefik(root, path, lines, out)
    if not scan.healthz:
        out.append(Finding("FAIL", "HEALTH-1", str(root), "no root /healthz route found in the source"))
    audit_health_body(scan, out)
    if not scan.internal:
        out.append(Finding("FAIL", "INT-1", str(root), "no /internal route found: add the token-protected health and caller endpoint"))
    if not scan.token_header:
        out.append(Finding("FAIL", "INT-1", str(root), "the service token header x-internal-service-token is never read"))
    if not scan.docs:
        out.append(Finding("FAIL", "DOCS-1", str(root), "no Swagger UI at /docs found"))
    elif not scan.spec_path:
        out.append(Finding("WARN", "DOCS-1", str(root), "the spec is not served at /docs/openapi.json"))
    for legacy in scan.legacy_docs:
        out.append(Finding("WARN", "DOCS-1", legacy, "legacy docs path: serve Swagger at /docs only"))
    if not seen_deploy:
        out.append(Finding("WARN", "PORT-1", str(root), "no Dockerfile/compose/env files found to check"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", nargs="?", default=".", help="repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    findings = run(root)
    fails = sum(f.level == "FAIL" for f in findings)
    warns = sum(f.level == "WARN" for f in findings)
    if args.json:
        print(json.dumps([f.as_dict() for f in findings], indent=2))
    else:
        for f in sorted(findings, key=lambda f: (f.level != "FAIL", f.rule, f.where)):
            print(f"{f.level:4}  {f.rule:8} {f.where}: {f.message}")
        print(f"{fails} FAIL, {warns} WARN in {root}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
