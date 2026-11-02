#!/usr/bin/env python3
"""Static checks for a Swarm Compose deployment file (standard library + `docker compose`).

Renders each file with dummy values and checks the deployment contract:

    python3 scripts/check_deploy.py docker-compose.yaml \\
        --env-file deploy/stg.env --set RUN_ENV=stg --set APP_IMAGE=example.invalid/app@sha256:<64 hex>

Checks per service: logging cap, memory limit, health check, stop grace period, update policy,
Traefik labels (under deploy.labels, unique plane-qualified router/service names, port, network),
external secrets with explicit names, `*_FILE` variables backed by a mounted secret, no `latest`
image, no `build:` and no published host ports on routed services.
API contract (api-contract skill) for routed services: the `Host()` rule is
`{SERVICE_NAME}.{ENV_NAME}.{domain}`, the process port and the Traefik server port are 3000,
`ENV_NAME` is set, and the container health probe uses `/healthz`.
Tracing: one `OTEL_SERVICE_NAME` per service (unique, equal to `SERVICE_NAME`), base-URL endpoint,
sampler ratio within 0..1, the OTLP token only as a mounted secret.
Infrastructure (PostgreSQL, Redis, ClickHouse, Kafka, S3): the detailed `<INFRA>_HOST/PORT/...`
variables are complete, `HEALTH_DEPS` lists exactly the infrastructure the service uses, and
passwords/keys never have a default value and never sit in a committed env file.

Exit code 0 = no errors (warnings may remain), 1 = at least one error, 2 = could not render.
Compose rendering is not Swarm validation: also run `docker stack config` on the same inputs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

SECRET_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
SECRET_VAR = re.compile(r"(PASSWORD|SECRET|SECRET_KEY|ACCESS_KEY|PRIVATE_KEY|API_KEY|TOKEN)$")
DEFAULTED = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*:\s*.*\$\{[A-Za-z0-9_]+:?-([^}]+)\}")

# infrastructure -> (variable prefix, always-required variables, secrets that need value or *_FILE)
INFRA = {
    "postgres": ("POSTGRES_", ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER"], ["POSTGRES_PASSWORD"]),
    "redis": ("REDIS_", ["REDIS_HOST"], ["REDIS_PASSWORD"]),
    "clickhouse": ("CLICKHOUSE_", ["CLICKHOUSE_HOST", "CLICKHOUSE_USER"], ["CLICKHOUSE_PASSWORD"]),
    "kafka": ("KAFKA_", ["KAFKA_BOOTSTRAP_SERVERS"], []),
    "s3": ("S3_", ["S3_ENDPOINT", "S3_BUCKET"], ["S3_ACCESS_KEY", "S3_SECRET_KEY"]),
}
INFRA_ALIASES = {"postgresql": "postgres", "pg": "postgres", "redpanda": "kafka", "rustfs": "s3", "minio": "s3"}


def check_raw_defaults(path: str, rep: "Report") -> None:
    """Secrets never get a default value (`${X_PASSWORD:-something}`), whatever the rendered result."""
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.lstrip().startswith("#"):
                continue
            m = DEFAULTED.match(line)
            if m and SECRET_VAR.search(m.group(1)) and not m.group(1).endswith("_FILE") and m.group(2).strip():
                rep.error(f"{path}:{number}", f"`{m.group(1)}` has a default value: secrets must be required "
                                              "(`${VAR:?message}`) or come from a mounted secret")


def check_env_file(path: str, rep: "Report") -> None:
    """Committed plane env files hold non-secret values only."""
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "=" not in line:
                rep.error(f"{path}:{number}", "not a KEY=VALUE line")
                continue
            key, value = line.split("=", 1)
            if key.startswith("export ") or value[:1] in "\"'" and value[:1]:
                rep.warn(f"{path}:{number}", "env files take literal KEY=VALUE (no `export`, no quotes)")
            if SECRET_VAR.search(key) and not key.endswith("_FILE") and value.strip():
                rep.error(f"{path}:{number}", f"`{key}` carries a value: secrets never belong in a committed env file")


def check_tracing(rep: "Report", where: str, env: dict, names: dict) -> None:
    """One stable service name per service; endpoint is a base URL; the OTLP token is a mounted secret."""
    otel = str(env.get("OTEL_SERVICE_NAME") or "")
    plain = str(env.get("SERVICE_NAME") or "")
    if not (otel or env.get("OTEL_EXPORTER_OTLP_ENDPOINT") or env.get("OTEL_TRACES_EXPORTER")):
        return  # service does not export traces
    if not otel:
        rep.warn(where, "tracing endpoint set but no `OTEL_SERVICE_NAME`: the dependency graph needs one stable name per service")
    elif plain and plain != otel:
        rep.warn(where, f"`OTEL_SERVICE_NAME={otel}` differs from `SERVICE_NAME={plain}`: logs, metrics and traces should share one name")
    if otel:
        if otel in names:
            rep.error(where, f"`OTEL_SERVICE_NAME={otel}` is also used by {names[otel]}: two services with one name collapse into a self edge")
        names[otel] = where
    endpoint = str(env.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "")
    if endpoint.rstrip("/").endswith("/v1/traces"):
        rep.warn(where, "`OTEL_EXPORTER_OTLP_ENDPOINT` should be the base URL: the client appends `/v1/traces`")
    if env.get("OTEL_EXPORTER_OTLP_HEADERS") and "authorization" in str(env["OTEL_EXPORTER_OTLP_HEADERS"]).lower():
        rep.error(where, "`OTEL_EXPORTER_OTLP_HEADERS` carries an Authorization value: mount the token and use `OTEL_AUTH_TOKEN_FILE`")
    if env.get("OTEL_AUTH_TOKEN"):
        rep.error(where, "`OTEL_AUTH_TOKEN` carries a value: mount the token as a secret and use `OTEL_AUTH_TOKEN_FILE`")
    arg = str(env.get("OTEL_TRACES_SAMPLER_ARG") or "")
    if arg:
        try:
            if not 0.0 <= float(arg) <= 1.0:
                raise ValueError
        except ValueError:
            rep.error(where, f"`OTEL_TRACES_SAMPLER_ARG={arg}` must be a number within 0..1")
    if str(env.get("TRACING_DETAIL", "")).lower() in ("1", "true", "yes", "on"):
        rep.warn(where, "`TRACING_DETAIL` is on (detailed mode): confirm the sampling ratio suits the span volume")
    if env.get("OTEL_PROPAGATORS") and "tracecontext" not in str(env["OTEL_PROPAGATORS"]):
        rep.warn(where, "`OTEL_PROPAGATORS` lacks `tracecontext`: other services will not continue this trace")


def check_infra(rep: "Report", where: str, env: dict) -> None:
    deps_raw = str(env.get("HEALTH_DEPS") or "")
    declared = {INFRA_ALIASES.get(d, d) for d in re.split(r"[,\s]+", deps_raw.lower()) if d}
    present = {name for name, (prefix, _, _) in INFRA.items() if any(k.startswith(prefix) for k in env)}
    for dep in sorted(declared - set(INFRA)):
        rep.error(where, f"HEALTH_DEPS names unknown infrastructure `{dep}` (known: {', '.join(INFRA)})")
    for dep in sorted(present - declared):
        rep.warn(where, f"uses {dep} variables but HEALTH_DEPS does not list `{dep}`: the start-up gate and "
                        "health check will not wait for it")
    for dep in sorted(declared - present - (declared - set(INFRA))):
        rep.error(where, f"HEALTH_DEPS lists `{dep}` but no {INFRA[dep][0]}* variables are set")
    if present and not declared:
        rep.warn(where, "uses infrastructure but sets no HEALTH_DEPS")
    for dep in sorted(present):
        _, required, secrets = INFRA[dep]
        for var in required:
            if not env.get(var):
                rep.error(where, f"{dep}: `{var}` is required")
        if dep == "kafka" and str(env.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")).startswith("SASL"):
            required_secrets = ["KAFKA_SASL_PASSWORD"]
            if not env.get("KAFKA_SASL_USERNAME"):
                rep.error(where, "kafka: `KAFKA_SASL_USERNAME` is required for SASL")
        else:
            required_secrets = secrets
        for var in required_secrets:
            if not env.get(var) and not env.get(f"{var}_FILE"):
                rep.error(where, f"{dep}: `{var}_FILE` (mounted secret) is required; secrets have no default")
            elif env.get(var) and not env.get(f"{var}_FILE"):
                rep.warn(where, f"{dep}: `{var}` is a plain variable; use `{var}_FILE` with a Swarm secret")
LATEST = re.compile(r"(^|[:/])latest($|@)")


def render(path: str, env_files: list[str], overrides: dict[str, str]) -> dict:
    cmd = ["docker", "compose"]
    for env_file in env_files:
        cmd += ["--env-file", env_file]
    cmd += ["-f", path, "config", "--format", "json", "--no-path-resolution"]
    env = dict(os.environ)
    env.update(overrides)
    try:
        out = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        sys.exit("docker is required to render the Compose file")
    if out.returncode != 0:
        print(f"{path}: cannot render\n{out.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return json.loads(out.stdout)


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def error(self, where: str, msg: str) -> None:
        self.errors += 1
        print(f"ERROR   {where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings += 1
        print(f"WARNING {where}: {msg}")


def is_one_shot(deploy: dict) -> bool:
    restart = (deploy.get("restart_policy") or {}).get("condition")
    return restart == "none" or deploy.get("replicas") == 0


def check_traefik(rep: Report, where: str, svc: dict, routers: dict, services: dict, run_env: str | None) -> bool:
    deploy_labels = (svc.get("deploy") or {}).get("labels") or {}
    top_labels = svc.get("labels") or {}
    if isinstance(deploy_labels, list):
        deploy_labels = dict(item.split("=", 1) for item in deploy_labels if "=" in item)
    if isinstance(top_labels, list):
        top_labels = dict(item.split("=", 1) for item in top_labels if "=" in item)

    if any(k.startswith("traefik.") for k in top_labels):
        rep.error(where, "Traefik labels are service-level `labels:`; the Swarm provider reads `deploy.labels`")
    if "traefik.docker.network" in deploy_labels:
        rep.error(where, "`traefik.docker.network` is the Docker-provider label; use `traefik.swarm.network` in Swarm")

    t = {k: str(v) for k, v in deploy_labels.items() if k.startswith("traefik.")}
    if not t:
        return False
    for key in t:
        if "$" in key:
            rep.error(where, f"label key `{key}` has an unresolved variable: Compose interpolates values, "
                             "not mapping keys; write labels as a list (`- key=value`)")
            break
    if t.get("traefik.enable", "").lower() != "true":
        rep.error(where, 'Traefik labels present but `traefik.enable: "true"` is missing')

    my_routers = {m.group(1) for k in t if (m := re.match(r"traefik\.http\.routers\.([^.]+)\.", k))}
    my_services = {m.group(1) for k in t if (m := re.match(r"traefik\.http\.services\.([^.]+)\.", k))}
    if not my_routers:
        rep.error(where, "no `traefik.http.routers.<name>.rule` label")
    if not my_services:
        rep.error(where, "no `traefik.http.services.<name>.loadbalancer.server.port` label")

    for name in my_routers:
        if f"traefik.http.routers.{name}.rule" not in t:
            rep.error(where, f"router `{name}` has no rule")
        elif "Host(" not in t[f"traefik.http.routers.{name}.rule"] and "PathPrefix(" not in t[f"traefik.http.routers.{name}.rule"]:
            rep.warn(where, f"router `{name}` rule has no Host()/PathPrefix(): it may match everything")
        if f"traefik.http.routers.{name}.entrypoints" not in t:
            rep.warn(where, f"router `{name}` does not name its entrypoint")
        if name in routers:
            rep.error(where, f"router name `{name}` is also used by {routers[name]}: names must be globally unique")
        routers[name] = where
        if run_env and not name.endswith(f"_{run_env}"):
            rep.warn(where, f"router `{name}` is not plane-qualified (expected suffix `_{run_env}`)")
        if "-" in name:
            rep.warn(where, f"router `{name}` uses `-`; the convention is lowercase with underscores")
    for name in my_services:
        port = t.get(f"traefik.http.services.{name}.loadbalancer.server.port")
        if port is None:
            rep.error(where, f"service `{name}` has no loadbalancer.server.port")
        elif not port.isdigit():
            rep.error(where, f"service `{name}` port `{port}` is not a number")
        if name in services:
            rep.error(where, f"Traefik service name `{name}` is also used by {services[name]}")
        services[name] = where
    for k, v in t.items():
        m = re.match(r"traefik\.http\.routers\.([^.]+)\.service$", k)
        if m and v not in my_services:
            rep.warn(where, f"router `{m.group(1)}` points to service `{v}` that this service does not define")

    networks = svc.get("networks") or {}
    net_names = set(networks)
    net_label = t.get("traefik.swarm.network")
    if len(net_names) > 1 and not net_label:
        rep.error(where, "service joins several networks but sets no `traefik.swarm.network`")
    if svc.get("ports"):
        rep.warn(where, "routed service also publishes host ports: route through the proxy instead")
    return True


API_PORT = "3000"


def check_api_contract(rep: Report, where: str, svc: dict, env: dict, run_env: str | None) -> None:
    """The api-contract skill: {service}.{env}.{domain} host, port 3000, ENV_NAME, /healthz."""
    deploy_labels = (svc.get("deploy") or {}).get("labels") or {}
    if isinstance(deploy_labels, list):
        deploy_labels = dict(item.split("=", 1) for item in deploy_labels if "=" in item)
    service_name = str(env.get("SERVICE_NAME") or "")
    env_name = str(env.get("ENV_NAME") or env.get("DEVELOPMENT_ENVIRONMENT") or "")

    if not env_name:
        rep.error(where, "routed service has no `ENV_NAME` (set `ENV_NAME: ${RUN_ENV}`): the env name is part of the host and healthz")
    elif run_env and env_name != run_env:
        rep.warn(where, f"ENV_NAME `{env_name}` differs from RUN_ENV `{run_env}`")
    expected_env = env_name or run_env or ""

    for key, value in deploy_labels.items():
        if re.match(r"traefik\.http\.routers\.[^.]+\.rule$", key):
            for host in re.findall(r"Host\(`([^`]+)`\)", str(value)):
                check_api_host(rep, where, host, service_name, expected_env)
        if re.match(r"traefik\.http\.services\.[^.]+\.loadbalancer\.server\.port$", key) and str(value) != API_PORT:
            rep.error(where, f"Traefik server port is `{value}`: every API listens on {API_PORT}")

    port = env.get("PORT")
    if port is None:
        rep.error(where, f'no `PORT: "{API_PORT}"` in the environment: every API listens on {API_PORT}')
    elif str(port) != API_PORT:
        rep.error(where, f"PORT is `{port}`: every API listens on {API_PORT}")

    path = env.get("HEALTH_APP_PATH")
    if path and str(path) != "/healthz":
        rep.error(where, f"HEALTH_APP_PATH `{path}`: the one health endpoint is /healthz")
    test = " ".join(str(part) for part in ((svc.get("healthcheck") or {}).get("test") or []))
    if re.search(r"/v\d+/healthz|(?<![\w}])/(readyz|health)\b", test):
        rep.error(where, "health check probes a versioned or old health path: use /healthz (health.sh --app does)")


def check_api_host(rep: Report, where: str, host: str, service_name: str, env_name: str) -> None:
    labels = host.split(".")
    if len(labels) < 3:
        rep.error(where, f"host `{host}` is not {{service_name}}.{{env_name}}.{{host}}")
        return
    if service_name and labels[0] != service_name:
        rep.error(where, f"host `{host}`: first label must be the service name `{service_name}` (SERVICE_NAME)")
    if env_name and labels[1] != env_name:
        rep.error(where, f"host `{host}`: second label must be the env name `{env_name}`")


def check_file(path: str, env_files: list[str], overrides: dict[str, str], rep: Report,
               routers: dict, tservices: dict, names: dict) -> None:
    check_raw_defaults(path, rep)
    cfg = render(path, env_files, overrides)
    run_env = overrides.get("RUN_ENV")
    top_secrets = cfg.get("secrets") or {}

    for name, secret in top_secrets.items():
        where = f"{path} secrets.{name}"
        if not secret.get("external"):
            rep.warn(where, "not external: Swarm external secrets are the supported delivery mechanism")
        else:
            real = secret.get("name")
            if not real or real == name:
                rep.error(where, "external secret needs an explicit versioned `name:` (for example `<purpose>_<plane>_v1`)")
            elif not SECRET_NAME.match(real):
                rep.error(where, f"secret name `{real}` has unsupported characters")
            elif not re.search(r"_v\d+$", real):
                rep.warn(where, f"secret name `{real}` has no `_v<generation>` suffix; rotation needs a new generation")

    for name, svc in (cfg.get("services") or {}).items():
        where = f"{path} service `{name}`"
        deploy = svc.get("deploy") or {}
        one_shot = is_one_shot(deploy)

        if "build" in svc:
            rep.warn(where, "`build:` is ignored by `docker stack deploy`; build in CI and deploy an image variable")
        image = svc.get("image", "")
        if not image:
            rep.error(where, "no `image:`")
        elif LATEST.search(image):
            rep.error(where, f"image `{image}` uses `latest`: deploy an immutable tag or digest")

        logging = svc.get("logging") or {}
        opts = logging.get("options") or {}
        if logging.get("driver") in (None, "json-file") and "max-size" not in opts:
            rep.error(where, "no log rotation (`logging` json-file with max-size/max-file)")

        limits = ((deploy.get("resources") or {}).get("limits")) or {}
        if "memory" not in limits:
            rep.error(where, "no `deploy.resources.limits.memory`")
        if "cpus" not in limits:
            rep.warn(where, "no `deploy.resources.limits.cpus`")

        if not one_shot:
            if not svc.get("healthcheck") or svc["healthcheck"].get("disable"):
                rep.error(where, "no health check Swarm can act on")
            elif "start_period" not in svc["healthcheck"]:
                rep.warn(where, "health check has no `start_period` for slow initialisation")
            if not svc.get("stop_grace_period"):
                rep.warn(where, "no `stop_grace_period`: default 10s may cut graceful shutdown short")
            if not deploy.get("update_config"):
                rep.warn(where, "no `deploy.update_config` (parallelism/order/failure_action)")
            elif (deploy["update_config"].get("order") == "start-first"
                  and (deploy.get("replicas") or 1) == 1 and (svc.get("volumes"))):
                rep.warn(where, "start-first with volumes and one replica: check that overlap is safe")
            if "restart_policy" not in deploy:
                rep.warn(where, "no `deploy.restart_policy`")

        env = svc.get("environment") or {}
        if isinstance(env, list):
            env = dict(item.split("=", 1) if "=" in item else (item, None) for item in env)
        mounted = {s if isinstance(s, str) else s.get("source") for s in (svc.get("secrets") or [])}
        mounted_targets = set()
        for s in svc.get("secrets") or []:
            src = s if isinstance(s, str) else s.get("source")
            tgt = src if isinstance(s, str) else (s.get("target") or src)
            mounted_targets.add(tgt if tgt.startswith("/") else f"/run/secrets/{tgt}")
        for s in mounted:
            if s not in top_secrets:
                rep.error(where, f"secret `{s}` is not declared in top-level `secrets:`")
        for key, value in env.items():
            if key.endswith("_FILE") and value:
                if value.startswith("/run/secrets/") and value not in mounted_targets:
                    rep.error(where, f"`{key}={value}` but that secret is not attached to the service")
            elif value and re.search(r"(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)$", key) and not key.endswith("_FILE"):
                rep.warn(where, f"`{key}` carries a literal value: prefer a mounted secret and `{key}_FILE`")
        check_infra(rep, where, env)
        check_tracing(rep, where, env, names)
        if "RUN_ENV" not in env:
            rep.warn(where, "no `RUN_ENV` in the environment")
        if not (env.get("SERVICE_NAME") or env.get("OTEL_SERVICE_NAME")):
            rep.warn(where, "no `SERVICE_NAME`/`OTEL_SERVICE_NAME`: logs, metrics and traces need one logical identity")

        routed = check_traefik(rep, where, svc, routers, tservices, run_env)
        if routed and not svc.get("networks"):
            rep.error(where, "routed service joins no network")
        if routed:
            check_api_contract(rep, where, svc, env, run_env)

        ports = svc.get("ports") or []
        for p in ports:
            if isinstance(p, dict) and p.get("published") and not routed:
                rep.warn(where, f"publishes host port {p.get('published')}: document ownership, firewall and plane routing")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", help="Swarm Compose file(s) of one plane")
    parser.add_argument("--env-file", action="append", default=[], help="deploy/<plane>.env (repeatable)")
    parser.add_argument("--set", action="append", default=[], metavar="VAR=value",
                        help="dummy value for a variable the workflow supplies (RUN_ENV, APP_IMAGE, ...)")
    args = parser.parse_args()

    overrides: dict[str, str] = {}
    for item in args.set:
        if "=" not in item:
            parser.error(f"--set expects VAR=value, got {item!r}")
        key, value = item.split("=", 1)
        overrides[key] = value

    rep = Report()
    for env_file in args.env_file:
        check_env_file(env_file, rep)
    routers: dict[str, str] = {}
    tservices: dict[str, str] = {}
    names: dict[str, str] = {}
    for path in args.files:
        check_file(path, args.env_file, overrides, rep, routers, tservices, names)
    print(f"\n{rep.errors} error(s), {rep.warnings} warning(s)")
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
