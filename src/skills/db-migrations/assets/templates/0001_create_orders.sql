-- +goose Up
-- A new table: columns are NOT NULL with defaults where a default exists, so the
-- backend model never needs a pointer or an Option for them.
CREATE TABLE orders (
    id         uuid        PRIMARY KEY,
    account_id uuid        NOT NULL,
    symbol     text        NOT NULL,
    quantity   numeric     NOT NULL DEFAULT 0,
    note       text        NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- An index on a table created in this same file needs no CONCURRENTLY.
CREATE INDEX orders_account_created_idx
    ON orders (account_id, created_at DESC);

-- +goose Down
DROP TABLE orders;
