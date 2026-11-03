---
name: deployment-setup
description: Write or review the deployment files for a service - Dockerfile, Swarm docker-compose.yaml, local compose file, plane env files and CI caller workflows - including service names, Traefik routing labels, networks, secrets, health checks, resources and rollback. Use for adding a service to staging/production, wiring CI deployment for one or many Compose files and images, or auditing an existing setup. Discover project-specific names, hosts and workflow inputs from the target repository and its deployment documentation.
metadata:
  group: platform
  summary: "Dockerfile, Swarm and local compose, Traefik labels, secrets and CI callers"
  version: "1.1"
---

# Deployment setup

Author, or review, the files that take a service from source to a running Swarm/Compose
deployment: image, runtime contract, ingress, secrets and CI. Keep concrete service names,
hostnames, networks and workflow settings in the project being configured; templates here use
placeholders such as `example-api` that must be replaced.

## 1. Discover the contract

Read the project's agent instructions, deployment notes, existing Dockerfile/Compose files,
workflows, `deploy/*.env` and the platform documentation it points to ([sources](references/sources.md)).
Reuse an existing file's conventions before introducing new ones. Establish:

- planes/environments and their triggers (for example staging on `main`, production on a release);
- the reusable deploy workflow and its **current** inputs (read the workflow, do not assume);
- ingress: which services are routed through the reverse proxy, the plane network it uses,
  entrypoint names, the hostname shape and the router-name registry, if any;
- hosts and placement: which nodes may run the service, labels, networks, storage ownership and ingress addresses, from the project's inventory and focused
  read-only checks, never from runner names ([host mapping](references/hosts-and-services.md));
- standalone Compose vs Swarm, one image vs several, one stack vs independent stacks
  ([layouts](references/compose-and-ci.md), [multi-service](references/multi-service-pipelines.md)).

If the repository has no deployment files yet, copy the closest template from
[assets/templates](assets/templates) and adapt it; do not copy another project's values.

## 2. Write the files

