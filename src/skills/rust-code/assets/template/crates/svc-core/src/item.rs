//! The `Item` aggregate: validation and normalisation, deterministic (no clock reads).

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::{Error, Result};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Item {
    pub id: String,
    pub name: String,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

impl Item {
    /// Callers inject the id and the time; the result is always UTC.
    pub fn new(id: String, name: &str, now: OffsetDateTime) -> Result<Item> {
        let name = name.trim();
        if name.is_empty() || name.chars().count() > 120 {
            return Err(Error::InvalidName);
        }
        Ok(Item {
            id,
            name: name.to_string(),
            created_at: now.to_offset(time::UtcOffset::UTC),
        })
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used)]
mod tests {
    use super::*;
    use time::macros::datetime;

    #[test]
    fn trims_and_normalises_to_utc() {
        let item = Item::new("1".into(), "  pen ", datetime!(2026-01-02 03:04:05 +7)).unwrap();
        assert_eq!(item.name, "pen");
        assert_eq!(item.created_at, datetime!(2026-01-01 20:04:05 UTC));
        assert_eq!(item.created_at.offset(), time::UtcOffset::UTC);
    }

    #[test]
    fn rejects_blank_and_long_names() {
        for name in ["", "   ", &"x".repeat(121)] {
            assert!(
                matches!(
                    Item::new("1".into(), name, datetime!(2026-01-02 0:00 UTC)),
                    Err(Error::InvalidName)
                ),
                "{name:?}"
            );
        }
    }
}
