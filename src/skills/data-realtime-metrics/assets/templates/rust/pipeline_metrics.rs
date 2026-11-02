//! Pipeline metrics: the shared `stream_pipeline_*` OTLP set (see references/metric-contract.md).
//!
//! Add this file as a module, build one `PipelineMetrics` at startup, and call the recording
//! methods from the hot path:
//!
//! ```ignore
//! let m = PipelineMetrics::new(Options {
//!     service: name,
//!     environment: "stg".into(),
//!     endpoint: url,
//!     ..Default::default()
//! })?;
//!
//! // Every message that arrives.
//! m.received(true);
//! // ... that is deliberately not forwarded.
//! m.dropped();
//! // After the ack / write.
//! m.published(payload.len() as u64, elapsed);
//! // Flushes the last export.
//! m.shutdown();
//! ```

use std::collections::HashMap;
use std::sync::atomic::{AtomicI64, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use opentelemetry::metrics::{Counter, Histogram, MeterProvider as _};
use opentelemetry::KeyValue;
use opentelemetry_otlp::{MetricExporter, Protocol, WithExportConfig, WithHttpConfig};
use opentelemetry_sdk::metrics::{PeriodicReader, SdkMeterProvider};
use opentelemetry_sdk::Resource;

const LATENCY_BUCKETS_MS: [f64; 15] = [
    1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0, 30000.0,
    60000.0,
];

type Source = Box<dyn Fn() -> i64 + Send + Sync>;

#[derive(Default)]
pub struct Options {
    /// The pipeline name, e.g. `ssi-ws-v3-transform`.
    pub service: String,
    pub environment: String,
    /// OTEL_EXPORTER_OTLP_ENDPOINT; empty keeps every call a no-op. `/v1/metrics` is appended.
    pub endpoint: String,
    pub token: String,
    /// Defaults to the hostname.
    pub node: Option<String>,
    /// Defaults to 10 s.
    pub export_interval: Option<Duration>,
    /// Adds the feed metrics: connection_active, reconnects_total, in_flight.
    pub ingestion: bool,
}

#[derive(Default)]
struct State {
    running: AtomicI64,
    connected: AtomicI64,
    kafka_ok: AtomicI64,
    last_input_ms: AtomicU64,
    backlog: Mutex<Option<Source>>,
    in_flight: Mutex<Option<Source>>,
}

pub struct PipelineMetrics {
    provider: Option<SdkMeterProvider>,
    messages: Counter<u64>,
    bytes: Counter<u64>,
    latency: Histogram<f64>,
    errors: Counter<u64>,
    reconnects: Option<Counter<u64>>,
    state: Arc<State>,
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

impl PipelineMetrics {
    pub fn new(o: Options) -> Result<Self, Box<dyn std::error::Error>> {
        let provider = if o.endpoint.is_empty() {
            None
        } else {
            let mut headers = HashMap::new();
            if !o.token.is_empty() {
                headers.insert("Authorization".to_string(), format!("Bearer {}", o.token));
            }
            let exporter = MetricExporter::builder()
                .with_http()
                .with_protocol(Protocol::HttpBinary)
                // The endpoint is used as given: include the signal path.
                .with_endpoint(format!("{}/v1/metrics", o.endpoint.trim_end_matches('/')))
                .with_headers(headers)
                .build()?;
            let reader = PeriodicReader::builder(exporter)
                .with_interval(o.export_interval.unwrap_or(Duration::from_secs(10)))
                .build();
            let node = o
                .node
                .clone()
                .unwrap_or_else(|| gethostname::gethostname().to_string_lossy().into_owned());
            let resource = Resource::builder()
                .with_attributes([
                    KeyValue::new("service.name", o.service.clone()),
                    KeyValue::new("service.namespace", "xnoquant"),
                    KeyValue::new("deployment.environment", o.environment.clone()),
                    KeyValue::new("host.name", node),
                ])
                .build();
            Some(
                SdkMeterProvider::builder()
                    .with_reader(reader)
                    .with_resource(resource)
                    .build(),
            )
        };
        // Without an endpoint the global API hands out a no-op meter.
        let meter = match &provider {
            Some(p) => p.meter("pipeline"),
            None => opentelemetry::global::meter("pipeline"),
        };
        let state = Arc::new(State::default());
        let messages = meter.u64_counter("stream_pipeline_messages_total").build();
        let bytes = meter
            .u64_counter("stream_pipeline_payload_bytes_total")
            .build();
        // No unit on the histogram: a unit makes Mimir rename it ..._ms_milliseconds_bucket.
        let latency = meter
            .f64_histogram("stream_pipeline_latency_ms")
            .with_boundaries(LATENCY_BUCKETS_MS.to_vec())
            .build();
        let errors = meter.u64_counter("stream_pipeline_errors_total").build();
        let restarts = meter.u64_counter("stream_pipeline_restarts_total").build();

        let started_at = now_ms() as f64 / 1000.0;
        let gauge_i64 =
            |name: &'static str, read: Arc<dyn Fn(&State) -> Option<i64> + Send + Sync>| {
                let state = state.clone();
                meter
                    .i64_observable_gauge(name)
                    .with_callback(move |obs| {
                        if let Some(v) = read(&state) {
                            obs.observe(v, &[]);
                        }
                    })
                    .build();
            };
        let gauge_f64 =
            |name: &'static str, read: Arc<dyn Fn(&State) -> Option<f64> + Send + Sync>| {
                let state = state.clone();
                meter
                    .f64_observable_gauge(name)
                    .with_callback(move |obs| {
                        if let Some(v) = read(&state) {
                            obs.observe(v, &[]);
                        }
                    })
                    .build();
            };
        gauge_i64(
            "stream_pipeline_running",
            Arc::new(|s| Some(s.running.load(Ordering::Relaxed))),
        );
        gauge_i64(
            "stream_pipeline_kafka_healthy",
            Arc::new(|s| Some(s.kafka_ok.load(Ordering::Relaxed))),
        );
        gauge_f64(
            "stream_pipeline_start_timestamp_seconds",
            Arc::new(move |_| Some(started_at)),
        );
        gauge_f64(
            "stream_pipeline_last_message_age_ms",
            Arc::new(|s| {
                let last = s.last_input_ms.load(Ordering::Relaxed);
                (last > 0).then(|| now_ms().saturating_sub(last) as f64)
            }),
        );
        gauge_f64(
            "stream_pipeline_latest_event_timestamp_seconds",
            Arc::new(|s| {
                let last = s.last_input_ms.load(Ordering::Relaxed);
                (last > 0).then(|| last as f64 / 1000.0)
            }),
        );
        gauge_i64(
            "stream_pipeline_consumer_lag",
            Arc::new(|s| s.backlog.lock().unwrap().as_ref().map(|f| f())),
        );
        let mut reconnects = None;
        if o.ingestion {
            reconnects = Some(
                meter
                    .u64_counter("stream_pipeline_reconnects_total")
                    .build(),
            );
            gauge_i64(
                "stream_pipeline_connection_active",
                Arc::new(|s| Some(s.connected.load(Ordering::Relaxed))),
            );
            gauge_i64(
                "stream_pipeline_in_flight",
                Arc::new(|s| s.in_flight.lock().unwrap().as_ref().map(|f| f())),
            );
        }
        // Process start: counts a restart and marks the pipeline running.
        restarts.add(1, &[]);
        state.running.store(1, Ordering::Relaxed);
        Ok(Self {
            provider,
            messages,
            bytes,
            latency,
            errors,
            reconnects,
            state,
        })
    }

    /// Reports running=0 and flushes the final export.
    pub fn shutdown(&self) {
        self.state.running.store(0, Ordering::Relaxed);
        self.state.connected.store(0, Ordering::Relaxed);
        if let Some(p) = &self.provider {
            let _ = p.force_flush();
            let _ = p.shutdown();
        }
    }

    /// Messages waiting: Kafka lag for consumers, queue depth for ingestion.
    pub fn set_backlog(&self, source: impl Fn() -> i64 + Send + Sync + 'static) {
        *self.state.backlog.lock().unwrap() = Some(Box::new(source));
    }

    /// Ingestion: messages handed to the Kafka client and not yet acknowledged.
    pub fn set_in_flight(&self, source: impl Fn() -> i64 + Send + Sync + 'static) {
        *self.state.in_flight.lock().unwrap() = Some(Box::new(source));
    }

    pub fn set_kafka_healthy(&self, healthy: bool) {
        self.state.kafka_ok.store(healthy as i64, Ordering::Relaxed);
    }

    /// Ingestion: whether the feed connection is up.
    pub fn set_connected(&self, connected: bool) {
        self.state
            .connected
            .store(connected as i64, Ordering::Relaxed);
    }

    pub fn reconnect(&self) {
        if let Some(c) = &self.reconnects {
            c.add(1, &[]);
        }
    }

    /// Every arrival. `live = false` (heartbeats, replays) counts it without refreshing the
    /// freshness gauges.
    pub fn received(&self, live: bool) {
        self.messages.add(1, &[KeyValue::new("status", "received")]);
        if live {
            self.state
                .last_input_ms
                .fetch_max(now_ms(), Ordering::Relaxed);
        }
    }

    /// Arrived but deliberately not forwarded; also call `received` for it.
    pub fn dropped(&self) {
        self.messages.add(1, &[KeyValue::new("status", "dropped")]);
    }

    /// Forwarded: Kafka ack, sink write, or handled successfully; latency runs from arrival.
    pub fn published(&self, bytes: u64, latency: Duration) {
        self.messages
            .add(1, &[KeyValue::new("status", "published")]);
        self.bytes.add(bytes, &[]);
        self.latency.record(latency.as_secs_f64() * 1000.0, &[]);
    }

    pub fn error(&self) {
        self.errors.add(1, &[]);
    }
}
