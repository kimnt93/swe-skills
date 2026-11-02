# Rust + Kafka (rdkafka)

Adapter: `assets/template/crates/svc-infra/src/kafka.rs` (Cargo feature `kafka`); settings: `.../config/kafka.rs`; env: `assets/env/kafka.env.example` ([env-config](env-config.md)). Tested live against Apache Kafka 4.1.

`Producer`: `enable.idempotence=true`, `acks=all`, `lz4`; `send(...).await` returns only after the broker's delivery report; `flush()` on shutdown.
`Consumer_`: `enable.auto.commit=false`, `commit` only after the handler succeeded (handlers idempotent), topics created first (a topic created after
the subscription is noticed only after a metadata refresh). SASL settings are added by `Kafka::client_config()` only for `SASL_*` protocols. Build
needs cmake (`apt-get install cmake` in the build stage).


## Example usage

- “Add an idempotent Kafka producer with delivery confirmation.”
- “Consume messages with manual commit and make the handler replay-safe.”
