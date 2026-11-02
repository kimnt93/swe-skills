//! Errors to Sentry or GlitchTip (service-errors skill).
//!
//! Every `tracing::error!` event becomes one Sentry event; warnings never do. An event carries the
//! static message, the stack of a panic, the environment, the release (`<service_name>@<version>`),
//! the node as server name and the tags `service_name` and `trace_id`. It never carries the event's
//! fields (they hold ids, errors and data), a request, a user, breadcrumbs, contexts, extra data or
//! a panic's payload text. OpenTelemetry owns traces: the SDK's tracing is off.
//!
//! Off unless a DSN is set. A Sentry outage never breaks a request: the transport sends from a
//! background thread. Wire it once in `main`:
//!
//! ```ignore
//! let _errors = errtracking::init(errtracking::Options {
//!     dsn: Some(cfg.sentry_dsn.clone()), // empty: off
//!     service_name: cfg.service_name.clone(),
//!     environment: cfg.env_name.clone(),
//!     release: format!("{}@{}", cfg.service_name, cfg.service_version),
//!     node_name: cfg.node_name.clone(),
//!     trace_id: None, // or a fn returning the current OpenTelemetry trace id
//! });
//! tracing_subscriber::registry()
//!     .with(EnvFilter::new(&cfg.log_level))
//!     .with(tracing_subscriber::fmt::layer().json())
//!     .with(errtracking::layer())
//!     .init();
//! ```
//!
//! Dropping the guard flushes for up to two seconds, so it must outlive the server.

use std::{
    borrow::Cow,
    collections::HashMap,
    sync::{Arc, Mutex},
    time::{Duration, Instant},
};

use sentry::{protocol::Event, ClientInitGuard, ClientOptions};
use sentry_tracing::EventFilter;
use tracing::{Level, Subscriber};
use tracing_subscriber::{registry::LookupSpan, Layer};

const FLUSH_TIMEOUT: Duration = Duration::from_secs(2);

/// One event per message per minute per process; local logs keep every occurrence.
const THROTTLE_WINDOW: Duration = Duration::from_secs(60);

const TAG_SERVICE: &str = "service_name";
const TAG_TRACE: &str = "trace_id";

/// Error-level messages that are not operational failures. Add a message here on purpose.
const SKIPPED: &[&str] = &["request completed"];

/// Returns the current trace id when the process has OpenTelemetry (see `trace_id` below).
pub type TraceId = fn() -> Option<String>;

pub struct Options {
    /// `SENTRY_DSN` (or the file named by `SENTRY_DSN_FILE`); `None` or blank turns reporting off.
    pub dsn: Option<String>,
    pub service_name: String,
    /// `ENV_NAME`: stg, prod, ...
    pub environment: String,
    /// `<service_name>@<SERVICE_VERSION>`
    pub release: String,
    pub node_name: String,
    /// Tags events with the trace of the failure; `None` without OpenTelemetry.
    pub trace_id: Option<TraceId>,
}

/// Starts reporting. The returned guard flushes on drop; with no DSN it is inert.
pub fn init(options: Options) -> ClientInitGuard {
    sentry::init(client_options(options))
}

/// The SDK options, separate from `init` so a test can add a capturing transport.
#[allow(clippy::field_reassign_with_default)] // the struct is non-exhaustive
pub fn client_options(options: Options) -> ClientOptions {
    let dsn = options
        .dsn
        .as_deref()
        .map(str::trim)
        .filter(|dsn| !dsn.is_empty());
    let service = options.service_name;
    let trace_id = options.trace_id;
    let throttle = Throttle::default();

    // `ClientOptions` is non-exhaustive: build it field by field.
    let mut opts = ClientOptions::default();
    // An unparsable DSN disables reporting; the error never names the value.
    opts.dsn = dsn.and_then(|dsn| dsn.parse().ok());
    opts.environment = Some(Cow::Owned(options.environment));
    opts.release = Some(Cow::Owned(options.release));
    opts.server_name = (!options.node_name.is_empty()).then_some(Cow::Owned(options.node_name));
    opts.attach_stacktrace = true;
    opts.send_default_pii = false;
    opts.max_breadcrumbs = 0;
    opts.shutdown_timeout = FLUSH_TIMEOUT;
    opts.before_send = Some(Arc::new(move |event| {
        scrub(event, &service, trace_id, &throttle)
    }));
    opts
}

/// The `tracing` layer: error events only. Fields are dropped later, in `scrub`.
pub fn layer<S>() -> impl Layer<S>
where
    S: Subscriber + for<'a> LookupSpan<'a>,
{
    sentry_tracing::layer().event_filter(|metadata| match *metadata.level() {
        Level::ERROR => EventFilter::Event,
        _ => EventFilter::Ignore,
    })
}

