# TypeScript / JavaScript (Node)

Template: `assets/templates/typescript/serviceTracing.ts`. Tests and demo: `smoke.ts` (`npx tsx smoke.ts`).
Tested with Node 22, `@opentelemetry/sdk-trace-node` / `sdk-trace-base` 2.12, `exporter-trace-otlp-proto` 0.223
(`tsc --noEmit` clean). Browser tracing has different transport/CORS needs and must never receive the collector token.

```bash
npm i @opentelemetry/api @opentelemetry/context-async-hooks @opentelemetry/core @opentelemetry/resources \
  @opentelemetry/sdk-trace-base @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-proto
```

## Wire it

```ts
import { ServiceTracing } from './serviceTracing.js';
export const tracing = ServiceTracing.fromEnv();      // OTEL_SERVICE_NAME|SERVICE_NAME, RUN_ENV, OTEL_* (references/env.md)
process.on('SIGTERM', async () => { await tracing.shutdown(); process.exit(0); });
```

Load this module (and any `@opentelemetry/instrumentation-*` registration) **before** the framework, database
and Kafka modules, so monkey-patching attaches: `node --import ./dist/tracing-start.js dist/main.js` (ESM) or
`--require` (CommonJS). Verify the startup order for the installed versions. Do not add a second SDK or context manager.

## Boundary spans (dependency mode)

| Hop | Use |
|---|---|
| Inbound HTTP (Express, Fastify, Nest) | `@opentelemetry/instrumentation-http` + the framework instrumentation (or `@opentelemetry/auto-instrumentations-node`), or `tracing.serverSpan(route, req.headers, fn)` |
| Outbound HTTP | `instrumentation-http` / `-undici`, or `tracing.clientSpan('GET /pricing', 'pricing', (headers) => fetch(url, { headers }))` |
| PostgreSQL / Redis | `instrumentation-pg`, `-ioredis`, `-redis`; otherwise `tracing.peerSpan('postgres', 'select orders', fn)` |
| ClickHouse, S3/RustFS | `peerSpan('clickhouse', 'insert trades', fn)`, `peerSpan('s3', 'put object', fn)` |
| Kafka (`kafkajs`) | `instrumentation-kafkajs`, or `producerSpan(topic, (h) => producer.send({ topic, messages: [{ value, headers: h }] }))` and `consumerSpan(topic, message.headers, fn)` (Buffer header values are decoded) |

## Rules and pitfalls

- Every helper runs your function **inside** the span (`context.with`), so awaited work and callbacks see the
  active span. Starting a span alone does not make it active.
- Async spans end after the awaited work, not at the first `await`; the helpers end them in `finally`.
- Detailed mode: `await tracing.detailSpan('compute', fn)` is a no-op wrapper unless `TRACING_DETAIL=true`.
- Log correlation (pino): `const [traceId, spanId] = ServiceTracing.ids()`; log both or neither (a `mixin`).
- Shutdown flush is bounded by the exporter timeout; a hard `process.exit()` before `await shutdown()` loses spans.
- The OTLP/HTTP proto exporter streams the body (`Transfer-Encoding: chunked`): a test receiver must read chunked bodies.

Source: [JavaScript instrumentation](https://opentelemetry.io/docs/languages/js/instrumentation/).

## Example usage

- “Trace this Fastify service so its outgoing calls and Kafka messages show in the graph.”
