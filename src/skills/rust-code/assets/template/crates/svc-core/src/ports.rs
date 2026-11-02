//! Ports: what the use cases need from the outside, declared where they are used and kept small.
//! Native `async fn` in traits (not object-safe): use cases are generic over the port, so there is
//! no boxing.

use crate::{item::Item, Result};

pub trait ItemRepository: Send + Sync {
    fn create(&self, item: &Item) -> impl std::future::Future<Output = Result<()>> + Send;
    /// `Error::NotFound` when absent.
    fn get(&self, id: &str) -> impl std::future::Future<Output = Result<Item>> + Send;
}

pub trait EventPublisher: Send + Sync {
    fn publish(
        &self,
        topic: &str,
        key: &str,
        value: &[u8],
    ) -> impl std::future::Future<Output = Result<()>> + Send;
}
