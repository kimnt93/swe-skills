-- +goose Up
-- Columns are NOT NULL with defaults, so Go structs need no pointers: a field is its
-- zero value, never nil.
CREATE TABLE zero_demo (
    id     uuid PRIMARY KEY,
    name   text        NOT NULL DEFAULT '',
    qty    bigint      NOT NULL DEFAULT 0,
    active boolean     NOT NULL DEFAULT false,
    seen   timestamptz NOT NULL DEFAULT '0001-01-01T00:00:00Z',
    note   text        NOT NULL DEFAULT ''
);

-- +goose Down
DROP TABLE zero_demo;
