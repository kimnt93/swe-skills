# TypeScript / JavaScript (pino)

Template: `assets/templates/typescript/serviceLogging.ts`. Smoke test: `smoke.ts`; dependency
versions: `package.json` (same folder). Plain JavaScript: drop the types. Library:
[pino](https://github.com/pinojs/pino). Tested with Node 22, pino 10.4, `@opentelemetry/api` 1.9.

```bash
npm i pino @opentelemetry/api
```

## Use

```ts
import { configureFromEnv, getLogger } from './serviceLogging.js';

configureFromEnv();                                   // SERVICE_NAME, DEVELOPMENT_ENVIRONMENT|ENV_NAME, NODE_NAME, LOG_LEVEL
const log = getLogger();                              // logger = "root"
log.info({ messages_received: 361234, channel_depth: 0 }, 'message statistics');
getLogger('api.request').warn({ request_id: rid, duration_ms: 1250.5 }, 'slow request');
log.error({ error: err, table: 'trades' }, 'sink write failed');   // error, error_type, stack
```

pino's call shape is `(fields, message)`. Pass an `Error` under the key `error` (or as the first
argument): the template writes `error` (message), `error_type`, and `stack` for error/fatal.
`getLogger(name)` returns a child with `logger = name`; create it once per component.

Docker: set `NODE_NAME` (Swarm `{{.Node.Hostname}}`); the template falls back to the hostname.

## What the template configures

- pino's numeric `level` becomes the label (`info`, `warn`, ...); `msg` becomes `message`;
- `time` is replaced by an ISO string with nine fractional digits: JavaScript has millisecond
  clocks, so the extra digits come from `process.hrtime.bigint()` anchored to the wall clock
  (re-anchored if the clock steps);
- the identity fields are pino `base` values; `pid` and `hostname` are dropped;
- a `mixin` adds `caller` (first stack frame outside the template and pino, relative to the
  nearest `package.json` directory and prefixed with its name), `trace_id`/`span_id` from the
  active OpenTelemetry span, and the error fields.

## Gotchas

- Computing `caller` captures a stack per line (microseconds to tens of microseconds). Log
  per operation; set `LOG_CALLER=false` only for a hot path you cannot change.
- TypeScript run through `tsx` or compiled: run compiled code with `node --enable-source-maps`
  so `caller` shows the `.ts` line instead of the `dist/*.js` line.
- Trace ids need a registered context manager (for example `NodeTracerProvider().register()`);
  without an active span no ids are written.
- ESM + `nodenext`: import local files with the `.js` extension.
- Do not use `console.log` for diagnostics in services.

## Verify

```bash
cd assets/templates/typescript && npm i && npm i -D @opentelemetry/sdk-trace-node tsx typescript @types/node
SERVICE_NAME=feed-ws ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug npx tsx smoke.ts \
  | python3 ../../../scripts/logcheck.py --service feed-ws --env local --node docker-host-1 --require-trace
```
