/**
 * Service tracing for the dependency graph (see references/typescript.md and references/env.md).
 * Copy this file into the service, build one ServiceTracing at startup, and shut it down on exit:
 *
 *   const tracing = ServiceTracing.fromEnv();          // SERVICE_NAME, RUN_ENV, OTEL_* ... (references/env.md)
 *   process.on('SIGTERM', async () => { await tracing.shutdown(); process.exit(0); });
 *
 * Default (dependency) mode records boundary spans only. Auto-instrumentation (http, undici, pg, ioredis,
 * kafkajs ...) covers most hops; the helpers below cover the rest and keep peer names stable. Each helper runs
 * `fn` inside the span (so async work stays in context), ends the span on every path and records failures:
 *
 *   await tracing.serverSpan('POST /orders', req.headers, async () => {          // inbound hop (SERVER)
 *     await tracing.peerSpan('postgres', 'insert orders', () => db.query(...));  // datastore (CLIENT)
 *     await tracing.clientSpan('GET /pricing', 'pricing', (headers) => fetch(url, { headers }));
 *     await tracing.producerSpan('orders.created', (headers) => producer.send({ ..., headers }));
 *   });
 *   await tracing.consumerSpan('orders.created', message.headers, async () => { ... });   // CONSUMER
 *
 * detailSpan() is a no-op unless TRACING_DETAIL=true (detailed mode on request). An empty endpoint,
 * OTEL_TRACES_EXPORTER=none or OTEL_SDK_DISABLED=true keeps every call working without a collector.
 * Load this module before the instrumented libraries (node --import ./dist/tracing-start.js ...).
 */
