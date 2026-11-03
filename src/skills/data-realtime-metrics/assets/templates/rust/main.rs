//! Smoke test: emit every metric once so scripts/otlp_check.py can verify the contract.
//!
//!   python3 scripts/otlp_check.py --role ingestion --wait 30 &
//!   cargo run -- http://127.0.0.1:4318 ingestion

mod pipeline_metrics;

use std::time::Duration;

use pipeline_metrics::{Options, PipelineMetrics};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    let (endpoint, role) = (args[1].clone(), args[2].clone());
    let m = PipelineMetrics::new(Options {
        service: format!(
            "feed-ws-{}",
            if role == "ingestion" { "feed" } else { &role }
        ),
        environment: "local".into(),
        endpoint,
        export_interval: Some(Duration::from_secs(1)),
        ingestion: role == "ingestion",
        ..Default::default()
    })?;
    m.set_kafka_healthy(true);
    m.set_backlog(|| 3);
    if role == "ingestion" {
        m.set_connected(true);
        m.set_in_flight(|| 2);
        m.reconnect();
    }
    m.received(true);
    m.received(true);
    m.received(false);
    m.dropped();
    m.published(128, Duration::from_millis(4));
    m.error();
    std::thread::sleep(Duration::from_secs(3));
    m.shutdown();
    Ok(())
}
