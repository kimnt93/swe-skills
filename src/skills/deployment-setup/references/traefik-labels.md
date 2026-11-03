# Traefik routing labels

Add labels only to services that must be reached through the reverse proxy. The proxy reads labels
from every stack in one flat namespace, so names must be globally unique. Discover the project's
entrypoint names, plane network names, hostname shape and any router-name registry before writing
labels; register new names there first when a registry exists.

## Host: `{service_name}.{env_name}.{host}`

Every routed API uses one host built from its service name, its env name and the public domain
(`orders-api.stg.@DOMAIN@`) and listens on port **3000**. One router serves `/docs`, `/v1` and
`/v2`, so there is a single `Host()` rule and no `PathPrefix`. The service-name variable is the same one
that fills `SERVICE_NAME`. The full contract is the [api-contract](../../api-contract/SKILL.md) skill
and `scripts/check_deploy.py` enforces the host shape, the port and `ENV_NAME`.

## HTTP service (Swarm provider)

Swarm labels go under `deploy.labels` (service labels, not container labels). Write them as a
**list** (`- key=value`): Compose interpolates values but not mapping keys, so `key: value` labels
leave a literal `${RUN_ENV}` in the router name and every plane gets the same (colliding) router.

```yaml
services:
  api:
    networks: [ingress-net, monitoring-net]
    deploy:
      labels:
        - traefik.enable=true
        - traefik.swarm.network=ingress-${RUN_ENV:?RUN_ENV is required}
        - traefik.http.routers.example_api_${RUN_ENV}.rule=Host(`${API_SERVICE_NAME:-example-api}.${RUN_ENV}.${PUBLIC_DOMAIN:?PUBLIC_DOMAIN is required}`)
        - traefik.http.routers.example_api_${RUN_ENV}.entrypoints=web
        - traefik.http.routers.example_api_${RUN_ENV}.service=example_api_${RUN_ENV}
        - traefik.http.services.example_api_${RUN_ENV}.loadbalancer.server.port=3000
```

| Label | Rule |
|---|---|
| `traefik.enable` | `"true"` opts in; discovery is normally `exposedByDefault=false`. |
| `traefik.swarm.network` | The overlay the proxy reaches the backend on; must be in the service's `networks` and the proxy must be on it too. Required when the service joins several networks, otherwise the proxy may pick an unreachable IP. |
| Router name | `<service>_<purpose>_<plane>` (`example_api_stg`): lowercase, underscores, **plane interpolated** so one file yields distinct routers per plane. Unique cluster-wide; two services both naming a router `api` collide silently. |
| `rule` | `Host(...)` built from `<service_name>.<env_name>.<host>` (`orders-api.stg.@DOMAIN@`). Put the domain in a plane env variable with `${VAR:?}`; never hard-code it. No `PathPrefix`: one host per service. |
| `entrypoints` | The project's existing HTTP entrypoint name (private/public). Do not invent one. |
| `loadbalancer.server.port` | The **container** port the process listens on: always `3000`. Verify from a task on the same overlay. |
| `.service` | Name the backend explicitly when a router and service stem differ or when reusing a service. |

Backticks in `Host(...)` need no escaping in a list item. If you must use the map form, write the plane
literally per file; never interpolate inside a key. Confirm with `docker stack config` that the rendered
router names contain the plane.

## Variations

- **Several routers to one backend** (aliases, path prefixes): one `services.<name>` label, multiple
  `routers.<name>.service: <name>`.
- **Middlewares** (strip prefix, auth, rate limit, headers): declare under
  `traefik.http.middlewares.<name>...`, attach with `routers.<r>.middlewares: <name>`; middleware
  names are also cluster-wide unique. Never put credentials in labels: labels are visible to anyone
  who can inspect the service.
- **gRPC/h2c backends**: `loadbalancer.server.scheme: h2c`, and a router on the entrypoint that
  accepts HTTP/2. Check the proxy's entrypoint contract.
- **Health-aware routing**: `loadbalancer.healthcheck.path`/`interval` only when the endpoint is
  unauthenticated and cheap; it supplements, not replaces, the Swarm `healthcheck`.
- **Public exposure**: requires an explicit opt-in label defined by the platform; joining an overlay or
  defining a private router never makes a service public. Follow the project's public-ingress contract.
- **Raw TCP** (databases, brokers): needs a proxy entrypoint, an `HostSNI(`*`)` router and a host/plane
  port mapping in the gateway repository; it is not a label-only change. Protocols that advertise their
  own address (Kafka) additionally need a client-reachable advertised address.

## Swarm vs local (Docker provider)

| Aspect | Swarm | Local compose |
|---|---|---|
| Label location | `deploy.labels` | service-level `labels:` |
| Network label | `traefik.swarm.network` | `traefik.docker.network` |
| Discovery proof | proxy dashboard shows router, service resolves | local only; not proof of Swarm |

Do not copy a provider-specific network label between files without converting it. A
`traefik.docker.network` under `deploy.labels` (or service-level labels in a Swarm file) is silently
ignored by the Swarm provider.

## Verify

1. `scripts/check_deploy.py` on each plane: required labels present, names unique and plane-qualified,
   port numeric, no unresolved `${...}` in label keys, network label set, labels under `deploy.labels`.
2. `docker stack config` renders every `${VAR:?}`.
3. After an authorized rollout, test: the intended `Host` header returns the service; an unknown host
   returns the proxy's 404 (not another service); backend failure gives 502/503, not 404;
   authenticated and unauthenticated behavior if the service enforces auth.
4. A 404 usually means no router matched; 502/503 means the router matched but the backend is
   unreachable, on the wrong network or unhealthy. Check, in order: task state, proxy dashboard,
   rendered labels on the live service, shared overlay membership, backend alias and port.

## Example usage

- “Expose the API behind the gateway for staging and production.”
- “Why does the proxy return 404 for this service?”