import { readFileSync } from 'node:fs';
import { hostname } from 'node:os';
import { pid } from 'node:process';
import {
  context, propagation, trace, SpanKind, SpanStatusCode, ROOT_CONTEXT, INVALID_SPAN_CONTEXT,
  type Attributes, type Span, type Context,
} from '@opentelemetry/api';
import { AsyncLocalStorageContextManager } from '@opentelemetry/context-async-hooks';
import {
  CompositePropagator, W3CBaggagePropagator, W3CTraceContextPropagator,
} from '@opentelemetry/core';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-proto';
import { resourceFromAttributes } from '@opentelemetry/resources';
import {
  AlwaysOffSampler, AlwaysOnSampler, BatchSpanProcessor, ParentBasedSampler, TraceIdRatioBasedSampler,
  type Sampler, type SpanExporter, type SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';

export interface Options {
  /** OTEL_SERVICE_NAME, else SERVICE_NAME: one stable logical name per service. */
  service: string;
  /** DEPLOYMENT_ENVIRONMENT, else RUN_ENV, else ENV_NAME, else "local". */
  environment?: string;
  node?: string;
  version?: string;
  /** OTLP/HTTP base URL; /v1/traces is appended. Empty = no export. */
  endpoint?: string;
  token?: string;
  timeoutMs?: number;
  sampler?: string;
  samplerArg?: number;
  detail?: boolean;
  resourceAttributes?: Attributes;
}

type Carrier = Record<string, string | string[] | Buffer | undefined>;
type Peer = { key: string; value: string; kind: SpanKind; prefix: string };

const PEERS: Record<string, Peer> = {
  postgres: { key: 'db.system', value: 'postgresql', kind: SpanKind.CLIENT, prefix: 'POSTGRES' },
  redis: { key: 'db.system', value: 'redis', kind: SpanKind.CLIENT, prefix: 'REDIS' },
  clickhouse: { key: 'db.system', value: 'clickhouse', kind: SpanKind.CLIENT, prefix: 'CLICKHOUSE' },
  kafka: { key: 'messaging.system', value: 'kafka', kind: SpanKind.PRODUCER, prefix: 'KAFKA' },
  s3: { key: 'rpc.system', value: 'aws-api', kind: SpanKind.CLIENT, prefix: 'S3' },
};

const env = (name: string, fallback = ''): string => (process.env[name] ?? fallback).trim();
const flag = (name: string): boolean => ['1', 'true', 'yes', 'on'].includes(env(name).toLowerCase());
const secret = (name: string): string => env(name) || (env(`${name}_FILE`) ? readFileSync(env(`${name}_FILE`), 'utf8').trim() : '');

let contextManagerInstalled = false;

export class ServiceTracing {
  readonly provider: NodeTracerProvider;
  private readonly tracer;

  constructor(readonly options: Options, exporter?: SpanExporter, processor?: SpanProcessor) {
    const o = options;
    const node = o.node || hostname();
    const resource = resourceFromAttributes({
      'service.name': o.service,
      'deployment.environment': o.environment ?? 'local',
      'deployment.environment.name': o.environment ?? 'local',
      'host.name': node,
      'service.instance.id': `${node}-${pid}`,
      ...(o.version ? { 'service.version': o.version } : {}),
      ...o.resourceAttributes,
    });
    const exp = exporter ?? (o.endpoint && env('OTEL_TRACES_EXPORTER', 'otlp') !== 'none' && !flag('OTEL_SDK_DISABLED')
      ? new OTLPTraceExporter({
          url: `${o.endpoint.replace(/\/$/, '')}/v1/traces`,
          headers: o.token ? { Authorization: `Bearer ${o.token}` } : {},
          timeoutMillis: o.timeoutMs ?? 5000,
        })
      : undefined);
    // Batch export off the request path; queue/batch sizes come from the OTEL_BSP_* variables.
    this.provider = new NodeTracerProvider({
      resource,
      sampler: newSampler(o),
      spanProcessors: exp ? [processor ?? new BatchSpanProcessor(exp)] : [],
    });
    // The context manager and propagator are process-global: install them once (Node's AsyncLocalStorage).
    if (!contextManagerInstalled) {
      context.setGlobalContextManager(new AsyncLocalStorageContextManager().enable());
      propagation.setGlobalPropagator(new CompositePropagator({
        propagators: [new W3CTraceContextPropagator(), new W3CBaggagePropagator()],
      }));
      contextManagerInstalled = true;
    }
    this.tracer = this.provider.getTracer('service-tracing');
  }

  static fromEnv(exporter?: SpanExporter): ServiceTracing {
    const service = env('OTEL_SERVICE_NAME') || env('SERVICE_NAME');
    if (!service) throw new Error('SERVICE_NAME (or OTEL_SERVICE_NAME) is required: one stable logical name per service');
    const extra = Object.fromEntries(env('OTEL_RESOURCE_ATTRIBUTES').split(',').filter((i) => i.includes('=')).map((i) => i.split('=', 2) as [string, string]));
    const version = env('SERVICE_VERSION') || (extra['service.version'] as string | undefined);
    delete extra['service.version'];
    return new ServiceTracing({
      service,
      environment: env('DEPLOYMENT_ENVIRONMENT') || env('RUN_ENV') || env('ENV_NAME') || 'local',
      node: env('NODE_NAME'),
      version,
      endpoint: env('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT').replace(/\/v1\/traces$/, '') || env('OTEL_EXPORTER_OTLP_ENDPOINT'),
      token: secret('OTEL_AUTH_TOKEN'),
      timeoutMs: Number(env('OTEL_EXPORTER_OTLP_TIMEOUT', '5000')),
      sampler: env('OTEL_TRACES_SAMPLER', 'parentbased_traceidratio'),
      samplerArg: Number(env('OTEL_TRACES_SAMPLER_ARG', '1.0')),
      detail: flag('TRACING_DETAIL'),
      resourceAttributes: extra,
    }, exporter);
  }

  // ---- boundary spans (dependency mode) --------------------------------------------------------------------
  /** Inbound request: continue the caller's trace from `headers` (missing/invalid -> a new trace). */
  serverSpan<T>(name: string, headers: Carrier | undefined, fn: (span: Span) => Promise<T> | T, attrs: Attributes = {}): Promise<T> {
    return this.run(name, SpanKind.SERVER, attrs, fn, extract(headers));
  }

  /** Outbound call to another service: `fn` receives the headers to send (traceparent...). */
  clientSpan<T>(name: string, peer: string, fn: (headers: Record<string, string>, span: Span) => Promise<T> | T, attrs: Attributes = {}): Promise<T> {
    return this.run(name, SpanKind.CLIENT, { 'peer.service': peer, ...attrs }, (span) => fn(inject(), span));
  }

  /** Datastore/broker/object store without its own instrumentation: a span with a stable peer identity.
   *  Host/port come from the infrastructure variables (POSTGRES_HOST, KAFKA_BOOTSTRAP_SERVERS, S3_ENDPOINT ...). */
  peerSpan<T>(kind: string, operation: string, fn: (span: Span) => Promise<T> | T, attrs: Attributes = {}): Promise<T> {
    const p = PEERS[kind] ?? { key: 'rpc.system', value: kind, kind: SpanKind.CLIENT, prefix: kind.toUpperCase() };
    const [host, port] = peerAddress(kind, p.prefix);
    const attributes: Attributes = {
      'peer.service': env(`PEER_SERVICE_${kind.toUpperCase()}`) || kind, [p.key]: p.value, ...attrs,
      ...(host ? { 'server.address': host } : {}), ...(port ? { 'server.port': port } : {}),
    };
    return this.run(`${kind} ${operation}`, p.kind, attributes, fn);
  }

  /** Publish to a queue/stream: `fn` receives the message headers that carry the context. */
  producerSpan<T>(destination: string, fn: (headers: Record<string, string>, span: Span) => Promise<T> | T, system = 'kafka', attrs: Attributes = {}): Promise<T> {
    return this.run(`${destination} publish`, SpanKind.PRODUCER, {
      'messaging.system': system, 'messaging.destination.name': destination, 'messaging.operation': 'publish',
      'peer.service': env(`PEER_SERVICE_${system.toUpperCase()}`) || system, ...attrs,
    }, (span) => fn(inject(), span));
  }

  /** Handle one message: parent = the producer's context from the message headers (Buffers are decoded). */
  consumerSpan<T>(destination: string, headers: Carrier | undefined, fn: (span: Span) => Promise<T> | T, system = 'kafka', attrs: Attributes = {}): Promise<T> {
    return this.run(`${destination} process`, SpanKind.CONSUMER, {
      'messaging.system': system, 'messaging.destination.name': destination, 'messaging.operation': 'process', ...attrs,
    }, fn, extract(headers));
  }

  /** Internal span for detailed mode; runs `fn` untraced unless TRACING_DETAIL=true. */
  detailSpan<T>(name: string, fn: (span: Span) => Promise<T> | T, attrs: Attributes = {}): Promise<T> {
    if (!this.options.detail) return Promise.resolve(fn(trace.wrapSpanContext(INVALID_SPAN_CONTEXT)));
    return this.run(name, SpanKind.INTERNAL, attrs, fn);
  }

  /** (traceId, spanId) of the active valid span as hex, else ['', ''] - for log correlation. */
  static ids(): [string, string] {
    const sc = trace.getActiveSpan()?.spanContext();
    return sc && trace.isSpanContextValid(sc) ? [sc.traceId, sc.spanId] : ['', ''];
  }

  async shutdown(): Promise<void> {
    await this.provider.shutdown(); // flushes the batch processor within its export timeout
  }

  private async run<T>(name: string, kind: SpanKind, attributes: Attributes, fn: (span: Span) => Promise<T> | T, parent?: Context): Promise<T> {
    const span = this.tracer.startSpan(name, { kind, attributes }, parent ?? context.active());
    try {
      return await context.with(trace.setSpan(parent ?? context.active(), span), () => fn(span));
    } catch (err) {
      // Error type only: messages can carry payloads or credentials.
      span.setStatus({ code: SpanStatusCode.ERROR, message: err instanceof Error ? err.constructor.name : typeof err });
      span.recordException({ name: err instanceof Error ? err.name : 'Error' });
      throw err;
    } finally {
      span.end();
    }
  }
}

function inject(): Record<string, string> {
  const carrier: Record<string, string> = {};
  propagation.inject(context.active(), carrier);
  return carrier;
}

function extract(headers: Carrier | undefined): Context {
  const flat: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers ?? {})) {
    if (v === undefined) continue;
    flat[k.toLowerCase()] = Buffer.isBuffer(v) ? v.toString() : Array.isArray(v) ? String(v[0]) : String(v);
  }
  return propagation.extract(ROOT_CONTEXT, flat);
}

