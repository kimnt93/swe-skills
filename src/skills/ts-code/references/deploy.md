# Deploy

| App | Image | Health |
|---|---|---|
| Next.js | [`Dockerfile.nextjs`](../../deployment-setup/assets/templates/Dockerfile.nextjs) (`deployment-setup`): `npm ci`, `next build`, run `.next/standalone/server.js` as `node` on port 3000 | `/healthz` (the template's route) |
| Vite SPA | [`Dockerfile.vite`](../../deployment-setup/assets/templates/Dockerfile.vite) (`deployment-setup`): `npm ci`, `vite build`, served by unprivileged nginx on port 3000 with SPA fallback | `/healthz` (a static JSON written at build) |

- `VITE_*` and `NEXT_PUBLIC_*` values are compiled in at build: pass them as build args per
  environment, or serve a small runtime `config.json` if one image must serve several environments.
- Server-only Next.js values (`API_BASE_URL`, secrets) come from the environment at run time, secrets
  through `*_FILE` like every service.
- Traefik routes `{service_name}.{env_name}.<domain>` to port 3000, as for APIs.
- Cache: hashed assets `immutable` for a year; `index.html` and `/healthz` `no-store`.
