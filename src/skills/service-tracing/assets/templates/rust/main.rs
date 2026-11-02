//! Smoke test and demo for service_tracing.rs.
//!   cargo test                 assertions with in-memory exporters (no collector needed)
//!   cargo run -- demo          export one demo request to OTEL_EXPORTER_OTLP_ENDPOINT (see
//!                              references/verification.md):
//!     SERVICE_NAME=api TRACEPARENT=<from upstream> DEMO_CALL=worker DEMO_DB=postgres \
//!       cargo run -- demo
//!     prints the traceparent it sends downstream.
mod service_tracing;

use opentelemetry::Context;
use service_tracing::{Carrier, Tracing};

fn main() {
    if std::env::args().nth(1).as_deref() != Some("demo") {
        eprintln!("run `cargo test`, or `cargo run -- demo`");
        return;
    }
    let tracing = Tracing::from_env().expect("tracing options");
    let mut inbound = Carrier::default();
    if let Ok(tp) = std::env::var("TRACEPARENT") {
        inbound.0.insert("traceparent".into(), tp);
    }
    let server = tracing.server_context("GET /demo", &inbound);
    if let Ok(db) = std::env::var("DEMO_DB") {
        let cx = tracing.peer_context(&server, &db, "query");
        tracing.finish::<String>(&cx, None);
    }
    if let Ok(peer) = std::env::var("DEMO_CALL") {
        let mut out = Carrier::default();
        let cx = tracing.client_context(&server, "GET /demo", &peer, &mut out);
        println!("{}", out.0["traceparent"]);
        tracing.finish::<String>(&cx, None);
    }
    tracing.finish::<String>(&server, None);
    tracing.shutdown();
    let _ = Context::current();
}

#[cfg(test)]
mod tests {
    use super::*;
    use opentelemetry::trace::SpanKind;
    use opentelemetry::Key;
    use opentelemetry_sdk::error::OTelSdkResult;
    use opentelemetry_sdk::trace::{InMemorySpanExporter, SpanData, SpanExporter};
    use opentelemetry_sdk::Resource;
    use service_tracing::Options;

    /// In-memory exporter that also keeps the resource the provider hands it (SpanData carries
    /// none).
    #[derive(Debug, Clone, Default)]
    struct Capture {
        inner: InMemorySpanExporter,
        resource: std::sync::Arc<std::sync::Mutex<Option<Resource>>>,
    }
    impl SpanExporter for Capture {
        fn export(
            &self,
            batch: Vec<SpanData>,
        ) -> impl std::future::Future<Output = OTelSdkResult> + Send {
            self.inner.export(batch)
        }
        fn set_resource(&mut self, resource: &Resource) {
            *self.resource.lock().unwrap() = Some(resource.clone());
        }
    }
    impl std::ops::Deref for Capture {
        type Target = InMemorySpanExporter;
        fn deref(&self) -> &InMemorySpanExporter {
            &self.inner
        }
    }
    fn res(exporter: &Capture, key: &str) -> String {
        exporter
            .resource
            .lock()
            .unwrap()
            .as_ref()
            .unwrap()
            .get(&Key::new(key.to_string()))
            .unwrap()
            .to_string()
    }

    fn make(service: &str, detail: bool) -> (Tracing, Capture) {
        let exporter = Capture::default();
        let options = Options {
            service: service.into(),
            environment: "test".into(),
            node: Some("n1".into()),
            version: Some("1.2.3".into()),
            detail,
            ..Default::default()
        };
        (
            Tracing::new(options, Some(Box::new(exporter.clone()))).unwrap(),
            exporter,
        )
    }

    fn attr(span: &opentelemetry_sdk::trace::SpanData, key: &str) -> Option<String> {
        span.attributes
            .iter()
            .find(|kv| kv.key.as_str() == key)
            .map(|kv| kv.value.to_string())
    }

