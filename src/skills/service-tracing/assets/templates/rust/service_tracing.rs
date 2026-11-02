//! Service tracing for the dependency graph (see references/rust.md and references/env.md).
//! Add this file as a module and build one `Tracing` at startup; shut it down on exit:
//!
//! ```ignore
//! // Reads SERVICE_NAME, RUN_ENV, OTEL_* ... (references/env.md).
//! let tracing = Tracing::from_env()?;
//! // ... run ...
//! tracing.shutdown();
//! ```
//!
//! Default (dependency) mode records boundary spans only. Framework/driver instrumentation covers
//! most hops; the helpers below cover the rest and keep peer names stable. Each `*_context` helper
//! starts a span and returns the `Context` that holds it. Run sync work with `cx.clone().attach()`;
//! run async work with `fut.with_context(cx.clone())` (never hold an entered guard across
//! `.await`). Then call `tracing.finish(&cx, err)` exactly once on every path.
//!
//! ```ignore
//! // Inbound (SERVER).
//! let carrier = Carrier::from_headers(req.headers());
//! let cx = tracing.server_context("POST /orders", &carrier);
//!
//! // Datastore (CLIENT).
//! let db = tracing.peer_context(&cx, "postgres", "insert orders");
//! tracing.finish(&db, None);
//!
//! // Outbound call: `out` holds the traceparent to send.
//! let mut out = Carrier::default();
//! let call = tracing.client_context(&cx, "GET /pricing", "pricing", &mut out);
//! ```
//!
//! `detail_context` returns `None` unless TRACING_DETAIL=true (detailed mode on request). An empty
//! endpoint, OTEL_TRACES_EXPORTER=none or OTEL_SDK_DISABLED=true keeps every call working without a
//! collector.

use std::collections::HashMap;
use std::fmt::Display;
use std::time::Duration;

use opentelemetry::global;
use opentelemetry::propagation::{
    Extractor, Injector, TextMapCompositePropagator, TextMapPropagator,
};
use opentelemetry::trace::{SpanKind, Status, TraceContextExt, Tracer, TracerProvider as _};
use opentelemetry::{Context, KeyValue};
use opentelemetry_otlp::{
    Protocol, SpanExporter as OtlpExporter, WithExportConfig, WithHttpConfig,
};
use opentelemetry_sdk::propagation::{BaggagePropagator, TraceContextPropagator};
use opentelemetry_sdk::trace::{
    BatchSpanProcessor, Sampler, SdkTracer, SdkTracerProvider, SimpleSpanProcessor, SpanExporter,
};
use opentelemetry_sdk::Resource;

/// Header/metadata carrier (HTTP headers, Kafka headers, task payload metadata).
#[derive(Default, Clone, Debug)]
pub struct Carrier(pub HashMap<String, String>);

impl Carrier {
    pub fn from_pairs<K: AsRef<str>, V: AsRef<[u8]>>(
        pairs: impl IntoIterator<Item = (K, V)>,
    ) -> Self {
        Carrier(
            pairs
                .into_iter()
                .map(|(k, v)| {
                    (
                        k.as_ref().to_lowercase(),
                        String::from_utf8_lossy(v.as_ref()).into_owned(),
                    )
                })
                .collect(),
        )
    }
}
impl Extractor for Carrier {
    fn get(&self, key: &str) -> Option<&str> {
        self.0.get(&key.to_lowercase()).map(String::as_str)
    }
    fn keys(&self) -> Vec<&str> {
        self.0.keys().map(String::as_str).collect()
    }
}
impl Injector for Carrier {
    fn set(&mut self, key: &str, value: String) {
        self.0.insert(key.to_lowercase(), value);
    }
}

#[derive(Clone, Debug)]
pub struct Options {
    /// OTEL_SERVICE_NAME, else SERVICE_NAME: one stable logical name per service.
    pub service: String,
    /// DEPLOYMENT_ENVIRONMENT, else RUN_ENV, else ENV_NAME, else "local".
    pub environment: String,
    pub node: Option<String>,
    pub version: Option<String>,
    /// OTLP/HTTP base URL; `/v1/traces` is appended. Empty = no export.
    pub endpoint: String,
    pub token: String,
    pub timeout: Duration,
    pub sampler: String,
    pub sampler_arg: f64,
    pub detail: bool,
    pub resource_attributes: Vec<(String, String)>,
}

impl Default for Options {
    fn default() -> Self {
        Options {
            service: String::new(),
            environment: "local".into(),
            node: None,
            version: None,
            endpoint: String::new(),
            token: String::new(),
            timeout: Duration::from_secs(5),
            sampler: "parentbased_traceidratio".into(),
            sampler_arg: 1.0,
            detail: false,
            resource_attributes: vec![],
        }
    }
}

pub struct Tracing {
    provider: SdkTracerProvider,
    tracer: SdkTracer,
    pub options: Options,
}

