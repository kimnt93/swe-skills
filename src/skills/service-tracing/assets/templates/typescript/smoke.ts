/**
 * Smoke test and demo for serviceTracing.ts.
 *   npx tsx smoke.ts        assertions with in-memory exporters (no collector needed)
 *   npx tsx smoke.ts demo   export one demo request to OTEL_EXPORTER_OTLP_ENDPOINT (see references/verification.md):
 *     SERVICE_NAME=api TRACEPARENT=<from upstream> DEMO_CALL=worker DEMO_DB=postgres npx tsx smoke.ts demo
 *     prints the traceparent it sends downstream.
 */
import assert from 'node:assert/strict';
import { SpanKind } from '@opentelemetry/api';
import { InMemorySpanExporter, SimpleSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { ServiceTracing } from './serviceTracing.js';

function make(service: string, detail = false) {
  const exporter = new InMemorySpanExporter();
  const tracing = new ServiceTracing({ service, environment: 'test', node: 'n1', version: '1.2.3', detail }, exporter, new SimpleSpanProcessor(exporter));
  return { tracing, spans: () => exporter.getFinishedSpans() };
}

async function test() {
  process.env.POSTGRES_HOST = 'db.internal';
  process.env.KAFKA_BOOTSTRAP_SERVERS = 'k1:9092,k2:9092';
  const web = make('web');
  const api = make('api');

  // web CLIENT -> headers -> api SERVER: one trace, parent = the client span
  await web.tracing.serverSpan('GET /home', undefined, () =>
    web.tracing.clientSpan('GET /orders', 'api', (headers) =>
      api.tracing.serverSpan('GET /orders', headers, () => api.tracing.peerSpan('postgres', 'select orders', () => undefined))));
  const client = web.spans().find((s) => s.kind === SpanKind.CLIENT)!;
  const server = api.spans().find((s) => s.kind === SpanKind.SERVER && s.name === 'GET /orders')!;
  assert.equal(server.spanContext().traceId, client.spanContext().traceId);
  assert.equal(server.parentSpanContext?.spanId, client.spanContext().spanId, "server span must be a child of the caller's client span");
  assert.equal(server.resource.attributes['service.name'], 'api');
  assert.equal(client.resource.attributes['deployment.environment'], 'test');
  assert.equal(client.resource.attributes['service.version'], '1.2.3');

  // peer identity for an uninstrumented datastore
  const db = api.spans().find((s) => s.kind === SpanKind.CLIENT)!;
  assert.equal(db.name, 'postgres select orders');
  assert.deepEqual(
    ['peer.service', 'db.system', 'server.address', 'server.port'].map((k) => db.attributes[k]),
    ['postgres', 'postgresql', 'db.internal', 5432]);

  // messaging: producer -> headers -> consumer (Buffer header values as kafkajs delivers them)
  let msgHeaders: Record<string, string> = {};
  await web.tracing.producerSpan('orders.created', (h) => { msgHeaders = h; });
  const asBuffers = Object.fromEntries(Object.entries(msgHeaders).map(([k, v]) => [k, Buffer.from(v)]));
  await api.tracing.consumerSpan('orders.created', asBuffers, () => undefined);
  const producer = web.spans().find((s) => s.kind === SpanKind.PRODUCER)!;
  const consumer = api.spans().find((s) => s.kind === SpanKind.CONSUMER)!;
  assert.equal(consumer.parentSpanContext?.spanId, producer.spanContext().spanId);
  assert.equal(consumer.spanContext().traceId, producer.spanContext().traceId);

  // missing or invalid context starts a valid new trace
  const before = api.spans().length;
  for (const bad of [undefined, {}, { traceparent: 'garbage' }, { traceparent: `00-${'0'.repeat(32)}-${'0'.repeat(16)}-01` }]) {
    await api.tracing.serverSpan('GET /bad', bad, (span) => assert.ok(span.spanContext().traceId !== '0'.repeat(32)));
  }
  assert.equal(api.spans().slice(before).filter((s) => !s.parentSpanContext).length, 4);

  // dependency mode records no internal spans; detailed mode does
  await api.tracing.serverSpan('GET /x', undefined, () => api.tracing.detailSpan('compute', () => undefined));
  assert.ok(!api.spans().some((s) => s.kind === SpanKind.INTERNAL));
  const detailed = make('api', true);
  await detailed.tracing.serverSpan('GET /x', undefined, () => detailed.tracing.detailSpan('compute', () => undefined));
  assert.equal(detailed.spans().filter((s) => s.kind === SpanKind.INTERNAL).length, 1);

  // failures: error status carries the type, never the message; the span still ends
  await assert.rejects(api.tracing.serverSpan('POST /fail', undefined, () => { throw new Error('secret-token-123'); }));
  const failed = api.spans().find((s) => s.name === 'POST /fail')!;
  assert.equal(failed.status.code, 2);
  assert.ok(!(failed.status.message ?? '').includes('secret'));

  // context survives awaits: the span is active inside async work
  await api.tracing.serverSpan('GET /async', undefined, async () => {
    await new Promise((r) => setTimeout(r, 5));
    assert.notDeepEqual(ServiceTracing.ids(), ['', '']);
  });
  assert.deepEqual(ServiceTracing.ids(), ['', ''], 'no active span outside the operation');

  // kafka peer: first bootstrap server
  await api.tracing.peerSpan('kafka', 'send', () => undefined);
  const k = api.spans().at(-1)!;
  assert.equal(k.kind, SpanKind.PRODUCER);
  assert.equal(k.attributes['server.address'], 'k1');
  console.log('ok');
}

async function demo() {
  const tracing = ServiceTracing.fromEnv();
  const inbound = process.env.TRACEPARENT ? { traceparent: process.env.TRACEPARENT } : undefined;
  await tracing.serverSpan('GET /demo', inbound, async () => {
    if (process.env.DEMO_DB) await tracing.peerSpan(process.env.DEMO_DB, 'query', () => undefined);
    if (process.env.DEMO_CALL) await tracing.clientSpan('GET /demo', process.env.DEMO_CALL, (h) => console.log(h.traceparent));
  });
  await tracing.shutdown();
}

await (process.argv[2] === 'demo' ? demo() : test());
