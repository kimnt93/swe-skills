# TypeScript / JavaScript

Template: `assets/templates/typescript/pipelineMetrics.ts`. Smoke test: `smoke.ts`;
dependency versions: `package.json` (all in the same folder). Plain JavaScript: drop the types.

Tested with Node 22 and the 2.x SDK line: `@opentelemetry/sdk-metrics` 2.12,
`@opentelemetry/resources` 2.12, `@opentelemetry/exporter-metrics-otlp-proto` 0.223.

```bash
npm i @opentelemetry/api @opentelemetry/sdk-metrics @opentelemetry/resources @opentelemetry/exporter-metrics-otlp-proto
```

## Wire it

```ts
import { readFileSync } from 'node:fs';
import { PipelineMetrics } from './pipelineMetrics.js';

const file = process.env.OTEL_AUTH_TOKEN_FILE;
const metrics = new PipelineMetrics({
  service: process.env.SERVICE_NAME!,               // e.g. ssi-ws-v3-transform
  environment: process.env.DEPLOYMENT_ENVIRONMENT ?? 'local',
  endpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
  token: file ? readFileSync(file, 'utf8').trim() : process.env.OTEL_AUTH_TOKEN,
  exportIntervalMs: Number(process.env.OTEL_METRIC_EXPORT_INTERVAL_MS ?? 10_000),
  ingestion: false,                                 // true for feed -> Kafka services
});
process.on('SIGTERM', async () => { await metrics.shutdown(); process.exit(0); });
```

Kafka consumer with kafkajs:

```ts
await consumer.run({ eachMessage: async ({ message }) => {
  const ts = Number(message.timestamp);              // Kafka timestamp, ms
  metrics.received({ eventMs: ts });
  if (!route(message)) { metrics.dropped(); return; }
  await write(message);                              // throws on failure
  metrics.published({ bytes: message.value?.length, latencyMs: Date.now() - ts });
}});
```

Producer (ingestion or transform): `await producer.send(...)` resolves on the broker ack, so
`published({ bytes, latencyMs: Date.now() - arrivedAt })` goes right after it; `catch` ->
`metrics.error()`.

Lag probe (interval, 15 s): `admin.fetchTopicOffsets(topic)` (high watermarks) minus
`admin.fetchOffsets({ groupId, topics: [topic] })` (committed), summed, then
`metrics.setBacklog(() => lag)`. `setKafkaHealthy(true)` when the call succeeds.
For websocket feeds: `ws.on('open')` -> `setConnected(true)`, `on('close')` ->
`setConnected(false)` and `reconnect()` per retry; `setBacklog(() => queue.length)`.

## Gotchas

- `OTLPMetricExporter({ url })` is used exactly as given: the template appends `/v1/metrics`.
- Use the `-proto` exporter (protobuf). `exporter-metrics-otlp-http` sends JSON, which also
  works with `scripts/otlp_check.py` but is larger; do not mix packages of different major lines.
- Histogram buckets come from `advice.explicitBucketBoundaries` (API >= 1.7); no unit.
- The exporter streams the request with chunked transfer encoding; a custom receiver or proxy
  must support it (the checker does).
- Always `await shutdown()` before exiting; `process.exit()` without it drops the last export.
- ESM + TypeScript `nodenext`: import local files with the `.js` extension.

## Verify

```bash
python3 scripts/otlp_check.py --role ingestion --wait 30 &
cd assets/templates/typescript && npm i && npx tsx smoke.ts http://127.0.0.1:4318 ingestion
```