fn env(name: &str) -> String {
    std::env::var(name).unwrap_or_default().trim().to_string()
}
fn flag(name: &str) -> bool {
    matches!(
        env(name).to_lowercase().as_str(),
        "1" | "true" | "yes" | "on"
    )
}
/// Value of NAME, else the contents of the file named by NAME_FILE.
fn secret(name: &str) -> Result<String, String> {
    let value = env(name);
    let file = env(&format!("{name}_FILE"));
    if value.is_empty() && !file.is_empty() {
        return std::fs::read_to_string(&file)
            .map(|v| v.trim().to_string())
            .map_err(|e| format!("{name}_FILE: {e}"));
    }
    Ok(value)
}

impl Options {
    pub fn from_env() -> Result<Options, String> {
        let service = if env("OTEL_SERVICE_NAME").is_empty() {
            env("SERVICE_NAME")
        } else {
            env("OTEL_SERVICE_NAME")
        };
        if service.is_empty() {
            return Err("SERVICE_NAME (or OTEL_SERVICE_NAME) is required".into());
        }
        let mut extra: Vec<(String, String)> = env("OTEL_RESOURCE_ATTRIBUTES")
            .split(',')
            .filter_map(|i| {
                i.split_once('=')
                    .map(|(k, v)| (k.trim().to_string(), v.trim().to_string()))
            })
            .collect();
        let version = [env("SERVICE_VERSION")]
            .into_iter()
            .chain(
                extra
                    .iter()
                    .find(|(k, _)| k == "service.version")
                    .map(|(_, v)| v.clone()),
            )
            .find(|v| !v.is_empty());
        extra.retain(|(k, _)| k != "service.version");
        let first = |names: &[&str], default: &str| {
            names
                .iter()
                .map(|n| env(n))
                .find(|v| !v.is_empty())
                .unwrap_or_else(|| default.to_string())
        };
        let traces = env("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT");
        let ratio = env("OTEL_TRACES_SAMPLER_ARG");
        let timeout_ms = env("OTEL_EXPORTER_OTLP_TIMEOUT");
        Ok(Options {
            service,
            environment: first(&["DEPLOYMENT_ENVIRONMENT", "RUN_ENV", "ENV_NAME"], "local"),
            node: Some(env("NODE_NAME")).filter(|v| !v.is_empty()),
            version,
            endpoint: if traces.is_empty() {
                env("OTEL_EXPORTER_OTLP_ENDPOINT")
            } else {
                traces.trim_end_matches("/v1/traces").to_string()
            },
            token: secret("OTEL_AUTH_TOKEN")?,
            timeout: Duration::from_millis(if timeout_ms.is_empty() {
                5000
            } else {
                timeout_ms
                    .parse()
                    .map_err(|_| "OTEL_EXPORTER_OTLP_TIMEOUT must be milliseconds")?
            }),
            sampler: first(&["OTEL_TRACES_SAMPLER"], "parentbased_traceidratio"),
            sampler_arg: if ratio.is_empty() {
                1.0
            } else {
                ratio
                    .parse()
                    .map_err(|_| "OTEL_TRACES_SAMPLER_ARG must be a number")?
            },
            detail: flag("TRACING_DETAIL"),
            resource_attributes: extra,
        })
    }
}

impl Tracing {
    pub fn from_env() -> Result<Tracing, String> {
        Tracing::new(Options::from_env()?, None)
    }

    /// `exporter`: tests pass an in-memory exporter (used with a synchronous processor).
    pub fn new(
        options: Options,
        exporter: Option<Box<dyn SpanExporterDyn>>,
    ) -> Result<Tracing, String> {
        let o = &options;
        if o.service.is_empty() {
            return Err("service name is required".into());
        }
        let node = o
            .node
            .clone()
            .unwrap_or_else(|| gethostname::gethostname().to_string_lossy().into_owned());
        let mut attrs = vec![
            KeyValue::new("service.name", o.service.clone()),
            KeyValue::new("deployment.environment", o.environment.clone()),
            KeyValue::new("deployment.environment.name", o.environment.clone()),
            KeyValue::new("host.name", node.clone()),
            KeyValue::new(
                "service.instance.id",
                format!("{node}-{}", std::process::id()),
            ),
        ];
        if let Some(v) = &o.version {
            attrs.push(KeyValue::new("service.version", v.clone()));
        }
        attrs.extend(
            o.resource_attributes
                .iter()
                .map(|(k, v)| KeyValue::new(k.clone(), v.clone())),
        );
        let mut builder = SdkTracerProvider::builder()
            .with_resource(Resource::builder().with_attributes(attrs).build())
            .with_sampler(sampler(o)?);
        match exporter {
            Some(e) => builder = e.install(builder),
            None if !o.endpoint.is_empty()
                && env("OTEL_TRACES_EXPORTER") != "none"
                && !flag("OTEL_SDK_DISABLED") =>
            {
                let mut headers = HashMap::new();
                if !o.token.is_empty() {
                    headers.insert("Authorization".to_string(), format!("Bearer {}", o.token));
                }
                let exporter = OtlpExporter::builder()
                    .with_http()
                    .with_protocol(Protocol::HttpBinary)
                    // The endpoint is used as given: include the signal path.
                    .with_endpoint(format!("{}/v1/traces", o.endpoint.trim_end_matches('/')))
                    .with_headers(headers)
                    .with_timeout(o.timeout)
                    .build()
                    .map_err(|e| e.to_string())?;
                // Batch export off the request path; queue/batch sizes come from the OTEL_BSP_*
                // variables.
                builder =
                    builder.with_span_processor(BatchSpanProcessor::builder(exporter).build());
            }
            None => {}
        }
        let provider = builder.build();
        global::set_tracer_provider(provider.clone());
        global::set_text_map_propagator(TextMapCompositePropagator::new(vec![
            Box::new(TraceContextPropagator::new()),
            Box::new(BaggagePropagator::new()),
        ]));
        let tracer = provider.tracer("service-tracing");
        Ok(Tracing {
            provider,
            tracer,
            options,
        })
    }