function newSampler(o: Options): Sampler {
  const name = (o.sampler ?? 'parentbased_traceidratio').toLowerCase();
  if (name === 'always_on') return new AlwaysOnSampler();
  if (name === 'always_off') return new AlwaysOffSampler();
  if (name === 'parentbased_always_on') return new ParentBasedSampler({ root: new AlwaysOnSampler() });
  if (name === 'parentbased_always_off') return new ParentBasedSampler({ root: new AlwaysOffSampler() });
  const ratio = o.samplerArg ?? 1;
  if (!(ratio >= 0 && ratio <= 1)) throw new Error(`OTEL_TRACES_SAMPLER_ARG must be within 0..1, got ${ratio}`);
  const base = new TraceIdRatioBasedSampler(ratio);
  return name === 'traceidratio' ? base : new ParentBasedSampler({ root: base }); // default: honour the upstream decision
}

function peerAddress(kind: string, prefix: string): [string, number] {
  if (kind === 'kafka') {
    const first = env('KAFKA_BOOTSTRAP_SERVERS').split(',')[0]?.trim() ?? '';
    const i = first.lastIndexOf(':');
    return i > 0 ? [first.slice(0, i), Number(first.slice(i + 1)) || 0] : [first, 0];
  }
  if (kind === 's3') {
    try {
      const u = new URL(env('S3_ENDPOINT'));
      return [u.hostname, Number(u.port) || (u.protocol === 'https:' ? 443 : 80)];
    } catch {
      return ['', 0];
    }
  }
  const defaults: Record<string, number> = { postgres: 5432, redis: 6379, clickhouse: 9000 };
  return [env(`${prefix}_HOST`), Number(env(`${prefix}_PORT`)) || defaults[kind] || 0];
}
