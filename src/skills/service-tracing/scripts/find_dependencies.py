#!/usr/bin/env python3
"""Draft the service dependency map of one or more repositories (evidence for service-tracing, dependency mode).

    python3 scripts/find_dependencies.py ~/code/repo-a ~/code/repo-b            # markdown draft
    python3 scripts/find_dependencies.py . --json

Reads, without running anything:
  * Compose/Swarm files   service names (OTEL_SERVICE_NAME / SERVICE_NAME, else the service key), network aliases,
                          environment variables that name infrastructure (POSTGRES_HOST, KAFKA_BOOTSTRAP_SERVERS,
                          REDIS_HOST, CLICKHOUSE_HOST, S3_ENDPOINT) or another service (URL/host variables),
                          Traefik routers (an ingress -> service edge) and depends_on
  * Source code           per project (go.mod, pyproject.toml/requirements.txt, package.json, Cargo.toml): which
                          HTTP/gRPC/messaging/datastore client libraries are used and whether a matching
                          OpenTelemetry instrumentation is present (the "instrumentation gaps")

Everything is evidence for a human or agent to confirm, never a verified edge: rows start as `inferred`.
Verify them with scripts/otlp_trace_check.py. Needs python3; Compose parsing needs PyYAML (else it says so).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:  # compose files are skipped with a note
    yaml = None

SKIP_DIRS = {".git", "node_modules", "target", "vendor", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
COMPOSE_DIRS = {"composes", "compose", "deploy", "swarm", "stacks", "stack"}
COMPOSE = re.compile(r"(^|[-_.])(docker-)?compose([-_.].*)?\.ya?ml$|^(stack|swarm)[-_.].*\.ya?ml$", re.I)
INFRA_VARS = {  # variable -> (node name, kind)
    "POSTGRES_HOST": ("postgres", "database"), "PGHOST": ("postgres", "database"),
    "REDIS_HOST": ("redis", "database"), "CLICKHOUSE_HOST": ("clickhouse", "database"),
    "KAFKA_BOOTSTRAP_SERVERS": ("kafka", "messaging"), "KAFKA_BROKERS": ("kafka", "messaging"),
    "S3_ENDPOINT": ("s3", "external"),
}
URL_VAR = re.compile(r"(_URL|_URI|_ENDPOINT|_ADDR|_ADDRESS|_HOST|_BASE_URL|_API)$")
IGNORED_VAR = re.compile(r"^(OTEL_|LOG_|TZ$|PATH$|HEALTH_)")
HOST = re.compile(r"(?:[a-z][a-z0-9+.-]*://)?(?:[^@/\s]*@)?([A-Za-z0-9_.-]+)(?::\d+)?")

# library signatures per language: capability -> (client regex, instrumentation regex)
SIGNATURES = {
    "go": {"manifest": ["go.mod"], "glob": "*.go", "libs": {
        "http client": (r"net/http\"|go-resty|\"github.com/hashicorp/go-retryablehttp", r"otelhttp"),
        "gRPC": (r"google.golang.org/grpc\"", r"otelgrpc"),
        "kafka": (r"confluent-kafka-go|IBM/sarama|segmentio/kafka-go|franz-go", r"otelkafka|otelsarama|kotel|instrumentation/.*kafka"),
        "postgres": (r"jackc/pgx|go-pg/pg|lib/pq|\"database/sql\"|uptrace/bun", r"otelpgx|otelsql|bunotel|pgotel|opentelemetry.*sql"),
        "redis": (r"redis/go-redis|gomodule/redigo", r"redisotel"),
        "clickhouse": (r"ClickHouse/clickhouse-go", r"opentelemetry.*clickhouse"),
        "s3": (r"aws-sdk-go-v2/service/s3|minio-go", r"otelaws"),
        "fiber": (r"gofiber/fiber", r"otelfiber|contrib/otelfiber"),
        "gin": (r"gin-gonic/gin", r"otelgin"),
    }},
    "python": {"manifest": ["pyproject.toml", "requirements.txt", "uv.lock"], "glob": "*.py", "libs": {
        "http client": (r"\b(httpx|requests|aiohttp|urllib3)\b", r"instrumentation-(httpx|requests|aiohttp-client|urllib3)"),
        "gRPC": (r"\bgrpc\b|grpcio", r"instrumentation-grpc"),
        "kafka": (r"confluent.kafka|aiokafka|kafka-python", r"instrumentation-(confluent-kafka|aiokafka|kafka-python)"),
        "postgres": (r"\b(psycopg2?|asyncpg|sqlalchemy)\b", r"instrumentation-(psycopg2?|asyncpg|sqlalchemy)"),
        "redis": (r"\bredis\b", r"instrumentation-redis"),
        "clickhouse": (r"clickhouse.(connect|driver)", r"instrumentation-clickhouse"),
        "s3": (r"\b(boto3|aioboto3|botocore)\b", r"instrumentation-(botocore|boto3sqs)"),
        "litestar": (r"\blitestar\b", r"instrumentation-asgi"),
        "celery": (r"\bcelery\b", r"instrumentation-celery"),
    }},
    "typescript": {"manifest": ["package.json"], "glob": "*.ts", "libs": {
        "http client": (r"\b(axios|undici|got|node-fetch)\b|fetch\(", r"instrumentation-(http|undici)|auto-instrumentations-node"),
        "gRPC": (r"@grpc/grpc-js", r"instrumentation-grpc|auto-instrumentations-node"),
        "kafka": (r"\bkafkajs\b", r"instrumentation-kafkajs|auto-instrumentations-node"),
        "postgres": (r"[\"'/]pg[\"'/]|\bpostgres\b|\bprisma\b|typeorm", r"instrumentation-pg|auto-instrumentations-node"),
        "redis": (r"\b(ioredis|redis)\b", r"instrumentation-(ioredis|redis)|auto-instrumentations-node"),
        "clickhouse": (r"@clickhouse/client", r"instrumentation-clickhouse"),
        "s3": (r"@aws-sdk/client-s3", r"instrumentation-aws-sdk|auto-instrumentations-node"),
        "express/nest/fastify": (r"\b(express|@nestjs/core|fastify)\b", r"instrumentation-(express|nestjs-core|fastify)|auto-instrumentations-node"),
    }},
    "rust": {"manifest": ["Cargo.toml"], "glob": "*.rs", "libs": {
        "http client": (r"\b(reqwest|hyper)\b", r"opentelemetry-http|tracing-opentelemetry|reqwest-tracing"),
        "gRPC": (r"\btonic\b", r"tracing-opentelemetry|tonic-tracing"),
        "kafka": (r"\brdkafka\b", r"tracing-opentelemetry"),
        "postgres": (r"\b(sqlx|tokio-postgres|diesel)\b", r"tracing-opentelemetry|sqlx-tracing"),
        "redis": (r"\bredis\b", r"tracing-opentelemetry"),
        "clickhouse": (r"\bclickhouse\b", r"tracing-opentelemetry"),
        "s3": (r"aws-sdk-s3|rust-s3", r"tracing-opentelemetry"),
        "axum/actix": (r"\b(axum|actix-web)\b", r"axum-tracing-opentelemetry|tracing-actix-web|tracing-opentelemetry"),
    }},
}
OTEL_SDK = {"go": r"go.opentelemetry.io/otel/sdk", "python": r"opentelemetry-sdk", "typescript": r"@opentelemetry/(sdk|api)",
            "rust": r"opentelemetry_sdk|opentelemetry-sdk"}


def walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        yield Path(dirpath), filenames


def redact(value: str) -> str:
    """Never print credentials: drop URL userinfo and mask anything that looks like a secret."""
    value = re.sub(r"(://)[^/@\s]*@", r"\1***@", str(value))
    return value if len(value) < 120 else value[:117] + "..."


def default_of(value) -> str:
    """`${VAR:-default}` -> default; plain value -> itself; `${VAR:?msg}` -> ''."""
    text = str(value)
    m = re.fullmatch(r"\$\{[A-Za-z0-9_]+:?-([^}]*)\}", text)
    if m:
        return m.group(1)
    return "" if "${" in text else text


def compose_services(path: Path, notes: list[str]) -> list[dict]:
    if yaml is None:
        notes.append(f"{path}: skipped (install PyYAML to read compose files)")
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        notes.append(f"{path}: not parsed ({type(exc).__name__})")
        return []
    out = []
    for key, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        env = svc.get("environment") or {}
        if isinstance(env, list):
            env = dict(item.split("=", 1) if "=" in item else (item, "") for item in env)
        name = default_of(env.get("OTEL_SERVICE_NAME", "")) or default_of(env.get("SERVICE_NAME", "")) or key
        aliases = {key}
        nets = svc.get("networks") or {}
        if isinstance(nets, dict):
            for cfg in nets.values():
                if isinstance(cfg, dict):
                    aliases.update(cfg.get("aliases") or [])
        labels = (svc.get("deploy") or {}).get("labels") or svc.get("labels") or {}
        if isinstance(labels, list):
            labels = dict(item.split("=", 1) for item in labels if "=" in item)
        hosts = re.findall(r"Host\(`([^`]+)`\)", " ".join(str(v) for v in labels.values()))
        deps = svc.get("depends_on") or []
        out.append({"image": str(svc.get("image", "")), "file": str(path), "key": key, "name": name, "aliases": sorted(aliases), "env": {k: str(v) for k, v in env.items()},
                    "ingress_hosts": hosts, "depends_on": sorted(deps if isinstance(deps, list) else deps.keys())})
    return out


IMAGE_KIND = [(r"postgres|timescale", "database"), (r"redis|dragonfly|valkey", "database"), (r"clickhouse", "database"),
              (r"kafka|redpanda", "messaging"), (r"rustfs|minio|s3", "external")]


def target_kind(target: dict) -> str:
    image = target.get("image", "").lower()
    return next((kind for pattern, kind in IMAGE_KIND if re.search(pattern, image)), "sync")


def edges_from_compose(services: list[dict]) -> list[dict]:
    by_alias: dict[str, dict] = {}
    for s in services:
        for a in s["aliases"] + [s["name"]]:
            by_alias.setdefault(a.lower(), s)
    edges = []
    for s in services:
        for var, value in s["env"].items():
            if IGNORED_VAR.match(var):
                continue
            raw = default_of(value) or value
            if var in INFRA_VARS:
                node, kind = INFRA_VARS[var]
                edges.append(edge(s["name"], node, kind, f"{node} ({var})", f"`{var}` in {Path(s['file']).name}", "infra"))
                continue
            if URL_VAR.search(var) and not re.search(r"(PASSWORD|SECRET|TOKEN)", var):
                m = HOST.match(raw.strip())
                host = (m.group(1) if m else "").lower()
                target = by_alias.get(host)
                if target and target is not s:
                    edges.append(edge(s["name"], target["name"], target_kind(target), f"{var}", f"`{var}={redact(raw)}` in {Path(s['file']).name}", "env"))
                elif host and "." in host and not host.endswith((".internal", ".local", ".svc")) and not re.fullmatch(r"[\d.]+", host) and not host.startswith("localhost"):
                    edges.append(edge(s["name"], host, "external", f"{var}", f"`{var}={redact(raw)}` in {Path(s['file']).name}", "env"))
        for dep in s["depends_on"]:
            target = by_alias.get(dep.lower())
            if target and target is not s:
                edges.append(edge(s["name"], target["name"], "startup", "depends_on", f"depends_on in {Path(s['file']).name}", "depends_on"))
        for host in s["ingress_hosts"]:
            edges.append(edge("ingress", s["name"], "sync", f"Host({host})", f"Traefik router in {Path(s['file']).name}", "ingress"))
    seen, unique = set(), []
    for e in edges:
        key = (e["caller"], e["callee"], e["transport"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def edge(caller, callee, kind, transport, evidence, source) -> dict:
    return {"caller": caller, "callee": callee, "kind": kind, "transport": transport, "evidence": evidence,
            "source": source, "status": "inferred"}


def scan_projects(root: Path) -> list[dict]:
    projects = []
    for dirpath, filenames in walk(root):
        for lang, spec in SIGNATURES.items():
            manifests = [m for m in spec["manifest"] if m in filenames]
            if not manifests:
                continue
            manifest_text = "\n".join((dirpath / m).read_text(encoding="utf-8", errors="ignore") for m in manifests if m != "uv.lock")
            sources = []
            for sub, files in walk(dirpath):
                if lang == "typescript" and sub != dirpath and "package.json" in files:
                    continue  # nested project
                sources += [sub / f for f in files if Path(f).match(spec["glob"]) or (lang == "typescript" and f.endswith((".tsx", ".js", ".mjs")))]
                if len(sources) > 4000:
                    break
            text = manifest_text + "\n" + "\n".join(p.read_text(encoding="utf-8", errors="ignore")[:60000] for p in sources[:1500])
            if lang == "typescript" and "main" not in manifest_text and not sources:
                continue
            libs = {}
            for capability, (client, instr) in spec["libs"].items():
                if re.search(client, text):
                    libs[capability] = bool(re.search(instr, text))
            if libs or re.search(OTEL_SDK[lang], text):
                projects.append({"path": str(dirpath), "language": lang, "otel_sdk": bool(re.search(OTEL_SDK[lang], text)),
                                 "clients": libs, "gaps": sorted(k for k, v in libs.items() if not v and k not in ("fiber", "gin", "litestar", "celery"))})
    return projects


def render_markdown(services, edges, projects, notes) -> str:
    out = ["# Dependency map (draft: all rows are `inferred` until observed in a trace)", ""]
    out += ["| Caller | Callee | Kind | Transport / name | Context propagated | Instrumented | Evidence | Status |",
            "|---|---|---|---|---|---|---|---|"]
    for e in sorted(edges, key=lambda e: (e["caller"], e["callee"])):
        if e["source"] in ("depends_on",):
            continue
        out.append(f"| {e['caller']} | {e['callee']} | {e['kind']} | {e['transport']} | ? | ? | {e['evidence']} | {e['status']} |")
    startup = [e for e in edges if e["source"] == "depends_on"]
    if startup:
        out += ["", "Start-up order hints (`depends_on`) are not call edges: " + ", ".join(f"{e['caller']}→{e['callee']}" for e in startup)]
    out += ["", "## Services found", ""]
    for s in sorted(services, key=lambda s: (s["name"], s["key"])):
        out.append(f"- `{s['name']}` (compose key `{s['key']}`, `{Path(s['file']).name}`)" + (f", routed at {', '.join(s['ingress_hosts'])}" if s["ingress_hosts"] else ""))
    out += ["", "## Code projects: client libraries and instrumentation", ""]
    for p in sorted(projects, key=lambda p: p["path"]):
        caps = ", ".join(f"{k}{'' if v else ' (**no instrumentation seen**)'}" for k, v in sorted(p["clients"].items())) or "no known clients"
        out.append(f"- `{p['path']}` [{p['language']}] otel sdk: {'yes' if p['otel_sdk'] else '**no**'}; {caps}")
    gaps = [p for p in projects if p["gaps"] or not p["otel_sdk"]]
    if gaps:
        out += ["", "## Likely instrumentation gaps (confirm in code, then use the helpers or the contrib package)", ""]
        for p in gaps:
            if not p["otel_sdk"]:
                out.append(f"- `{p['path']}`: no OpenTelemetry SDK; start with `service-tracing` templates")
            if p["gaps"]:
                out.append(f"- `{p['path']}`: add instrumentation or `peer_span` for: {', '.join(p['gaps'])}")
    if notes:
        out += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="+", help="repository or monorepo directories")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-code", action="store_true", help="skip the source scan (compose/env only)")
    args = parser.parse_args()

    notes: list[str] = []
    services: list[dict] = []
    projects: list[dict] = []
    for raw in args.roots:
        root = Path(raw).expanduser().resolve()
        if not root.is_dir():
            sys.exit(f"not a directory: {raw}")
        for dirpath, filenames in walk(root):
            for f in filenames:
                is_yaml = f.endswith((".yaml", ".yml"))
                if (COMPOSE.search(f) or (is_yaml and dirpath.name in COMPOSE_DIRS)) and ".local." not in f:
                    services += compose_services(dirpath / f, notes)
        if not args.no_code:
            projects += scan_projects(root)
    edges = edges_from_compose(services)
    if args.json:
        print(json.dumps({"services": services, "edges": edges, "projects": projects, "notes": notes}, indent=2))
    else:
        print(render_markdown(services, edges, projects, notes))


if __name__ == "__main__":
    main()
