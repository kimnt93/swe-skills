//! Integration tests against real PostgreSQL and Redis. Ignored by default:
//!
//!     docker compose -f docker-compose.infra.local.yaml up -d postgres redis
//!     scripts/health.sh --wait postgres,redis
//!     set -a; . ./.env; set +a; cargo test -p svc-infra -- --ignored
#![allow(clippy::unwrap_used, clippy::expect_used)]

use svc_core::{config, item::Item, ports::ItemRepository, Error};
use svc_infra::{postgres::PgItems, redis_lock::Redis, s3::ObjectStore};
use time::OffsetDateTime;
use uuid::Uuid;

#[tokio::test]
#[ignore = "needs live PostgreSQL"]
async fn postgres_round_trip() {
    let cfg = config::load().expect("integration environment");
    let pg = PgItems::open(&cfg.postgres, cfg.postgres.pool_size).unwrap();
    // goose Up section (the real service applies it with the goose binary as a one-shot job)
    let up = include_str!("../../../schemas/0001_items.sql")
        .split("-- +goose Up")
        .nth(1)
        .unwrap()
        .split("-- +goose Down")
        .next()
        .unwrap()
        .to_string();
    let (client, conn) = tokio_postgres_connect(&cfg).await;
    tokio::spawn(conn);
    client
        .batch_execute(&format!("DROP TABLE IF EXISTS items; {up}"))
        .await
        .unwrap();

    let item = Item::new(Uuid::new_v4().to_string(), "pen", OffsetDateTime::now_utc()).unwrap();
    pg.create(&item).await.unwrap();
    let got = pg.get(&item.id).await.unwrap();
    assert_eq!(got.name, "pen");
    assert_eq!(got.created_at.offset(), time::UtcOffset::UTC);
    assert!(matches!(
        pg.get(&Uuid::new_v4().to_string()).await,
        Err(Error::NotFound)
    ));
    assert!(matches!(pg.get("not-a-uuid").await, Err(Error::NotFound)));
    pg.upsert(&item).await.unwrap();
    pg.upsert(&item).await.unwrap(); // idempotent
    pg.ping().await.unwrap();
}

#[tokio::test]
#[ignore = "needs live Redis"]
async fn redis_lock_is_exclusive() {
    let cfg = config::load().expect("integration environment");
    let r = Redis::open(&cfg.redis).await.unwrap();
    r.ping().await.unwrap();
    let key = format!("lock:{}", Uuid::new_v4());
    assert!(r.lock(&key, "a", 5).await.unwrap());
    assert!(
        !r.lock(&key, "b", 5).await.unwrap(),
        "a second holder must not get the lock"
    );
    assert!(
        !r.unlock(&key, "b").await.unwrap(),
        "only the owner may release"
    );
    assert!(r.unlock(&key, "a").await.unwrap());
    assert!(r.lock(&key, "b", 5).await.unwrap());
}

async fn tokio_postgres_connect(
    cfg: &config::Config,
) -> (
    tokio_postgres::Client,
    tokio_postgres::Connection<tokio_postgres::Socket, tokio_postgres::tls::NoTlsStream>,
) {
    let mut c = tokio_postgres::Config::new();
    c.host(&cfg.postgres.host)
        .port(cfg.postgres.port)
        .dbname(&cfg.postgres.db)
        .user(&cfg.postgres.user)
        .password(&cfg.postgres.password);
    c.connect(tokio_postgres::NoTls).await.unwrap()
}

#[tokio::test]
#[ignore = "needs live RustFS or another S3-compatible store"]
async fn s3_round_trip() {
    let cfg = config::load().expect("integration environment");
    let store = ObjectStore::open(&cfg.s3);
    store.ensure_bucket().await.unwrap();
    store.ping().await.unwrap();
    let prefix = format!("e2e/{}/", Uuid::new_v4());
    store
        .put(
            &format!("{prefix}a.json"),
            br#"{"a":1}"#.to_vec(),
            "application/json",
        )
        .await
        .unwrap();
    assert_eq!(
        store.get(&format!("{prefix}a.json")).await.unwrap(),
        br#"{"a":1}"#
    );
    assert_eq!(
        store.list(&prefix, 10).await.unwrap(),
        vec![format!("{prefix}a.json")]
    );
    assert!(matches!(
        store.get(&format!("{prefix}missing")).await,
        Err(Error::NotFound)
    ));
    store.delete(&format!("{prefix}a.json")).await.unwrap();
}

#[cfg(feature = "kafka")]
#[tokio::test]
#[ignore = "needs a live Kafka broker"]
async fn kafka_publish_consume() {
    use rdkafka::{
        admin::{AdminClient, AdminOptions, NewTopic, TopicReplication},
        client::DefaultClientContext,
        config::ClientConfig,
        Message,
    };
    use svc_infra::kafka::{Consumer_, Producer};
    let mut cfg = config::load().expect("integration environment").kafka;
    cfg.consumer_group = format!("e2e-{}", Uuid::new_v4());
    let topic = format!("e2e.{}", Uuid::new_v4());
    // create the topic first
    let mut base = ClientConfig::new();
    for (k, v) in cfg.client_config() {
        base.set(k, v);
    }
    let admin: AdminClient<DefaultClientContext> = base.create().unwrap();
    admin
        .create_topics(
            &[NewTopic::new(&topic, 1, TopicReplication::Fixed(1))],
            &AdminOptions::new(),
        )
        .await
        .unwrap();
    let consumer = Consumer_::new(&cfg, &[&topic], true).unwrap();
    let producer = Producer::new(&cfg).unwrap();
    producer.ping().unwrap();
    producer
        .publish_with_headers(&topic, "k", b"v", &[("traceparent", "00-abc")])
        .await
        .unwrap();
    let msg = tokio::time::timeout(std::time::Duration::from_secs(30), consumer.recv())
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        (msg.key(), msg.payload()),
        (Some(&b"k"[..]), Some(&b"v"[..]))
    );
    consumer.commit(&msg).unwrap(); // only after the message was handled
    producer.flush();
}
