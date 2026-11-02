# Swarm Compose contract

The Swarm file (`docker-compose.yaml`) is the deployed contract. `docker stack deploy` ignores
`build:`, `depends_on` ordering, `container_name` and `restart:`; it uses `image:` and `deploy:`.
Start from `assets/templates/docker-compose.yaml`.

## Service identity

| Field | Rule |
|---|---|
| Compose service key | Stable lowercase logical name (`api`, `worker`). After deploy the Swarm service is `<stack>_<key>`; the stack is `<stack>-<plane>`. |
| `SERVICE_NAME` / `OTEL_SERVICE_NAME` | Same logical name for logs, metrics, traces and the service graph. Use `${SERVICE_NAME:-<default>}`. |
| `RUN_ENV` | `${RUN_ENV:?RUN_ENV is required}`: supplied by CI from the plane, never defaulted. |
| `NODE_NAME` | `"{{.Node.Hostname}}"` (Swarm template) when logs/metrics need the host identity. |
| Network alias | Add a stable alias for services other services call (`networks: {ingress-net: {aliases: [example-api]}}`); callers use the alias, not task IPs. |

## Standard block per service

```yaml
x-logging: &logging
  driver: json-file
  options: {max-size: "10m", max-file: "3"}

services:
  api:
    image: ${APP_IMAGE:?APP_IMAGE is required}
    environment: {TZ: UTC, RUN_ENV: "${RUN_ENV:?RUN_ENV is required}", SERVICE_NAME: "${SERVICE_NAME:-example-api}"}
    logging: *logging
    healthcheck: {test: ["CMD", "/app/healthcheck"], interval: 30s, timeout: 10s, start_period: 30s, retries: 3}
    stop_grace_period: 30s
    deploy:
      replicas: 1
      resources: {limits: {cpus: "1.0", memory: 512M}, reservations: {cpus: "0.25", memory: 128M}}
      restart_policy: {condition: any, delay: 5s, max_attempts: 10, window: 300s}
      update_config: {parallelism: 1, delay: 10s, order: stop-first, failure_action: rollback}
      rollback_config: {parallelism: 1, delay: 10s, order: stop-first, failure_action: pause}
```

- **Labels**: write `deploy.labels` as a list (`- key=value`) when a key contains `${RUN_ENV}`; see [Traefik labels](traefik-labels.md).
- **Logging**: log files are unbounded without the cap. Write JSON to stdout/stderr.
- **Resources**: size the memory limit from a measured peak with headroom; software that sizes caches
  from visible memory needs an explicit flag or it is OOM-killed at the limit.
- **Infrastructure**: use the `x-<infra>` variable blocks and `HEALTH_DEPS`; the entrypoint gate waits for
  dependencies and the health check keeps checking them ([infra health](infra-health.md)). Keep
  `start_period` >= `HEALTH_WAIT_SECONDS`.
- **Health check**: stable liveness (plus dependency reachability when failing should restart the task).
  Give slow starts a realistic `start_period`. Put complex checks in an executable file in the image;
  avoid shell substitutions (`$VAR`) in `test:` when the file is rendered twice (escape as `$$`).
- **Update order**: `start-first` for stateless services that tolerate overlap (check ports/volumes);
  `stop-first` for single-writer, stateful or duplicate-consumer services, with `replicas: 1`.
- **One-shot jobs** (migrations): `restart_policy: {condition: none}`; run through a completion gate
  (separate migration stack/step) before dependent services, never as a parallel matrix entry.

## Environment and configuration

- Non-secret values: `${NAME:-default}` for tunables, `${NAME:?message}` for required values.
  Plane values live in `deploy/<plane>.env` as literal `KEY=VALUE` (no `export`, quotes, shell
  evaluation or inline comments) and must not set variables the workflow owns (`RUN_ENV`, `DOCKER_*`,
  `GITHUB_*`, `PATH` and similar).
- Secrets: external, versioned, explicitly named, mounted as files and read through `*_FILE`
  variables ([secrets](secrets.md)); never a default value. Keep the top-level `secrets:` block plain: no YAML anchors, one
  explicit `name:` per entry, so CI preflight can read it.
- Telemetry: `OTEL_EXPORTER_OTLP_ENDPOINT` points at the plane's collector on the monitoring overlay;
  `OTEL_AUTH_TOKEN_FILE`/headers come from a mounted secret, never a committed value.

## Networks

Join only the overlays a service needs: the ingress overlay (if routed or if it must resolve aliases
there), the monitoring overlay (telemetry), and any datastore overlay. Declare them `external: true`
with plane-qualified names:

```yaml
networks:
  ingress-net: {external: true, name: ingress-${RUN_ENV:?RUN_ENV is required}}
  monitoring-net: {external: true, name: monitoring-${RUN_ENV:?RUN_ENV is required}}
```

Exposure: do not use `ports:` for services reached through the reverse proxy. Publish a host port
only with a documented ownership, firewall and plane-routing plan.

## Placement and state

Combine a broad constraint (`node.role == worker`) with a service-specific node label
(`node.labels.<purpose> == true`); create and verify the label before deploy. Use plane-qualified named
volumes for persistent data and document ownership, backup/restore, single-writer constraint and what
happens when the task reschedules (named volumes are host-local).

## Several services in one file

Share defaults through `x-` anchors **outside** the `secrets:` block, with per-service overrides
(`<<: *base`). Give each service its own command, resources, replicas and secret list. Keep services
that must roll out independently in separate stacks/files ([multi-service](multi-service-pipelines.md)).

## Local file

`docker-compose.local.yaml` keeps the same service keys, commands and env semantics but may add
`build:`, `pull_policy: build`, `env_file: .env`, published ports and development credentials. Use
Docker-provider Traefik labels there (see [Traefik labels](traefik-labels.md)); a local render does
not prove the Swarm provider discovers the service.

## Example usage

- “Write the Swarm compose file for an API plus a worker that share one image.”
- “Add logging, limits and update policy to this compose file.”