| File | Guidance | Starting point |
|---|---|---|
| `Dockerfile` | [Dockerfile rules](references/dockerfile.md): pinned stages, non-root, signals, health gate entrypoint | `assets/templates/Dockerfile.{go,python,node,rust}`; frontends `Dockerfile.nextjs` (standalone server) and `Dockerfile.vite` + `nginx.spa.conf` (static SPA), both on port 3000 (see the `ts-code` skill's deploy reference) |
| `docker-compose.yaml` (Swarm contract) | [Swarm Compose](references/swarm-compose.md): identity, env, secrets, networks, placement, logging, resources, update/rollback | `assets/templates/docker-compose.yaml` |
| Traefik labels | [Traefik labels](references/traefik-labels.md): `deploy.labels`, host `{service_name}.{env_name}.{host}`, port 3000, unique router/service names, network, local vs Swarm provider | in the Swarm template |
| `docker-compose.local.yaml` | same service names and commands, `build:`, local ports, Docker-provider labels | `assets/templates/docker-compose.local.yaml` |
| `deploy/<plane>.env` | literal `KEY=VALUE` non-secret plane values; no quotes, `export`, comments or secrets | `assets/templates/deploy/*.env` |
| `.github/workflows/*.yml` | [CI workflows](references/ci-workflows.md): stg/prod callers, validation, permissions, triggers | `assets/templates/workflows/*.yml` |
| Infrastructure (PostgreSQL, Redis, ClickHouse, Kafka, S3/RustFS) | [infra variables and health gate](references/infra-health.md): detailed `<INFRA>_HOST/PORT/...` variables, required passwords with no default, `HEALTH_DEPS`, start-up wait | `x-<infra>` blocks in the Swarm/local templates, `.env.example`, `scripts/health.sh`, `docker-compose.infra.local.yaml` |
| Secrets | [secrets](references/secrets.md): external versioned names, `_FILE` mounts, per-consumer attachment | in the Swarm template |

Rules that apply to every file:

- **API contract** for every HTTP service ([api-contract](../api-contract/SKILL.md)): the process listens on port `3000`
  (`PORT: "3000"`, `EXPOSE 3000`, Traefik server port `3000`); the host is `{service_name}.{env_name}.{host}`
  (`orders-api.stg.@DOMAIN@`) built from `SERVICE_NAME` and `RUN_ENV`; `ENV_NAME: ${RUN_ENV}` is always set; the
  container health check probes `/healthz`; `/docs` and `/v1` share the one router.
- One logical **service name** per deployable. Use it for the Compose service, `SERVICE_NAME`,
  `OTEL_SERVICE_NAME`, the network alias, the Traefik router/service stem and the log/metric/trace
  identity, so every signal and route resolves to the same name.
- Fail closed: every value whose absence would deploy the wrong target uses `${VAR:?message}`.
  Qualify plane-specific resources (networks, secrets, routers, volumes) with `${RUN_ENV}`.
- Deploy an immutable image variable (for example `${APP_IMAGE:?}`), never `latest`.
- Every Swarm service declares logging limits, CPU/memory limits, a health check that Swarm can act
  on, `stop_grace_period`, restart policy and update/rollback policy.
- A service that uses infrastructure always ships the start-up gate and health check
  (`scripts/health.sh --wait`, `HEALTH_DEPS`) so it never starts, fails and restarts before its database,
  cache, broker or object store is up. Passwords and keys are required and never have a default value.
- Routed services get Traefik labels under `deploy.labels`; non-routed services get none and join
  only the networks they need. Never publish a database/admin port to make a probe convenient.
- Secrets are attached only to the services that read them. Commit names, never values.
- Stateful or single-writer services use one replica and stop-first updates unless overlap is proven safe.

## 3. Verify

Run the checker on every affected file and plane, then render with the intended runtime:

```bash
python3 scripts/check_deploy.py docker-compose.yaml --env-file deploy/stg.env --set RUN_ENV=stg --set APP_IMAGE=example.invalid/app@sha256:$(printf '0%.0s' {1..64})
docker stack config -c docker-compose.yaml   # with the same dummy variables
```

The checker renders with dummy values and reports missing logging/resources/health checks, an API host that is not
`{SERVICE_NAME}.{ENV_NAME}.{domain}`, a port other than 3000, a missing `ENV_NAME`, a probe of `/v1/healthz` or `/readyz` (health is `/healthz`),
Swarm-vs-Docker label mix-ups, duplicate or malformed Traefik routers, secrets without explicit
names, `_FILE` variables with no mounted secret, secrets with a default or inside an env file,
incomplete infrastructure variables or `HEALTH_DEPS` that disagree with them, `latest` images and
published ports on routed services. It does not replace the runtime validator: Compose rendering alone does not establish
Swarm compatibility. Also check workflow syntax and inputs, image coverage (one image variable per
build component), secret references, placement labels and migration gates; build the image and run
it as the final user; test any helper script you ship (run `health.sh` against real or local
infrastructure, including a dependency that is down and a missing password).

For an authorized rollout, verify the exact revision and image digest, running tasks, update
completion, the route (`Host` header hit, unknown host, backend failure) and application behavior.
Distinguish configuration intent, observed infrastructure and functional acceptance. Report checks
performed and missing evidence; never claim an unverified rollout. A setup request covers repository
changes and local verification; execute a rollout only when the user authorized that target.

## Language stacks

The service code that this deployment contract serves comes from the language skills: Go ([go-code](../go-code/SKILL.md)), Python
([py-code](../py-code/SKILL.md)) and Rust, including Python+Rust packages ([rust-code](../rust-code/SKILL.md)). Build notes: Go with Kafka needs
`CGO_ENABLED=1` and `libstdc++` in the runtime image; Rust with `rdkafka` needs `cmake` in the build stage; a maturin package builds its wheel in a
Rust+Python builder stage and installs it into a slim runtime. Database schema changes ship as a one-shot migration job: see the
[db-migrations](../db-migrations/SKILL.md) skill; in Dockerfiles split `RUN` chains with `\`, one command per line.

## Example usage

- “Use $deployment-setup to add a Dockerfile, Swarm compose file and staging/production CI for this service.”
- “Use $deployment-setup to add Traefik routing labels to the API service.”
- “Use $deployment-setup to wire PostgreSQL, Redis and Kafka variables and the start-up health gate into this service.”
- “Use $deployment-setup to deploy several services from this repository with a shared image.”
- “Use $deployment-setup to review secrets, host placement and rollback for these stacks.”
