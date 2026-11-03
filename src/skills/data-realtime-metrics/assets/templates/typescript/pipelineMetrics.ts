/**
 * Pipeline metrics: the shared stream_pipeline_* OTLP set (see references/metric-contract.md).
 *
 * Copy this file into the service, build one PipelineMetrics at startup, and call the
 * recording methods from the hot path:
 *
 *   const metrics = new PipelineMetrics({ service: process.env.SERVICE_NAME!, environment: 'stg', endpoint });
 *   metrics.received();                         // every message that arrives
 *   metrics.dropped();                          // ... that is deliberately not forwarded
 *   metrics.published({ bytes, latencyMs });    // after the ack / write
 *   await metrics.shutdown();                   // flushes the last export
 *
 * Needs @opentelemetry/api, sdk-metrics, resources and exporter-metrics-otlp-proto (2.x SDK line).
 */
import { hostname } from 'node:os';
import { metrics as otelApi } from '@opentelemetry/api';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-proto';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';

const LATENCY_BUCKETS_MS = [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000];

export interface PipelineMetricsOptions {
  /** The pipeline name, e.g. feed-ws-transform. */
  service: string;
  environment: string;
  /** OTEL_EXPORTER_OTLP_ENDPOINT; empty keeps every call a no-op. /v1/metrics is appended. */
  endpoint?: string;
  token?: string;
  node?: string;
  exportIntervalMs?: number;
  /** Adds the feed metrics: connection_active, reconnects_total, in_flight. */
  ingestion?: boolean;
}

export class PipelineMetrics {
  private readonly provider?: MeterProvider;
  private readonly messages;
  private readonly bytes;
  private readonly latency;
  private readonly errors;
  private readonly reconnects?;
  private running = 0;
  private connected = 0;
  private kafkaOk = 0;
  private lastInputMs = 0;
  private readonly startedAt = Date.now() / 1000;
  private backlog?: () => number;
  private inFlight?: () => number;

  constructor(o: PipelineMetricsOptions) {
    if (o.endpoint) {
      const exporter = new OTLPMetricExporter({
        // `url` is used exactly as given: include the signal path.
        url: `${o.endpoint.replace(/\/$/, '')}/v1/metrics`,
        headers: o.token ? { Authorization: `Bearer ${o.token}` } : {},
      });
      this.provider = new MeterProvider({
        resource: resourceFromAttributes({
          'service.name': o.service,
          'service.namespace': 'platform',
          'deployment.environment': o.environment,
          'host.name': o.node ?? hostname(),
        }),
        readers: [new PeriodicExportingMetricReader({ exporter, exportIntervalMillis: o.exportIntervalMs ?? 10_000 })],
      });
    }
    // Without an endpoint the global API returns a no-op meter.
    const meter = this.provider ? this.provider.getMeter(o.service) : otelApi.getMeter(o.service);
    this.messages = meter.createCounter('stream_pipeline_messages_total');
    this.bytes = meter.createCounter('stream_pipeline_payload_bytes_total');
    // No unit on the histogram: a unit makes Mimir rename it ..._ms_milliseconds_bucket.
    this.latency = meter.createHistogram('stream_pipeline_latency_ms', {
      advice: { explicitBucketBoundaries: LATENCY_BUCKETS_MS },
    });
    this.errors = meter.createCounter('stream_pipeline_errors_total');
    const restarts = meter.createCounter('stream_pipeline_restarts_total');
    const gauge = (name: string, read: () => number | undefined) =>
      meter.createObservableGauge(name).addCallback((result) => {
        const value = read();
        if (value !== undefined) result.observe(value);
      });
    gauge('stream_pipeline_running', () => this.running);
    gauge('stream_pipeline_kafka_healthy', () => this.kafkaOk);
    gauge('stream_pipeline_start_timestamp_seconds', () => this.startedAt);
    gauge('stream_pipeline_last_message_age_ms', () => (this.lastInputMs ? Math.max(0, Date.now() - this.lastInputMs) : undefined));
    gauge('stream_pipeline_latest_event_timestamp_seconds', () => (this.lastInputMs ? this.lastInputMs / 1000 : undefined));
    gauge('stream_pipeline_consumer_lag', () => this.backlog?.());
    if (o.ingestion) {
      this.reconnects = meter.createCounter('stream_pipeline_reconnects_total');
      gauge('stream_pipeline_connection_active', () => this.connected);
      gauge('stream_pipeline_in_flight', () => this.inFlight?.());
    }
    // Process start: counts a restart and marks the pipeline running.
    restarts.add(1);
    this.running = 1;
  }

  async shutdown(): Promise<void> {
    this.running = 0;
    this.connected = 0;
    if (this.provider) {
      await this.provider.forceFlush();
      await this.provider.shutdown();
    }
  }

  /** Messages waiting: Kafka lag for consumers, queue depth for ingestion. */
  setBacklog(source: () => number): void { this.backlog = source; }
  /** Ingestion: messages handed to the Kafka client and not yet acknowledged. */
  setInFlight(source: () => number): void { this.inFlight = source; }
  setKafkaHealthy(healthy: boolean): void { this.kafkaOk = healthy ? 1 : 0; }
  /** Ingestion: whether the feed connection is up. */
  setConnected(connected: boolean): void { this.connected = connected ? 1 : 0; }
  reconnect(): void { this.reconnects?.add(1); }

  /**
   * Every arrival. `live: false` (heartbeats, replays) counts it without refreshing the
   * freshness gauges. `eventMs` is the Kafka timestamp or event time, default now.
   */
  received(opts: { count?: number; live?: boolean; eventMs?: number } = {}): void {
    this.messages.add(opts.count ?? 1, { status: 'received' });
    if (opts.live ?? true) this.lastInputMs = Math.max(this.lastInputMs, opts.eventMs ?? Date.now());
  }

  /** Arrived but deliberately not forwarded; also call received() for them. */
  dropped(count = 1): void { this.messages.add(count, { status: 'dropped' }); }

  /** Forwarded: Kafka ack, sink write, or handled successfully. */
  published(opts: { count?: number; bytes?: number; latencyMs?: number } = {}): void {
    this.messages.add(opts.count ?? 1, { status: 'published' });
    if (opts.bytes) this.bytes.add(opts.bytes);
    if (opts.latencyMs !== undefined) this.latency.record(Math.max(0, opts.latencyMs));
  }

  error(count = 1): void { this.errors.add(count); }
}