    pub fn shutdown(&self) {
        let _ = self.provider.shutdown(); // flushes the batch processor within its export timeout
    }

    // ---- boundary spans (dependency mode)
    // --------------------------------------------------------------
    /// Inbound request: continue the caller's trace from the carrier (missing/invalid -> a new
    /// trace).
    pub fn server_context(&self, name: &str, inbound: &dyn Extractor) -> Context {
        let parent = TraceContextPropagator::new().extract(inbound);
        self.start(&parent, name, SpanKind::Server, vec![])
    }

    /// Outbound call to another service: injects the context into `out`.
    pub fn client_context(
        &self,
        parent: &Context,
        name: &str,
        peer: &str,
        out: &mut dyn Injector,
    ) -> Context {
        let cx = self.start(
            parent,
            name,
            SpanKind::Client,
            vec![KeyValue::new("peer.service", peer.to_string())],
        );
        TraceContextPropagator::new().inject_context(&cx, out);
        cx
    }

    /// Datastore/broker/object store without instrumentation: a span with a stable peer identity.
    /// Host and port come from the infrastructure variables (POSTGRES_HOST,
    /// KAFKA_BOOTSTRAP_SERVERS, S3_ENDPOINT ...).
    pub fn peer_context(&self, parent: &Context, kind: &str, operation: &str) -> Context {
        let (key, value, span_kind, prefix) = match kind {
            "postgres" => ("db.system", "postgresql", SpanKind::Client, "POSTGRES"),
            "redis" => ("db.system", "redis", SpanKind::Client, "REDIS"),
            "clickhouse" => ("db.system", "clickhouse", SpanKind::Client, "CLICKHOUSE"),
            "kafka" => ("messaging.system", "kafka", SpanKind::Producer, "KAFKA"),
            "s3" => ("rpc.system", "aws-api", SpanKind::Client, "S3"),
            _ => ("rpc.system", kind, SpanKind::Client, ""),
        };
        let peer = Some(env(&format!("PEER_SERVICE_{}", kind.to_uppercase())))
            .filter(|v| !v.is_empty())
            .unwrap_or_else(|| kind.to_string());
        let mut attrs = vec![
            KeyValue::new("peer.service", peer),
            KeyValue::new(key, value.to_string()),
        ];
        let (host, port) = peer_address(kind, prefix);
        if !host.is_empty() {
            attrs.push(KeyValue::new("server.address", host));
        }
        if port != 0 {
            attrs.push(KeyValue::new("server.port", port as i64));
        }
        self.start(parent, &format!("{kind} {operation}"), span_kind, attrs)
    }

    /// Publish to a queue/stream: injects the context into the message headers.
    pub fn producer_context(
        &self,
        parent: &Context,
        destination: &str,
        out: &mut dyn Injector,
    ) -> Context {
        let cx = self.start(
            parent,
            &format!("{destination} publish"),
            SpanKind::Producer,
            vec![
                KeyValue::new("messaging.system", "kafka"),
                KeyValue::new("messaging.destination.name", destination.to_string()),
                KeyValue::new("messaging.operation", "publish"),
                KeyValue::new("peer.service", "kafka"),
            ],
        );
        TraceContextPropagator::new().inject_context(&cx, out);
        cx
    }

