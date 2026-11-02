# Dockerfile rules

Start from the closest template in `assets/templates/Dockerfile.*`; keep the target project's
existing base images, package mirror and user conventions when it already has a Dockerfile.

## Required properties

| Property | Rule |
|---|---|
| Pinned inputs | Every upstream image/tool version is an `ARG` (`ARG GO_IMAGE=golang:1.26-bookworm`); prefer a digest for stronger reproducibility. Never `latest`. |
| Stages | Separate `build` and runtime stages. Copy only runtime artifacts into the final stage. |
| Dependencies | Copy the lockfile first and use a deterministic install (`go mod download`, `uv sync --locked`, `npm ci`, `cargo fetch --locked`) so the layer caches. Configure a private package mirror before the first install when the project requires one. |
| User | Run as a documented non-root UID/GID (for example 10001 or 65532). `chown` every runtime-writable path explicitly. |
| Secrets | No credentials in `ARG`, `ENV`, package-manager URLs or layers. Use build secret mounts (`RUN --mount=type=secret`) for private dependencies. |
| Entrypoint | Exec form. A shell entrypoint must end in `exec "$@"` so the real process gets `SIGTERM`. Services with infrastructure use the gate: `ENTRYPOINT ["/app/scripts/health.sh","--wait","--","/app/service"]` ([infra health](infra-health.md)). |
| Shutdown | Process stops within `stop_grace_period` and exits meaningfully; test graceful and forced stop. |
| Health | Ship `scripts/health.sh` (bash only; no `curl`/`wget`/client tools) for the start-up gate and the Compose `healthcheck`; the runtime image needs `bash`. Distroless: use an app subcommand instead. |
| Context | Add a `.dockerignore` (`.git`, `.env*`, `node_modules`, `target`, data, caches). A secret in the build context can leak into a layer. |
| Timezone/locale | Default `TZ=UTC` unless the application needs otherwise. |

## One image, several processes

Build several binaries/entrypoints into one image and select the process with `command:` or
`entrypoint:` per Compose service. Use this when services share code and a release cadence. Use one
Dockerfile per component (named `Dockerfile.<component>` or `<component>/Dockerfile`) when
dependencies, base images or release cadence differ; map each to its own image variable
([multi-service](multi-service-pipelines.md)).

## Runtime base choice

| Runtime | Base | Note |
|---|---|---|
| Static Go (`CGO_ENABLED=0`) | `gcr.io/distroless/static:nonroot` or `scratch` + CA bundle | No shell: health probe must be an app subcommand. |
| Go with cgo (for example librdkafka) | `debian:bookworm-slim` + `ca-certificates libstdc++6` | Match the libc/lib versions of the build stage. |
| Python | `python:<minor>-slim-<distro>` with a venv copied from the build stage | Set `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`; install native libs only at runtime what wheels need. |
| Node | `node:<lts>-slim` | `NODE_ENV=production`, `npm ci --omit=dev`; copy built output only. |
| Rust | `debian:bookworm-slim` or distroless `cc` | Build with `--locked --release`; strip. |

## Verify

`docker build` with the same build args CI passes (`build_args`, build network); run the image as
the final user; check the process runs as non-root, writable paths work, `docker stop` exits within
the grace period, the health probe passes and fails correctly (dependency down), and the log output
is the project's expected format. Record what cannot be reproduced locally (private mirrors,
host-only networks).

## Example usage

- “Write a production Dockerfile for this Go service with a cgo dependency.”
- “Review this Dockerfile for secrets, non-root user and signal handling.”

## Frontends

- **Next.js** (`Dockerfile.nextjs`): `npm ci`, `next build` with `output: "standalone"`, then the runtime
  stage copies `.next/standalone`, `.next/static` and `public` and runs `node server.js` as `node`
  on port 3000. `/healthz` is the app's own route handler.
- **Vite SPA** (`Dockerfile.vite` + `nginx.spa.conf`): `npm ci`, `vite build`, a static `healthz.json`
  written at build, served by `nginxinc/nginx-unprivileged` on port 3000 with SPA fallback, immutable
  caching for `/assets/` and `no-store` for `index.html` and `/healthz`.
- Public build-time values (`NEXT_PUBLIC_*`, `VITE_*`) are build args per environment; server-only
  values and `*_FILE` secrets come at run time.
