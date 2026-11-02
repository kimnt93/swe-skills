//! Live test for the SeaORM adapter. Ignored by default:
//!
//!     set -a; . ./.env; set +a
//!     cargo test -p svc-infra --features orm --test orm_live -- --ignored
#![cfg(feature = "orm")]
#![allow(clippy::unwrap_used, clippy::expect_used)]

use svc_core::{config, item::Item, ports::ItemRepository, Error};
use svc_infra::orm::OrmItems;
use time::OffsetDateTime;
use uuid::Uuid;

#[tokio::test]
#[ignore = "needs live PostgreSQL with the items table (goose up)"]
async fn orm_round_trip() {
    let cfg = config::load().expect("integration environment");
    let repo = OrmItems::open(&cfg.postgres, cfg.postgres.pool_size as u32)
        .await
        .unwrap();
    repo.ping().await.unwrap();

    let item = Item::new(Uuid::new_v4().to_string(), "pen", OffsetDateTime::now_utc()).unwrap();
    repo.create(&item).await.unwrap();

    let got = repo.get(&item.id).await.unwrap();
    assert_eq!(got.name, "pen");
    assert_eq!(got.created_at.offset(), time::UtcOffset::UTC);

    assert!(matches!(
        repo.get(&Uuid::new_v4().to_string()).await,
        Err(Error::NotFound)
    ));

    repo.upsert(&item).await.unwrap();
    repo.upsert(&item).await.unwrap(); // idempotent

    let listed = repo
        .list_by_ids(&[Uuid::parse_str(&item.id).unwrap()])
        .await
        .unwrap();
    assert_eq!(listed.len(), 1);
}
