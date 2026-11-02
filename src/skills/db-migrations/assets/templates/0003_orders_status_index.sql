-- +goose NO TRANSACTION

-- +goose Up
-- On an existing (possibly large) table: CONCURRENTLY does not block writes, and it
-- cannot run inside a transaction, hence NO TRANSACTION above.
CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_status_idx
    ON orders (status);

-- +goose Down
DROP INDEX CONCURRENTLY IF EXISTS orders_status_idx;
