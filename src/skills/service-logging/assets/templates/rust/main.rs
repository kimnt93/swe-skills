//! Smoke test: emit the line types a service produces, then validate them:
//!
//!   SERVICE_NAME=ssi-ws-v3 ENV_NAME=local NODE_NAME=docker-host-1 LOG_LEVEL=debug \
//!     cargo run --features otel \
//!     | python3 scripts/logcheck.py --service ssi-ws-v3 --env local --node docker-host-1 \
//!         --require-trace

mod service_logging;

fn main() -> Result<(), String> {
    let options = service_logging::options_from_env("ssi-data")?;

    #[cfg(feature = "otel")]
    let provider = {
        use opentelemetry::trace::TracerProvider as _;
        use tracing_subscriber::layer::SubscriberExt;
        use tracing_subscriber::util::SubscriberInitExt;
        let provider = opentelemetry_sdk::trace::SdkTracerProvider::builder().build();
        let otel = tracing_opentelemetry::layer().with_tracer(provider.tracer("smoke"));
        tracing_subscriber::registry()
            .with(otel)
            .with(service_logging::layer(options))
            .init();
        provider
    };
    #[cfg(not(feature = "otel"))]
    service_logging::init(options);

    tracing::info!(
        messages_received = 361234u64,
        messages_published = 361233u64,
        channel_depth = 0u64,
        "message statistics"
    );
    tracing::warn!(target: "api.request", request_id = "r-1", duration_ms = 1250.5, "slow request");
    tracing::debug!(ok = true, time = 5u64, "custom field named time");
    tracing::error!(
        error = "sink write failed",
        error_type = "SinkError",
        table = "trades",
        "write failed"
    );
    tracing::error!(fatal = true, "cannot continue");

    #[cfg(feature = "otel")]
    {
        let span = tracing::info_span!("work");
        let _guard = span.enter();
        tracing::info!("inside a span");
        drop(provider);
    }
    Ok(())
}