    /// Handle one message: parent = the producer's context from the message headers.
    pub fn consumer_context(&self, destination: &str, inbound: &dyn Extractor) -> Context {
        let parent = TraceContextPropagator::new().extract(inbound);
        self.start(
            &parent,
            &format!("{destination} process"),
            SpanKind::Consumer,
            vec![
                KeyValue::new("messaging.system", "kafka"),
                KeyValue::new("messaging.destination.name", destination.to_string()),
                KeyValue::new("messaging.operation", "process"),
            ],
        )
    }

    /// Internal span for detailed mode: `Some(context)` only when TRACING_DETAIL=true, else `None`
    /// (do nothing). `if let Some(cx) = tracing.detail_context(&parent, "compute") { ...;
    /// tracing.finish::<String>(&cx, None); }`
    pub fn detail_context(&self, parent: &Context, name: &str) -> Option<Context> {
        self.options
            .detail
            .then(|| self.start(parent, name, SpanKind::Internal, vec![]))
    }

    /// End the span held by `cx`; record only the error type (messages can carry payloads or
    /// credentials).
    pub fn finish<E: Display + ?Sized>(&self, cx: &Context, err: Option<&E>) {
        let span = cx.span();
        if let Some(e) = err {
            let _ = e;
            span.set_status(Status::error(std::any::type_name::<E>().to_string()));
        }
        span.end();
    }

    /// (trace_id, span_id) of the active valid span as hex, else empty strings: for log
    /// correlation.
    #[allow(dead_code)]
    pub fn ids(cx: &Context) -> (String, String) {
        let sc = cx.span().span_context().clone();
        if sc.is_valid() {
            (sc.trace_id().to_string(), sc.span_id().to_string())
        } else {
            (String::new(), String::new())
        }
    }

    fn start(&self, parent: &Context, name: &str, kind: SpanKind, attrs: Vec<KeyValue>) -> Context {
        let span = self
            .tracer
            .span_builder(name.to_string())
            .with_kind(kind)
            .with_attributes(attrs)
            .start_with_context(&self.tracer, parent);
        parent.with_span(span)
    }
}

/// Lets tests (and callers) hand over any exporter without exposing the SDK's generic builder.
pub trait SpanExporterDyn {
    fn install(
        self: Box<Self>,
        builder: opentelemetry_sdk::trace::TracerProviderBuilder,
    ) -> opentelemetry_sdk::trace::TracerProviderBuilder;
}
impl<E: SpanExporter + 'static> SpanExporterDyn for E {
    fn install(
        self: Box<Self>,
        builder: opentelemetry_sdk::trace::TracerProviderBuilder,
    ) -> opentelemetry_sdk::trace::TracerProviderBuilder {
        builder.with_span_processor(SimpleSpanProcessor::new(*self))
    }
}

fn sampler(o: &Options) -> Result<Sampler, String> {
    let name = o.sampler.to_lowercase();
    let parent = |s: Sampler| Sampler::ParentBased(Box::new(s));
    match name.as_str() {
        "always_on" => return Ok(Sampler::AlwaysOn),
        "always_off" => return Ok(Sampler::AlwaysOff),
        "parentbased_always_on" => return Ok(parent(Sampler::AlwaysOn)),
        "parentbased_always_off" => return Ok(parent(Sampler::AlwaysOff)),
        _ => {}
    }
    if !(0.0..=1.0).contains(&o.sampler_arg) {
        return Err(format!(
            "OTEL_TRACES_SAMPLER_ARG must be within 0..1, got {}",
            o.sampler_arg
        ));
    }
    let ratio = Sampler::TraceIdRatioBased(o.sampler_arg);
    Ok(if name == "traceidratio" {
        ratio
    } else {
        parent(ratio)
    }) // default: honour the upstream decision
}

fn peer_address(kind: &str, prefix: &str) -> (String, u16) {
    match kind {
        "kafka" => {
            let servers = env("KAFKA_BOOTSTRAP_SERVERS");
            let first = servers.split(',').next().unwrap_or("").trim();
            match first.rsplit_once(':') {
                Some((h, p)) => (h.to_string(), p.parse().unwrap_or(0)),
                None => (first.to_string(), 0),
            }
        }
        "s3" => {
            let endpoint = env("S3_ENDPOINT");
            let (scheme, rest) = endpoint.split_once("://").unwrap_or(("", &endpoint));
            let authority = rest.split('/').next().unwrap_or("");
            match authority.rsplit_once(':') {
                Some((h, p)) => (h.to_string(), p.parse().unwrap_or(0)),
                None => (
                    authority.to_string(),
                    if scheme == "https" {
                        443
                    } else if scheme.is_empty() {
                        0
                    } else {
                        80
                    },
                ),
            }
        }
        _ => {
            let default = match kind {
                "postgres" => 5432,
                "redis" => 6379,
                "clickhouse" => 9000,
                _ => 0,
            };
            (
                env(&format!("{prefix}_HOST")),
                env(&format!("{prefix}_PORT")).parse().unwrap_or(default),
            )
        }
    }
}