/// Keeps the message and the stack; drops everything else; throttles repeats.
fn scrub(
    mut event: Event<'static>,
    service: &str,
    trace_id: Option<TraceId>,
    throttle: &Throttle,
) -> Option<Event<'static>> {
    let message = event
        .message
        .clone()
        .or_else(|| event.logentry.as_ref().map(|entry| entry.message.clone()))
        .unwrap_or_default();
    if SKIPPED.contains(&message.as_str()) || throttle.hit(&message) {
        return None;
    }

    event.request = None;
    event.user = None;
    event.breadcrumbs = Default::default();
    event.contexts = Default::default();
    event.extra = Default::default();
    event.modules = Default::default();
    for exception in event.exception.iter_mut() {
        exception.value = None; // a panic payload can hold business data or a secret
    }

    event.tags = Default::default();
    event.tags.insert(TAG_SERVICE.into(), service.into());
    if let Some(id) = trace_id.and_then(|current| current()) {
        event.tags.insert(TAG_TRACE.into(), id);
    }

    Some(event)
}

/// Remembers when each message was last sent.
#[derive(Default, Clone)]
struct Throttle(Arc<Mutex<HashMap<String, Instant>>>);

impl Throttle {
    /// True when `message` was already sent within the window.
    fn hit(&self, message: &str) -> bool {
        let Ok(mut last) = self.0.lock() else {
            return false;
        };
        let now = Instant::now();
        match last.get(message) {
            Some(at) if now.duration_since(*at) < THROTTLE_WINDOW => true,
            _ => {
                last.insert(message.to_string(), now);
                false
            }
        }
    }
}

#[cfg(test)]
#[allow(clippy::cognitive_complexity)] // the tracing macros expand to branches
mod tests {
    use sentry::test::with_captured_events_options;
    use tracing_subscriber::{layer::SubscriberExt, Registry};

    use super::*;

    const DSN: &str = "http://key@127.0.0.1:9/1";

    fn options(dsn: Option<&str>) -> Options {
        Options {
            dsn: dsn.map(str::to_string),
            service_name: "svc".into(),
            environment: "stg".into(),
            release: "svc@1.2.3".into(),
            node_name: "node-1".into(),
            trace_id: Some(|| Some("a".repeat(32))),
        }
    }

    fn capture(dsn: Option<&str>, run: impl FnOnce()) -> Vec<Event<'static>> {
        let mut opts = client_options(options(dsn));
        opts.dsn = DSN.parse().ok().or(opts.dsn);
        let subscriber = Registry::default().with(layer());
        with_captured_events_options(|| tracing::subscriber::with_default(subscriber, run), opts)
    }

    /// A warning, then the same error twice with private fields: one event must come out.
    fn failure_events() -> Vec<Event<'static>> {
        capture(Some(DSN), || {
            tracing::warn!("expected upstream fault");
            tracing::error!(
                token = "private-token",
                user = "private-user",
                "operation failed"
            );
            tracing::error!("operation failed"); // throttled: one event per minute
        })
    }

    #[test]
    fn an_error_is_one_event_with_the_identity() {
        let events = failure_events();
        assert_eq!(events.len(), 1, "{events:?}");
        let event = &events[0];
        assert_eq!(event.message.as_deref(), Some("operation failed"));
        assert_eq!(event.environment.as_deref(), Some("stg"));
        assert_eq!(event.release.as_deref(), Some("svc@1.2.3"));
        assert_eq!(event.server_name.as_deref(), Some("node-1"));
        assert_eq!(event.tags.get(TAG_SERVICE).map(String::as_str), Some("svc"));
        assert_eq!(event.tags.get(TAG_TRACE), Some(&"a".repeat(32)));
    }

    #[test]
    fn nothing_private_travels() {
        let events = failure_events();
        let event = &events[0];
        assert!(event.extra.is_empty() && event.contexts.is_empty());
        assert!(event.user.is_none() && event.request.is_none());
        assert!(!format!("{event:?}").contains("private-"));
    }

    #[test]
    fn the_request_summary_is_not_an_operational_failure() {
        let events = capture(Some(DSN), || tracing::error!("request completed"));
        assert!(events.is_empty());
    }

    #[test]
    fn no_dsn_or_a_bad_one_disables_reporting_without_naming_it() {
        for dsn in [None, Some(""), Some("   "), Some("private-invalid-dsn")] {
            let opts = client_options(options(dsn));
            assert!(opts.dsn.is_none(), "{dsn:?}");
        }
    }
}
