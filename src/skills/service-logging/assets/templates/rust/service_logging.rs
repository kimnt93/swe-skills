//! Unified service logging on `tracing` (see references/log-format.md). Add this file as a
//! module and call once at startup:
//!
//! ```ignore
//! // The root is the project directory name used in `caller`.
//! service_logging::init_from_env("ssi-data")?;
//! tracing::info!(messages_received = 361234u64, channel_depth = 0u64, "message statistics");
//! tracing::warn!(target: "api.request", request_id = "r-1", duration_ms = 1250.5, "slow request");
//! tracing::error!(error = %err, error_type = "SinkError", "sink write failed");
//! // Level "fatal".
//! tracing::error!(fatal = true, "cannot continue");
//! ```
//!
//! Every line has level, development_environment, service_name, node_name, logger (the event
//! target: the module path, or the `target:` you set), time (UTC RFC 3339, 9 fractional
//! digits), caller (<root>/<relative path>:<line>) and message, plus trace_id/span_id when
//! the `otel` feature is on and the event happens inside an OpenTelemetry span. For trace ids
//! compose the layer with your tracer instead of calling `init`:
//!
//! ```ignore
//! let otel = tracing_opentelemetry::layer().with_tracer(provider.tracer("my-service"));
//! let options = service_logging::options_from_env("ssi-data")?;
//! tracing_subscriber::registry()
//!     .with(otel)
//!     .with(service_logging::layer(options))
//!     .init();
//! ```
//!
//! Custom fields stay flat; a name that collides with a core field is written as `field_<name>`.

#![allow(dead_code)] // a template: the smoke test uses only part of it

use std::fmt;

use serde_json::{Map, Value};
use tracing::field::{Field, Visit};
use tracing::{Event, Level, Subscriber};
use tracing_subscriber::fmt::format::Writer;
use tracing_subscriber::fmt::{FmtContext, FormatEvent, FormatFields};
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::registry::LookupSpan;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::{EnvFilter, Layer, Registry};