    #[test]
    fn dependency_edges() {
        std::env::set_var("POSTGRES_HOST", "db.internal");
        std::env::set_var("KAFKA_BOOTSTRAP_SERVERS", "k1:9092,k2:9092");
        let (web, web_spans) = make("web", false);
        let (api, api_spans) = make("api", false);

        // web CLIENT -> headers -> api SERVER: one trace, parent = the client span
        let home = web.server_context("GET /home", &Carrier::default());
        let mut headers = Carrier::default();
        let client = web.client_context(&home, "GET /orders", "api", &mut headers);
        assert!(
            headers.0.contains_key("traceparent"),
            "client span must inject traceparent"
        );
        let server = api.server_context("GET /orders", &headers);
        let db = api.peer_context(&server, "postgres", "select orders");
        api.finish::<String>(&db, None);
        api.finish::<String>(&server, None);
        web.finish::<String>(&client, None);
        web.finish::<String>(&home, None);

        let web_done = web_spans.get_finished_spans().unwrap();
        let api_done = api_spans.get_finished_spans().unwrap();
        let c = web_done
            .iter()
            .find(|s| s.span_kind == SpanKind::Client)
            .unwrap();
        let s = api_done
            .iter()
            .find(|s| s.span_kind == SpanKind::Server)
            .unwrap();
        assert_eq!(s.span_context.trace_id(), c.span_context.trace_id());
        assert_eq!(
            s.parent_span_id,
            c.span_context.span_id(),
            "server span must be a child of the caller's client span"
        );
        assert_eq!(res(&api_spans, "service.name"), "api");
        assert_eq!(res(&web_spans, "deployment.environment"), "test");
        assert_eq!(res(&web_spans, "service.version"), "1.2.3");

        // peer identity for an uninstrumented datastore
        let d = api_done
            .iter()
            .find(|s| s.span_kind == SpanKind::Client)
            .unwrap();
        assert_eq!(d.name, "postgres select orders");
        assert_eq!(attr(d, "peer.service").as_deref(), Some("postgres"));
        assert_eq!(attr(d, "db.system").as_deref(), Some("postgresql"));
        assert_eq!(attr(d, "server.address").as_deref(), Some("db.internal"));
        assert_eq!(attr(d, "server.port").as_deref(), Some("5432"));

        // messaging: producer -> headers -> consumer
        let mut msg = Carrier::default();
        let p = web.producer_context(&Context::new(), "orders.created", &mut msg);
        web.finish::<String>(&p, None);
        let cons = api.consumer_context(
            "orders.created",
            &Carrier::from_pairs(msg.0.iter().map(|(k, v)| (k.as_str(), v.as_bytes()))),
        );
        api.finish::<String>(&cons, None);
        let producer = web_spans
            .get_finished_spans()
            .unwrap()
            .into_iter()
            .find(|s| s.span_kind == SpanKind::Producer)
            .unwrap();
        let consumer = api_spans
            .get_finished_spans()
            .unwrap()
            .into_iter()
            .find(|s| s.span_kind == SpanKind::Consumer)
            .unwrap();
        assert_eq!(consumer.parent_span_id, producer.span_context.span_id());
        assert_eq!(
            consumer.span_context.trace_id(),
            producer.span_context.trace_id()
        );

        // missing or invalid context starts a valid new trace
        let before = api_spans.get_finished_spans().unwrap().len();
        for bad in [
            vec![],
            vec![("traceparent", "garbage".to_string())],
            vec![(
                "traceparent",
                format!("00-{}-{}-01", "0".repeat(32), "0".repeat(16)),
            )],
        ] {
            let mut c = Carrier::default();
            for (k, v) in bad {
                c.0.insert(k.into(), v);
            }
            let cx = api.server_context("GET /bad", &c);
            assert!(opentelemetry::trace::TraceContextExt::span(&cx)
                .span_context()
                .is_valid());
            api.finish::<String>(&cx, None);
        }
        let roots = api_spans
            .get_finished_spans()
            .unwrap()
            .into_iter()
            .skip(before)
            .filter(|s| s.parent_span_id == opentelemetry::trace::SpanId::INVALID)
            .count();
        assert_eq!(roots, 3);

        // failures: error status carries the type name only, never the message
        let cx = api.server_context("POST /fail", &Carrier::default());
        api.finish(&cx, Some(&"secret-token-123".to_string()));
        let failed = api_spans
            .get_finished_spans()
            .unwrap()
            .into_iter()
            .find(|s| s.name == "POST /fail")
            .unwrap();
        let is_clean_error = match &failed.status {
            opentelemetry::trace::Status::Error { description } => !description.contains("secret"),
            _ => false,
        };
        assert!(
            is_clean_error,
            "the status must be an error that does not carry the message"
        );

        // kafka peer: first bootstrap server
        let cx = api.peer_context(&Context::new(), "kafka", "send");
        api.finish::<String>(&cx, None);
        let k = api_spans
            .get_finished_spans()
            .unwrap()
            .into_iter()
            .last()
            .unwrap();
        assert_eq!(k.span_kind, SpanKind::Producer);
        assert_eq!(attr(&k, "server.address").as_deref(), Some("k1"));
    }

    #[test]
    fn detail_is_gated_by_mode() {
        let (api, spans) = make("api", false);
        let server = api.server_context("GET /x", &Carrier::default());
        assert!(
            api.detail_context(&server, "compute").is_none(),
            "dependency mode starts no internal span"
        );
        api.finish::<String>(&server, None);
        assert!(!spans
            .get_finished_spans()
            .unwrap()
            .iter()
            .any(|s| s.span_kind == SpanKind::Internal));
        let (det, dspans) = make("api", true);
        let server = det.server_context("GET /x", &Carrier::default());
        let d = det
            .detail_context(&server, "compute")
            .expect("detailed mode starts the span");
        det.finish::<String>(&d, None);
        det.finish::<String>(&server, None);
        assert_eq!(
            dspans
                .get_finished_spans()
                .unwrap()
                .iter()
                .filter(|s| s.span_kind == SpanKind::Internal)
                .count(),
            1
        );
    }
}
