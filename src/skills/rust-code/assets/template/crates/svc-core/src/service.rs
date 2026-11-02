//! Use cases: flow and validation; no SQL, no HTTP.

use serde::Serialize;
use time::OffsetDateTime;

use crate::{
    item::Item,
    ports::{EventPublisher, ItemRepository},
    Error, Result,
};

pub struct Items<R, E> {
    pub repo: R,
    pub events: E,
    pub new_id: fn() -> String,
    pub now: fn() -> OffsetDateTime,
}

#[derive(Serialize)]
struct ItemCreated<'a> {
    id: &'a str,
    name: &'a str,
}

impl<R: ItemRepository, E: EventPublisher> Items<R, E> {
    pub async fn create(&self, name: &str) -> Result<Item> {
        let item = Item::new((self.new_id)(), name, (self.now)())?;
        self.repo.create(&item).await?;
        let payload = serde_json::to_vec(&ItemCreated {
            id: &item.id,
            name: &item.name,
        })
        .map_err(|e| Error::Messaging(format!("encode event: {e}")))?;
        self.events
            .publish("items.created", &item.id, &payload)
            .await?;
        Ok(item)
    }

    pub async fn get(&self, id: &str) -> Result<Item> {
        self.repo.get(id).await
    }
}
