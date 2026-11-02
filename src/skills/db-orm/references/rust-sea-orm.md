# Rust + SeaORM

*Verified with: SeaORM 2.0.4 (`sqlx-postgres`, `runtime-tokio-rustls`, `with-time`, `with-uuid`), Rust 1.99, PostgreSQL 17; the adapter passes `cargo clippy -D warnings` and `assets/rust-sea-orm/orm_live.rs` passes live.*

Use it only when an ORM is requested or already in the project ([orm-rules](orm-rules.md)); the default is `tokio-postgres` with raw SQL
(`rust-code/references/postgres.md`).

Reference: `assets/rust-sea-orm/orm.rs` (adapter), `orm_live.rs` (ignored live test) and `Cargo.snippet.toml` (the three Cargo edits). Put
`orm.rs` in `crates/svc-infra/src/` behind the `orm` feature, so a service without it compiles no ORM:

```toml
# crates/svc-infra/Cargo.toml
sea-orm = { workspace = true, optional = true }

[features]
orm = ["dep:sea-orm"]
```

## Entity rules

```rust
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
```

- The entity module is private to the adapter; convert to the domain `Item` in `to_item` (UUID to `String`, `OffsetDateTime` stays UTC).
  Domain types never derive `DeriveEntityModel`.
- Plain fields, no `Option` for `NOT NULL` columns. You may generate the entity from the migrated database with `sea-orm-cli generate
  entity`, then trim it; the database is the source of truth, not the entity.
- Build the pool from `Settings` with `PgConnectOptions` (no URL string, so no password escaping or logging) and wrap it with
  `SqlxPostgresConnector::from_sqlx_postgres_pool`.

## Queries

```rust
// One row: find_by_id; None -> Error::NotFound.
let model = entity::Entity::find_by_id(uuid)
    .one(&self.db)
    .await
    .map_err(storage)?
    .ok_or(Error::NotFound)?;

// A set in one query, newest first, bounded.
let models = entity::Entity::find()
    .filter(entity::Column::Id.is_in(ids.iter().copied()))
    .order_by_desc(entity::Column::CreatedAt)
    .limit(500)
    .all(&self.db)
    .await
    .map_err(storage)?;

// Idempotent write.
let conflict = OnConflict::column(entity::Column::Id)
    .update_column(entity::Column::Name)
    .to_owned();

entity::Entity::insert(active_model)
    .on_conflict(conflict)
    .exec(&self.db)
    .await
    .map_err(storage)?;
```

- One call per line for chains. A transaction is `self.db.begin().await?` ... `txn.commit().await?` (rolls back on drop); one per business
  operation.
- Raw SQL escape hatch: `Statement::from_sql_and_values(DbBackend::Postgres, SQL, [values])` with `SQL` a multi-line `const`.
- Map `DbErr` to the crate's generic `Error::Storage("database operation failed")`: a `DbErr` can contain SQL and hostnames. Log the cause
  where it is handled.

## Do not

- `sea-orm-migration`, `Schema::create_table_from_entity` or `synchronize` against a real database (goose files own the schema,
  `db-migrations`). If the project already uses `sea-orm-migration`, keep it as the only system.
- Add the ORM to a crate that does not need it (compile time grows noticeably); keep it behind the `orm` feature.
- Return an entity `Model` from `svc-core` or the API crate.

## Checks

```bash
cargo fmt --all -- --check && cargo clippy -p svc-infra --features orm --all-targets -- -D warnings
set -a; . ./.env; set +a; cargo test -p svc-infra --features orm --test orm_live -- --ignored
```

## Example usage

- "Add SeaORM behind a Cargo feature, same repository port." · "Generate the entity for the new `positions` table."