type TimeFormat = [time::format_description::BorrowedFormatItem<'static>];

const TIME_FORMAT: &TimeFormat = time::macros::format_description!(
    "[year]-[month]-[day]T[hour]:[minute]:[second].[subsecond digits:9]Z"
);
const RESERVED: [&str; 10] = [
    "level",
    "development_environment",
    "service_name",
    "node_name",
    "logger",
    "time",
    "caller",
    "message",
    "trace_id",
    "span_id",
];

pub struct Options {
    pub service: String,
    pub environment: String,
    pub node: String,
    /// debug, info, warn, error (trace also works).
    pub level: String,
    /// Project directory name that prefixes every caller path.
    pub root: String,
}

/// SERVICE_NAME (required); DEVELOPMENT_ENVIRONMENT else ENV_NAME else "local"; NODE_NAME (in
/// Docker set it to the host name; default the hostname); LOG_LEVEL (default info).
pub fn options_from_env(root: &str) -> Result<Options, String> {
    let get = |key: &str| std::env::var(key).ok().filter(|v| !v.is_empty());
    let service = get("SERVICE_NAME")
        .ok_or("SERVICE_NAME is required (the pipeline/service name, e.g. ssi-ws-v3)")?;
    Ok(Options {
        service,
        environment: get("DEVELOPMENT_ENVIRONMENT")
            .or_else(|| get("ENV_NAME"))
            .unwrap_or_else(|| "local".into()),
        node: get("NODE_NAME")
            .unwrap_or_else(|| gethostname::gethostname().to_string_lossy().into_owned()),
        level: get("LOG_LEVEL").unwrap_or_else(|| "info".into()),
        root: root.to_string(),
    })
}

/// `options_from_env` + `init`.
pub fn init_from_env(root: &str) -> Result<(), String> {
    init(options_from_env(root)?);
    Ok(())
}

/// Installs the JSON formatter as the global subscriber (stdout). Safe to call once.
pub fn init(o: Options) {
    let _ = Registry::default().with(layer(o)).try_init();
}

/// The formatting layer, for composing with other layers (e.g. the OpenTelemetry layer).
pub fn layer<S>(o: Options) -> impl Layer<S> + Send + Sync
where
    S: Subscriber + for<'a> LookupSpan<'a>,
{
    let level = match o.level.to_lowercase().as_str() {
        "warning" => "warn".to_string(),
        "critical" | "fatal" => "error".to_string(),
        other => other.to_string(),
    };
    tracing_subscriber::fmt::layer()
        .with_writer(std::io::stdout)
        .event_format(UnifiedFormat {
            service: o.service,
            environment: o.environment,
            node: o.node,
            root: o.root,
        })
        .with_filter(EnvFilter::try_new(&level).unwrap_or_else(|_| EnvFilter::new("info")))
}

struct UnifiedFormat {
    service: String,
    environment: String,
    node: String,
    root: String,
}

#[derive(Default)]
struct Fields {
    message: String,
    fatal: bool,
    values: Map<String, Value>,
}

impl Fields {
    fn put(&mut self, field: &Field, value: Value) {
        let name = field.name();
        let key = if RESERVED.contains(&name) {
            format!("field_{name}")
        } else {
            name.to_string()
        };
        self.values.insert(key, value);
    }
}

impl Visit for Fields {
    fn record_debug(&mut self, field: &Field, value: &dyn fmt::Debug) {
        if field.name() == "message" {
            self.message = format!("{value:?}");
        } else {
            self.put(field, Value::String(format!("{value:?}")));
        }
    }
    fn record_str(&mut self, field: &Field, value: &str) {
        if field.name() == "message" {
            self.message = value.to_string();
        } else {
            self.put(field, Value::String(value.to_string()));
        }
    }
    fn record_bool(&mut self, field: &Field, value: bool) {
        if field.name() == "fatal" {
            self.fatal = value;
        } else {
            self.put(field, Value::Bool(value));
        }
    }
    fn record_i64(&mut self, field: &Field, value: i64) {
        self.put(field, value.into());
    }
    fn record_u64(&mut self, field: &Field, value: u64) {
        self.put(field, value.into());
    }
    fn record_f64(&mut self, field: &Field, value: f64) {
        self.put(
            field,
            serde_json::Number::from_f64(value)
                .map_or_else(|| Value::String(value.to_string()), Value::Number),
        );
    }
}

impl UnifiedFormat {
    /// `<root>/<relative path>:<line>`; dependency paths are cut at the registry.
    fn caller(&self, file: Option<&str>, line: Option<u32>) -> String {
        let file = file.unwrap_or("unknown");
        let shown = if let Some(i) = file.find("/registry/src/") {
            file[i + "/registry/src/".len()..]
                .splitn(2, '/')
                .nth(1)
                .unwrap_or(file)
                .to_string()
        } else if file.starts_with('/') {
            std::path::Path::new(file)
                .file_name()
                .map_or(file.to_string(), |n| n.to_string_lossy().into_owned())
        } else {
            format!("{}/{}", self.root, file.trim_start_matches("./"))
        };
        format!("{shown}:{}", line.unwrap_or(1).max(1))
    }
}

#[cfg(feature = "otel")]
fn trace_ids() -> Option<(String, String)> {
    use opentelemetry::trace::TraceContextExt;
    use tracing_opentelemetry::OpenTelemetrySpanExt;
    let from_tracing = tracing::Span::current()
        .context()
        .span()
        .span_context()
        .clone();
    let context = if from_tracing.is_valid() {
        from_tracing
    } else {
        opentelemetry::Context::current()
            .span()
            .span_context()
            .clone()
    };
    context.is_valid().then(|| {
        (
            context.trace_id().to_string(),
            context.span_id().to_string(),
        )
    })
}

#[cfg(not(feature = "otel"))]
fn trace_ids() -> Option<(String, String)> {
    None
}

impl<S, N> FormatEvent<S, N> for UnifiedFormat
where
    S: Subscriber + for<'a> LookupSpan<'a>,
    N: for<'a> FormatFields<'a> + 'static,
{
    fn format_event(
        &self,
        _: &FmtContext<'_, S, N>,
        mut writer: Writer<'_>,
        event: &Event<'_>,
    ) -> fmt::Result {
        let mut fields = Fields::default();
        event.record(&mut fields);
        let meta = event.metadata();
        let level = match *meta.level() {
            _ if fields.fatal => "fatal",
            Level::TRACE => "trace",
            Level::DEBUG => "debug",
            Level::INFO => "info",
            Level::WARN => "warn",
            Level::ERROR => "error",
        };
        let mut line = Map::new();
        line.insert("level".into(), level.into());
        line.insert(
            "development_environment".into(),
            self.environment.clone().into(),
        );
        line.insert("service_name".into(), self.service.clone().into());
        line.insert("node_name".into(), self.node.clone().into());
        line.insert("logger".into(), meta.target().into());
        line.extend(fields.values);
        if let Some((trace_id, span_id)) = trace_ids() {
            line.insert("trace_id".into(), trace_id.into());
            line.insert("span_id".into(), span_id.into());
        }
        let time = time::OffsetDateTime::now_utc()
            .format(TIME_FORMAT)
            .map_err(|_| fmt::Error)?;
        line.insert("time".into(), time.into());
        line.insert(
            "caller".into(),
            self.caller(meta.file(), meta.line()).into(),
        );
        line.insert("message".into(), fields.message.into());
        writeln!(
            writer,
            "{}",
            serde_json::to_string(&line).map_err(|_| fmt::Error)?
        )
    }
}
