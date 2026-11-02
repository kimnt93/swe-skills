//! Kafka adapter (rdkafka / librdkafka): an idempotent producer that awaits the delivery report and
//! a manual-commit consumer. Connection settings come from `svc_core::config::Kafka` (KAFKA_*
//! environment variables).

use std::time::Duration;

use rdkafka::{
    config::ClientConfig,
    consumer::{CommitMode, Consumer, StreamConsumer},
    message::{Header, OwnedHeaders},
    producer::{FutureProducer, FutureRecord, Producer as _},
    Message,
};
use svc_core::{config::Kafka as Settings, ports::EventPublisher, Error, Result};

fn messaging(_e: impl std::fmt::Display) -> Error {
    // Broker errors can include addresses; the cause is logged where it is handled.
    Error::Messaging("kafka operation failed".into())
}

fn base_config(s: &Settings) -> ClientConfig {
    let mut c = ClientConfig::new();
    for (k, v) in s.client_config() {
        c.set(k, v);
    }
    c
}

pub struct Producer {
    inner: FutureProducer,
}

impl Producer {
    /// Idempotent and `acks=all`: retries cannot duplicate or lose messages.
    pub fn new(s: &Settings) -> Result<Producer> {
        let inner = base_config(s)
            .set("enable.idempotence", "true")
            .set("acks", "all")
            .set("linger.ms", "5")
            .set("compression.type", "lz4")
            .create()
            .map_err(messaging)?;
        Ok(Producer { inner })
    }

    /// Publishes with a header (for example `traceparent`) and returns when the broker
    /// acknowledged.
    pub async fn publish_with_headers(
        &self,
        topic: &str,
        key: &str,
        value: &[u8],
        headers: &[(&str, &str)],
    ) -> Result<()> {
        let mut h = OwnedHeaders::new();
        for (k, v) in headers {
            h = h.insert(Header {
                key: k,
                value: Some(*v),
            });
        }
        self.inner
            .send(
                FutureRecord::to(topic).key(key).payload(value).headers(h),
                Duration::from_secs(5),
            )
            .await
            .map(|_| ())
            .map_err(|(e, _)| messaging(e))
    }

    /// Drains queued messages (bounded); call on shutdown.
    pub fn flush(&self) {
        let _ = self.inner.flush(Duration::from_secs(10));
    }

    pub fn ping(&self) -> Result<()> {
        self.inner
            .client()
            .fetch_metadata(None, Duration::from_secs(3))
            .map(|_| ())
            .map_err(messaging)
    }
}

impl EventPublisher for Producer {
    async fn publish(&self, topic: &str, key: &str, value: &[u8]) -> Result<()> {
        self.publish_with_headers(topic, key, value, &[]).await
    }
}

/// A manual-commit consumer: `recv` returns the next message, `commit` is called only after it was
/// handled (a crash re-delivers, so handlers must be idempotent). Create topics first: a topic
/// created after the subscription is not noticed until the next metadata refresh.
pub struct Consumer_ {
    inner: StreamConsumer,
}

impl Consumer_ {
    pub fn new(s: &Settings, topics: &[&str], earliest: bool) -> Result<Consumer_> {
        let inner: StreamConsumer = base_config(s)
            .set("group.id", &s.consumer_group)
            .set("enable.auto.commit", "false")
            .set(
                "auto.offset.reset",
                if earliest { "earliest" } else { "latest" },
            )
            .create()
            .map_err(messaging)?;
        inner.subscribe(topics).map_err(messaging)?;
        Ok(Consumer_ { inner })
    }

    pub async fn recv(&self) -> Result<rdkafka::message::OwnedMessage> {
        let m = self.inner.recv().await.map_err(messaging)?;
        Ok(m.detach())
    }

    pub fn commit(&self, m: &rdkafka::message::OwnedMessage) -> Result<()> {
        let mut tpl = rdkafka::TopicPartitionList::new();
        tpl.add_partition_offset(
            m.topic(),
            m.partition(),
            rdkafka::Offset::Offset(m.offset() + 1),
        )
        .map_err(messaging)?;
        self.inner.commit(&tpl, CommitMode::Sync).map_err(messaging)
    }
}
