//! Optional SeaORM adapter for the items port, behind the `orm` Cargo feature.
//!
//! Use it only when the project asks for an ORM or already has one. The default adapter is raw SQL
//! (`postgres.rs`). Both implement `ItemRepository`. The schema stays in goose files
//! (db-migrations): never run an ORM schema sync against a real database.

use sea_orm::sea_query::OnConflict;
use sea_orm::sqlx::postgres::{PgConnectOptions, PgPoolOptions};
use sea_orm::DatabaseConnection;
use sea_orm::{
    ActiveValue::Set, ColumnTrait, DbErr, EntityTrait, QueryFilter, SqlxPostgresConnector,
};
use svc_core::{config::Postgres as Settings, item::Item, ports::ItemRepository, Error, Result};
use uuid::Uuid;

/// The `items` table. A model is not a domain type: see `to_item`.
mod entity {
    use sea_orm::entity::prelude::*;

    #[derive(Clone, Debug, PartialEq, DeriveEntityModel)]
    #[sea_orm(table_name = "items")]
    pub struct Model {
        #[sea_orm(primary_key, auto_increment = false)]
        pub id: Uuid,
        pub name: String,
        pub created_at: TimeDateTimeWithTimeZone,
    }

    #[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
    pub enum Relation {}

    impl ActiveModelBehavior for ActiveModel {}
}

#[derive(Clone)]
pub struct OrmItems {
    db: DatabaseConnection,
}

fn storage(_cause: DbErr) -> Error {
    // The driver's message can include hosts and SQL; keep it generic and log the cause where it
    // is handled.
    Error::Storage("database operation failed".into())
}

fn to_item(model: entity::Model) -> Item {
    Item {
        id: model.id.to_string(),
        name: model.name,
        created_at: model.created_at,
    }
}

fn to_active(item: &Item) -> Result<entity::ActiveModel> {
    let id = Uuid::parse_str(&item.id).map_err(|_| Error::NotFound)?;

    Ok(entity::ActiveModel {
        id: Set(id),
        name: Set(item.name.clone()),
        created_at: Set(item.created_at),
    })
}

impl OrmItems {
    /// Builds the pool from the same POSTGRES_* settings as the raw adapter.
    pub async fn open(s: &Settings, max_connections: u32) -> Result<Self> {
        let options = PgConnectOptions::new()
            .host(&s.host)
            .port(s.port)
            .database(&s.db)
            .username(&s.user)
            .password(&s.password);

        let pool = PgPoolOptions::new()
            .max_connections(max_connections)
            .connect_with(options)
            .await
            .map_err(|_| Error::Storage("database connection failed".into()))?;

        Ok(Self {
            db: SqlxPostgresConnector::from_sqlx_postgres_pool(pool),
        })
    }

    pub async fn ping(&self) -> Result<()> {
        self.db.ping().await.map_err(storage)
    }

    /// Idempotent write: a replay converges on one row.
    pub async fn upsert(&self, item: &Item) -> Result<()> {
        let conflict = OnConflict::column(entity::Column::Id)
            .update_column(entity::Column::Name)
            .to_owned();

        entity::Entity::insert(to_active(item)?)
            .on_conflict(conflict)
            .exec(&self.db)
            .await
            .map_err(storage)?;

        Ok(())
    }

    /// One bounded query for a set (no N+1).
    pub async fn list_by_ids(&self, ids: &[Uuid]) -> Result<Vec<Item>> {
        use sea_orm::{QueryOrder, QuerySelect};

        let models = entity::Entity::find()
            .filter(entity::Column::Id.is_in(ids.iter().copied()))
            .order_by_desc(entity::Column::CreatedAt)
            .limit(500)
            .all(&self.db)
            .await
            .map_err(storage)?;

        Ok(models.into_iter().map(to_item).collect())
    }
}

impl ItemRepository for OrmItems {
    async fn create(&self, item: &Item) -> Result<()> {
        entity::Entity::insert(to_active(item)?)
            .exec(&self.db)
            .await
            .map_err(storage)?;

        Ok(())
    }

    async fn get(&self, id: &str) -> Result<Item> {
        let Ok(uuid) = Uuid::parse_str(id) else {
            return Err(Error::NotFound);
        };

        let model = entity::Entity::find_by_id(uuid)
            .one(&self.db)
            .await
            .map_err(storage)?
            .ok_or(Error::NotFound)?;

        Ok(to_item(model))
    }
}
