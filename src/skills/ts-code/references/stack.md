# Stack

| Concern | Choice | Notes |
|---|---|---|
| runtime | Node 22 LTS | matches `deployment-setup`'s `node:22-bookworm-slim` |
| package manager | npm (lockfile committed) | keep pnpm where a repo already uses it; never mix lockfiles |
| language | TypeScript 6.0 | pinned below 6.1 because `typescript-eslint` 8 supports `<6.1`; move to 7 when it does |
| UI | React 19 | function components and hooks only |
| SSR framework | Next.js 16, App Router | `output: "standalone"` |
| SPA build | Vite 8 + `@vitejs/plugin-react` | |
| server state | `@tanstack/react-query` 5 (Vite apps) | Next.js: fetch in server components |
| API types | `openapi-typescript` 7 via `npx` (`npm run api:types`) | run on demand; it is not a dependency (its TypeScript peer is older) |
| lint | ESLint 10 flat config + `typescript-eslint` strict + `react-hooks` | `no-console` is an error |
| format | Prettier, 100 columns | |
| unit tests | Vitest 5 (+ Testing Library and jsdom for components) | |
| e2e | Playwright 1.64 | against the production build (`vite preview`, `next start`) |

Pin exact versions in `package.json`, commit the lockfile, and use `npm ci` in CI and Docker.
Upgrade with one PR per major version, with the template's full check list green.

`tsconfig.json` essentials: `strict`, `noUncheckedIndexedAccess`, `noFallthroughCasesInSwitch`,
`isolatedModules`, `moduleResolution: "bundler"`, `skipLibCheck`. Node-only files (Vite and Playwright
configs, e2e tests) get their own `tsconfig.node.json` with `types: ["node"]`, so browser code can't
use `process`.
